# Person 3 — Orchestration & Memory

Status: **core logic done and tested; Strands + live OpenSearch wiring
still open.** `SiteAgent` (`agent.py`) and `run_swarm_cycle` (`loop.py`)
are real, working code — this is what `scripts/run_isolated_vs_pooled.py`
actually runs. What's left is infrastructure this environment couldn't
provide: real Strands agents need model credentials (Bedrock/Anthropic/etc.)
that aren't configured here, and a live OpenSearch cluster needs Docker,
whose daemon isn't running here. Both gaps are scoped to one call site
each — see below.

```bash
py -3 -m pytest tests/test_shared_store.py tests/test_orchestration.py -v
py -3 scripts/run_isolated_vs_pooled.py   # runs the real swarm cycle end to end
```

From `Tripwire_Execution_Doc.md`:

- [x] Wire each site as an agent: detect → abstract → request-to-share → receive → re-check — done as `SiteAgent`, not yet Strands-wrapped
- [ ] Stand up OpenSearch as the shared pattern store — `OpenSearchPatternStore` is written but untested against a live cluster; `LocalPatternStore` is the working fallback
- [x] Connect Person 1's detector and Person 2's policy gate into one running loop, not three separate scripts — `run_swarm_cycle`
- [x] Make the pooled-memory check actually change Person 1's detection number — proven: `site_c_low_data` 33.3% → 66.7%, zero added false positives

## What's actually here

| File | Purpose |
|---|---|
| `agent.py` | `SiteAgent` — one substation's detect → drift-filter → abstract → request-to-share → receive → re-check, wrapping its own `SiteDetector` around a shared `PolicyGate` and `PatternStore`. |
| `loop.py` | `run_swarm_cycle(gate, store)` — runs every configured site's `SiteAgent` through one full round: everyone detects and shares, then everyone re-checks against the pool. This generalizes the original low-data-site-only demo to every site, which is the more faithful reading of "no central brain" (execution doc, 3a) — and empirically, the well-resourced sites improve too (93.3%→100%, 97.2%→100%), not just the low-data one. |

`../shared_store/store.py` (also Person 3's) has the `PatternStore`
interface both of these depend on.

## The two remaining gaps, and exactly how narrow they are

### 1. Strands agents

`SiteAgent.detect()`, `.share_round()`, and `.receive_and_recheck()` are
plain Python methods today — no LLM in the loop. A Strands `Agent` wraps
an LLM call loop around tool functions, which means constructing and
running a real one needs a model provider (AWS Bedrock, Anthropic, etc.)
and credentials this environment doesn't have — invoking one would mean
spending someone's real API budget, so that wasn't done without asking.

The wrapping itself is thin once credentials exist:

```python
from strands import Agent, tool

@tool
def detect_and_share(site_agent: SiteAgent) -> ShareRoundResult:
    flagged = site_agent.detect()
    return site_agent.share_round(flagged)

@tool
def receive_and_recheck(site_agent: SiteAgent) -> list[str]:
    return sorted(site_agent.receive_and_recheck())

agent = Agent(tools=[detect_and_share, receive_and_recheck])  # needs a model provider configured
```

Nothing about `SiteAgent`'s logic needs to change — only who calls
`detect_and_share` / `receive_and_recheck` and when (an LLM deciding, vs.
`loop.py` calling them directly in a fixed order).

### 2. A live OpenSearch cluster

`shared_store/store.py::OpenSearchPatternStore` is written against the
real `opensearch-py` client (`indices.create`, `.index`, `.search`,
`.count`) but has never connected to an actual cluster in this
environment — `docker info` here shows the daemon isn't running, so there
was nothing to stand up SAM CLI + LocalStack or a real OpenSearch
container against. Swapping it in once one exists is one line, in
`scripts/run_isolated_vs_pooled.py` (or wherever a live loop is driven
from):

```python
# store = LocalPatternStore(root / "shared_store" / "pool.jsonl")
store = OpenSearchPatternStore(hosts=[{"host": "localhost", "port": 9200}])
```

`SiteAgent` and `run_swarm_cycle` only ever call `.index()`, `.query()`,
and `.count()` — both classes implement the same `PatternStore` interface,
so nothing else changes.

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
