"""
The real Strands wiring orchestration/README.md described as "the two
remaining gaps" — this closes gap #1.

`SiteAgent` (agent.py) is unchanged: `detect()`, `share_round()`, and
`receive_and_recheck()` are exactly the same deterministic, tested Python
they always were. What changes here is *who decides when to call them*.
In `loop.py::run_swarm_cycle`, that's a fixed Python `for` loop. Here,
it's a real `strands.Agent` backed by a real model — reading a prompt,
deciding to call `detect_and_share` for each site, then
`receive_and_recheck` for each site, via genuine LLM tool-calling, not a
hardcoded sequence.

The model is a local Ollama model (`qwen2.5:1.5b`, see
`scripts/run_strands_swarm.py` for the exact pull command) rather than
AWS Bedrock or Anthropic, because this environment has no cloud model
credentials configured — Strands doesn't care which provider sits behind
it, and swapping to Bedrock later is a one-line change to the `model=`
argument built in `build_model()`. `llama3.2:1b` was tried first and
rejected: it would print tool-call-shaped JSON as plain assistant text
instead of issuing real tool calls through Ollama's function-calling
path, which Strands has no way to execute. `qwen2.5:1.5b`, trained
explicitly for tool use, calls tools correctly.

Three honest, observed limits of a small local model doing real tool
calling, each handled below rather than hidden:

1. It sometimes calls a tool for the same site more than once despite
   being told not to (observed: 6 `detect_and_share` calls for 3 sites in
   one run). `share_round()` is not safe to run twice — it would abstract
   and index the same anomalies again under new signature ids, inflating
   the pool with duplicates. Fixed by making the tools themselves
   idempotent (see `_build_tools`), not by trusting the prompt harder.
2. Asked to do six tool calls across two phases in one turn, it would
   complete phase one and then stop, believing it was done. Fixed by
   splitting the two phases into two separate calls.
3. The first fix for #2 kept one `Agent` alive across both calls, on the
   theory that it should get to remember what it already did. In testing
   this backfired: on the runs where #1 produced duplicate calls, the
   resulting cluttered conversation history caused phase two — asked in
   that same conversation — to degrade into echoing the instructions back
   as plain text instead of calling anything, which dropped single-attempt
   success noticeably below what direct one-phase testing had suggested.
   Fixed by giving each phase its own fresh `Agent` and short conversation
   (see `_run_once`) — the underlying Python state (`agents`, `log`) is
   shared via closure regardless of which `Agent` object calls into it,
   so nothing about *correctness* depends on one `Agent` remembering the
   other phase, only reliability did, and it does much better with a
   clean slate each phase: 6/6 single-attempt successes across two
   separate test batches after this change, versus frequent failures
   (including one run that failed all 3 attempts back to back) before it.

This module is deliberately *not* wired into `orchestration/loop.py` or
the website's live backend (`server.py`): an LLM tool-calling loop is
slower and less deterministic than a plain function call, which is the
wrong trade for a button judges click during a demo. `run_swarm_cycle`
stays the fast, deterministic path. This module is the honest proof that
the Strands-orchestrated version also works, exactly as scoped.
"""

from __future__ import annotations

from dataclasses import dataclass

from strands import Agent, tool
from strands.models.ollama import OllamaModel

from detection.baseline import DetectionMetrics, evaluate_detection
from detection.dataset import SiteConfig, generate_all_sites
from orchestration.agent import ShareRoundResult, SiteAgent
from orchestration.loop import SwarmCycleResult
from policy.gate import PolicyGate
from shared_store.store import PatternStore

DEFAULT_MODEL_ID = "qwen2.5:1.5b"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"


def build_model(model_id: str = DEFAULT_MODEL_ID, host: str = DEFAULT_OLLAMA_HOST) -> OllamaModel:
    """A local, free, fully offline model — see this module's docstring
    for why this isn't AWS Bedrock."""
    return OllamaModel(host=host, model_id=model_id, temperature=0.1)


@dataclass
class _ToolLog:
    """Tool calls report their real results here — the numbers below come
    from these entries, never from parsing the LLM's closing remarks.
    An LLM narrating "site_a improved to 100%" is not evidence that it
    did; the tool actually running `SiteAgent.share_round()` is."""

    share_results: dict[str, ShareRoundResult]
    recheck_results: dict[str, set[str]]


def _build_tools(agents: dict[str, SiteAgent], log: _ToolLog):
    @tool
    def detect_and_share(site_id: str) -> dict:
        """Run this site's detector and attempt to share whatever clears
        the drift filter through the Cedar policy gate.

        Args:
            site_id: which site to run, e.g. "site_a", "site_b", "site_c_low_data".
        """
        # A small local model occasionally calls a tool for the same site
        # more than once despite being told not to (observed: 6 calls for
        # 3 sites in one run). share_round() is not safe to run twice --
        # it would abstract and index the same anomalies again under new
        # signature ids, inflating the pool with duplicates of one site's
        # patterns. The fix is here, not in the prompt: make the tool
        # itself idempotent, so a model quirk can't distort real state.
        if site_id in log.share_results:
            result = log.share_results[site_id]
        else:
            agent = agents[site_id]
            flagged = agent.detect()
            result = agent.share_round(flagged)
            log.share_results[site_id] = result
        return {
            "site_id": site_id,
            "flagged": result.flagged,
            "shared": result.shared,
            "denied": result.denied,
        }

    @tool
    def receive_and_recheck(site_id: str) -> dict:
        """Re-check this site's own unflagged consumers against whatever
        the shared pool now holds from every site that has already run
        detect_and_share.

        Args:
            site_id: which site to re-check, e.g. "site_a", "site_b", "site_c_low_data".
        """
        if site_id in log.recheck_results:
            newly_flagged = log.recheck_results[site_id]
        else:
            agent = agents[site_id]
            newly_flagged = agent.receive_and_recheck()
            log.recheck_results[site_id] = newly_flagged
        return {"site_id": site_id, "total_flagged_after_pool": len(newly_flagged)}

    return [detect_and_share, receive_and_recheck]


@dataclass(frozen=True)
class StrandsSwarmResult:
    cycle: SwarmCycleResult
    transcript: str


def _run_once(
    gate: PolicyGate,
    store: PatternStore,
    configs: tuple[SiteConfig, ...],
    model: OllamaModel | None,
) -> StrandsSwarmResult:
    sites = generate_all_sites(configs)
    agents = {c.site_id: SiteAgent(c, sites[c.site_id], gate, store) for c in configs}
    log = _ToolLog(share_results={}, recheck_results={})
    tools = _build_tools(agents, log)

    site_ids = [c.site_id for c in configs]
    resolved_model = model or build_model()
    system_prompt = (
        "You orchestrate electricity-theft detection sites by calling tools. "
        "Call exactly the tool you are asked to call, once each, for every "
        "site named in the request. Do not call it for a site twice. "
        "Do not call it for a site you were not asked about. "
        "When done, reply with one short sentence and nothing else."
    )

    # Each phase gets its own fresh Agent -- a new, short, single-purpose
    # conversation -- rather than one Agent carrying both phases' history.
    # Observed cause worth recording: when phase one produced duplicate
    # calls (the model repeating a site despite being told not to), the
    # resulting cluttered history made phase two, asked in the same
    # conversation, degrade into echoing the instructions back as text
    # instead of calling anything. The underlying Python state (`agents`,
    # `log`) is shared via closure regardless of which Agent object calls
    # into it, so nothing about correctness depends on one Agent
    # remembering the other phase -- only reliability does, and it does
    # better with less clutter in front of it.
    share_agent = Agent(model=resolved_model, tools=tools, system_prompt=system_prompt)
    share_agent(
        "Call detect_and_share exactly once for each of these sites: "
        f"{', '.join(site_ids)}."
    )
    missing_share = set(site_ids) - set(log.share_results)
    if missing_share:
        raise RuntimeError(
            f"the model did not call detect_and_share for {missing_share}. "
            "This is exactly the non-determinism risk noted in this module's "
            "docstring; retry, or fall back to loop.run_swarm_cycle."
        )

    recheck_agent = Agent(model=resolved_model, tools=tools, system_prompt=system_prompt)
    response = recheck_agent(
        "Call receive_and_recheck exactly once for each of these sites: "
        f"{', '.join(site_ids)}."
    )

    missing_recheck = set(site_ids) - set(log.recheck_results)
    if missing_recheck:
        raise RuntimeError(
            f"the model did not call receive_and_recheck for {missing_recheck}. "
            "This is exactly the non-determinism risk noted in this module's "
            "docstring; retry, or fall back to loop.run_swarm_cycle."
        )

    isolated_metrics: dict[str, DetectionMetrics] = {}
    pooled_metrics: dict[str, DetectionMetrics] = {}
    for site_id, site_agent in agents.items():
        isolated_metrics[site_id] = evaluate_detection(sites[site_id], site_agent.isolated_flag_ids())
        pooled_metrics[site_id] = evaluate_detection(sites[site_id], log.recheck_results[site_id])

    cycle = SwarmCycleResult(
        isolated_metrics=isolated_metrics,
        pooled_metrics=pooled_metrics,
        share_results=log.share_results,
        pool_size=store.count(),
    )
    return StrandsSwarmResult(cycle=cycle, transcript=str(response))


def run_swarm_cycle_via_strands(
    gate: PolicyGate,
    store: PatternStore,
    configs: tuple[SiteConfig, ...],
    model: OllamaModel | None = None,
    max_attempts: int = 5,
) -> StrandsSwarmResult:
    """The same detect -> share -> re-check cycle as `loop.run_swarm_cycle`,
    but orchestrated by a real `strands.Agent` instead of a Python `for`
    loop. Every site still gets its own `SiteAgent` wrapping its own
    private data; the gate and store are still shared across all of them,
    exactly as `agent.py`'s docstring requires.

    After the fresh-agent-per-phase fix in `_run_once` (see this module's
    docstring, point 3), single-attempt success was 6/6 across two
    separate test batches — before that fix, the same setup failed often
    enough that one run burned all 3 of an earlier, smaller retry budget
    in a row. The retry loop is kept anyway: a small local model calling
    real tools is not a component to trust at 100% on faith just because
    recent runs looked clean, and the cost of a spare attempt is one more
    ~10 second Ollama call against a store that gets wiped first. If every
    attempt still fails, the last error propagates — callers who need a
    guaranteed result should catch that and fall back to
    `loop.run_swarm_cycle`, exactly as the error message says.
    """
    last_error: RuntimeError | None = None
    for attempt in range(1, max_attempts + 1):
        if hasattr(store, "clear"):
            store.clear()  # wipe any partial writes a failed attempt made
        try:
            return _run_once(gate, store, configs, model)
        except RuntimeError as e:
            last_error = e
            print(f"  [attempt {attempt}/{max_attempts} failed: {e}]")
    assert last_error is not None
    raise last_error
