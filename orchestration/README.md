# Person 3 — Orchestration & Memory

Status: **core logic done and tested; Strands wiring done and tested;
live OpenSearch genuinely blocked by this environment, not just
unattempted.** `SiteAgent` (`agent.py`) and `run_swarm_cycle` (`loop.py`)
are real, working code — this is what `scripts/run_isolated_vs_pooled.py`
actually runs, and it's what the website's live backend (`../server.py`)
calls too. `strands_agent.py` is the same pipeline orchestrated by a real
`strands.Agent` instead, proven working end to end — see below for both.

```bash
py -3 -m pytest tests/test_shared_store.py tests/test_orchestration.py tests/test_strands_agent.py -v
py -3 scripts/run_isolated_vs_pooled.py   # the fast, deterministic path — what the website runs
py -3 scripts/run_strands_swarm.py        # the same cycle, orchestrated by a real local LLM
```

From `Tripwire_Execution_Doc.md`:

- [x] Wire each site as an agent: detect → abstract → request-to-share → receive → re-check — done as `SiteAgent`, and as of `strands_agent.py`, also genuinely Strands-wrapped
- [ ] Stand up OpenSearch as the shared pattern store — attempted for real, blocked at the host level (see below); `LocalPatternStore` remains the working, tested path
- [x] Connect Person 1's detector and Person 2's policy gate into one running loop, not three separate scripts — `run_swarm_cycle`
- [x] Make the pooled-memory check actually change Person 1's detection number — proven: `site_c_low_data` 33.3% → 66.7%, zero added false positives, both via the plain loop and via the Strands agent

## What's actually here

| File | Purpose |
|---|---|
| `agent.py` | `SiteAgent` — one substation's detect → drift-filter → abstract → request-to-share → receive → re-check, wrapping its own `SiteDetector` around a shared `PolicyGate` and `PatternStore`. |
| `loop.py` | `run_swarm_cycle(gate, store)` — runs every configured site's `SiteAgent` through one full round via a plain Python loop: everyone detects and shares, then everyone re-checks against the pool. Fast and fully deterministic — this is what `../server.py`'s live website endpoint calls, on purpose (see `strands_agent.py`'s docstring for why an LLM loop is the wrong trade for a button judges click). |
| `strands_agent.py` | The same cycle, orchestrated by a real `strands.Agent` backed by a local Ollama model instead of a `for` loop. Not wired into the website; a standalone, tested proof that the Strands wrapping described below actually works, not just that it's thin. |

`../shared_store/store.py` (also Person 3's) has the `PatternStore`
interface all three depend on.

## Gap 1 — Strands agents — closed

`SiteAgent.detect()`, `.share_round()`, and `.receive_and_recheck()`
never changed. What's new is `orchestration/strands_agent.py`, which
wraps two of them as real `@tool`-decorated functions and hands them to
a real `strands.Agent`:

```python
@tool
def detect_and_share(site_id: str) -> dict:
    agent = agents[site_id]              # agents: dict[str, SiteAgent], closed over
    flagged = agent.detect()
    result = agent.share_round(flagged)
    ...

agent = Agent(model=OllamaModel(host="http://localhost:11434", model_id="qwen2.5:1.5b"),
              tools=[detect_and_share, receive_and_recheck])
```

No cloud credentials were available in this environment (no Bedrock, no
Anthropic key), so the model behind the agent is a local Ollama model
instead — free, offline, and Strands doesn't care which provider sits
behind it. Getting this genuinely working, not just wired, surfaced three
real small-model limits, each fixed in the code rather than papered over
in the prompt — full account in `strands_agent.py`'s module docstring:

1. `llama3.2:1b` couldn't reliably emit real tool calls at all — swapped
   for `qwen2.5:1.5b`, which has explicit tool-use training.
2. The model would sometimes call a tool for the same site twice — fixed
   by making the tools idempotent, not by trusting the prompt harder.
3. Splitting the two phases (share, then recheck) into two separate turns
   on *one* `Agent` was tried first and was unreliable whenever #2 fired,
   because the cluttered history confused the model on the second turn.
   Fixed by giving each phase its own fresh `Agent` — the real state
   (`SiteAgent`, the shared pool) lives in Python closures regardless of
   which `Agent` object calls into it, so nothing about correctness
   depends on the LLM remembering the earlier phase.

Result after those fixes: 6/6 single-attempt successes across two
separate test batches, reproducing the exact same 33.3% → 66.7% (and
93.3%→100%, 97.2%→100%) as the plain loop — see
`scripts/run_strands_swarm.py`'s output. A retry loop (`max_attempts=5`)
stays in `run_swarm_cycle_via_strands` regardless, because a small local
model doing agentic tool-calling doesn't deserve 100% faith just because
recent runs looked clean.

## Gap 2 — a live OpenSearch cluster — genuinely blocked, not just unattempted

This was actually attempted this session, not left aside for lack of
Docker being started. Docker Desktop is installed here; starting its
daemon fails with:

```
Please enable the "Virtual Machine Platform" optional component and
ensure virtualization is enabled in the BIOS.
```

`systeminfo` on this machine reports `Hyper-V Requirements: A hypervisor
has been detected` — this Windows install is itself running inside a
hypervisor, which is almost always why nested virtualization (what WSL2's
backing VM, and therefore Docker Desktop's default backend, needs) isn't
available to the guest. That's a host-level constraint, not a missing
`winget install` — enabling a Windows feature or editing a BIOS setting
that isn't reachable from inside this VM won't fix it.

`shared_store/store.py::OpenSearchPatternStore` is still written against
the real `opensearch-py` client and still just as untested against a live
cluster as before. Swapping it in, on real hardware or a host where
nested virtualization is available, is still exactly this one line:

```python
# store = LocalPatternStore(root / "shared_store" / "pool.jsonl")
store = OpenSearchPatternStore(hosts=[{"host": "localhost", "port": 9200}])
```

`SiteAgent`, `run_swarm_cycle`, and `strands_agent.py` only ever call
`.index()`, `.query()`, and `.count()` — both classes implement the same
`PatternStore` interface, so nothing else changes.

## Rules that must not change when the remaining gaps are closed

- **One `PolicyGate` instance per process**, constructed once and reused —
  it parses Cedar's policy/schema on construction; re-parsing per request
  is wasted work.
- `gate.evaluate_share_request(...)` **always logs**, allow or deny.
  Don't add a second logging step in the agent loop — that would double-log.
- `decision.allowed` is the **only** signal that gates whether a signature
  reaches the shared store. Don't re-derive that decision from
  `signature.has_meter_id` etc. in agent code.
- The **re-check** half of the loop does **not** go through the policy
  gate — the gate only guards the write path. Pooled signatures are
  already sanitized by construction.
- `filter_for_sharing()` (the drift trigger) runs **before** abstraction,
  not after. See `../detection/README.md`, "Why the drift filter exists,"
  for what goes wrong if this step is skipped (the pool gets poisoned by
  the isolation forest's own false positives).

See `../policy/README.md` → "Interface contract with Person 3" and
`../detection/README.md` → "Interface contract with Person 3" for the
full field-level contracts.
