# TRIPWIRE

**Team Saturn · First Commit Hackathon · Bharat Builds Tour Stop 01**

> Share what your meters learn. Not what your meters see.

India loses roughly ₹1.32 lakh crore a year to electricity theft, and the
gap between the best- and worst-performing DISCOMs runs to about 45.8
percentage points — not because smaller DISCOMs are worse at their jobs,
but because they see too few theft cases to learn the pattern alone, and
raw consumption data is too sensitive to pool across utilities. TRIPWIRE
lets sites share the abstracted *shape* of a theft pattern — never the raw
record — with the sharing boundary enforced by a Cedar policy engine, not
by promise. Full background: `docs/Tripwire_Execution_Doc.md`
and `docs/TeamSaturn_ProjectBrief_DISCOM.pdf`.

## Architecture

```
   Site A (Strands agent)         Site B (Strands agent)        Site C — low data
   ┌─────────────────────┐        ┌─────────────────────┐       ┌─────────────────────┐
   │ 1. detect (Person 1)│        │ 1. detect            │       │ 1. detect — starts   │
   │ 2. abstract (Pers.2)│        │ 2. abstract           │       │    weak in isolation │
   │ 3. request-to-share │        │ 3. request-to-share   │       │ 2. abstract           │
   └──────────┬───────────┘        └──────────┬───────────┘       │ 3. request-to-share   │
              │                               │                   └──────────┬───────────┘
              ▼                               ▼                              ▼
        ┌─────────────────── Cedar policy gate (Person 2) ───────────────────┐
        │  forbid: any has_meter_id / has_consumer_id / has_raw_series /     │
        │          has_household_field / has_location  -> DENY, logged      │
        │  permit: kind == "signature" && granularity <= 10 -> ALLOW, logged │
        └───────────────────────────────┬──────────────────────────────────┘
                                         ▼ (permitted signatures only)
                          ┌───────────────────────────────┐
                          │ Shared OpenSearch pattern store │  (Person 3)
                          │  — pooled knowledge, no raw data │
                          └───────────────┬───────────────┘
                                          ▼ (4. receive, 5. re-check)
                          every site checks new anomalies against
                          its own model AND the pooled library
```

Research grounding: detection built on the SGCC dataset (Zheng et al.,
IEEE) and the EnsembleNTLDetect framework (Kulkarni et al., ICDMW 2021);
the shared store is framed on Google Research's Titans — test-time memory,
no retraining required.

## Team split and current status

| Owner | Component | Status |
|---|---|---|
| **Person 1** | **Detection — site split, per-site detector, isolated-vs-pooled number** | **done — see `detection/README.md`** |
| **Person 2** | **Policy & Abstraction — signature abstraction, Cedar policies, block-then-pass proof, decision logging** | **done — see `policy/README.md`** |
| **Person 3** | **Orchestration & Memory — the loop and the shared store** | **core logic done; Strands/live-OpenSearch wiring still open — see `orchestration/README.md`** |

All three components are wired together into one real, tested,
end-to-end pipeline — the isolation forest, the drift trigger, the real
Cedar gate, the shared pattern store, and the pooled re-check all run
through `orchestration/loop.py::run_swarm_cycle`, no mocking anywhere in
the chain:

```bash
py -3 -m pip install -r requirements.txt
py -3 -m pytest tests/ -v                    # 105 tests
py -3 scripts/demo_block_then_pass.py        # the on-screen block -> pass proof
py -3 scripts/run_isolated_vs_pooled.py      # the measured result, full swarm cycle
py -3 scripts/inspect_log.py                 # inspect every logged decision
```

**The measured result** (reproducible, see `detection/README.md` for why
`site_c_low_data` starts weak and why the drift filter matters):

```
site_c_low_data: isolated (before) detection_rate=33.3% (2/6 theft caught)
                 pooled   (after)  detection_rate=66.7% (4/6 theft caught)
                 +33.3 points, same site, same consumers, zero added false positives
```

(The well-resourced sites improve too — 93.3%→100% and 97.2%→100% — which
is the real "no central brain" swarm effect from section 3a working as
designed, not something tuned only for the low-data site.)

**What's still open for Person 3**: the loop above (`SiteAgent`,
`run_swarm_cycle`) and the shared store (`LocalPatternStore`,
`OpenSearchPatternStore`) are real, tested code — but each site still runs
as a plain Python object in one process on a fixed dataset, not a live
Strands agent watching a real OpenSearch cluster. Wrapping `SiteAgent`'s
methods as Strands tools needs real model credentials this environment
doesn't have; pointing `OpenSearchPatternStore` at a live cluster needs
Docker running (its daemon isn't up here). Both are documented, scoped,
one-call-site changes — see `orchestration/README.md`.

## Repo layout

```
tripwire/
  policy/            # Person 2 — done
    signature.py      # anomaly -> signature vector, strips identifiers
    gate.py            # PolicyGate: real Cedar authorization + logging
    decision_log.py    # append-only JSONL log + query/summarize
    policies/
      sharing.cedar       # the two Cedar rules
      sharing.cedarschema # the Cedar entity/action schema
  detection/         # Person 1 — done
    dataset.py         # synthetic SGCC-style sites, uneven volume
    features.py         # feature engineering, shared with policy/signature.py
    detector.py          # per-site IsolationForest
    drift.py              # the "surprise" trigger before sharing
    baseline.py            # detection_rate / precision / false_positive_rate
    pooled_recheck.py       # matches unflagged consumers against the pool
  orchestration/     # Person 3 — core loop done, Strands wiring open
    agent.py           # SiteAgent: one site's detect->share->recheck loop
    loop.py             # run_swarm_cycle: every site, one shared pool
  shared_store/      # Person 3 — local store done, live OpenSearch open
    store.py            # PatternStore, LocalPatternStore, OpenSearchPatternStore
  data/              # Person 1 — SGCC dataset split (gitignored raw files)
  tests/             # 105 tests, all against real code (real Cedar, real IsolationForest)
  scripts/
    demo_block_then_pass.py     # console demo of the block -> pass proof
    run_isolated_vs_pooled.py    # the measured result
    inspect_log.py                # decision log CLI
  requirements.txt
  pytest.ini
```

## Deliverables checklist (from the execution doc)

- [ ] Public GitHub repo, first commit dated 17 Sept, all three with push access
- [~] Working pipeline: detect → abstract → policy gate → shared store → improved detection, runnable end to end — works today against `LocalPatternStore` (`scripts/run_isolated_vs_pooled.py`); swapping in a live OpenSearch cluster and real Strands agents is the remaining infra work (`orchestration/README.md`)
- [x] One measured result: isolated vs. pooled detection rate on the low-data site — `scripts/run_isolated_vs_pooled.py`, 33.3% → 66.7%
- [x] Block-then-pass proof, logged and reproducible — `scripts/demo_block_then_pass.py`
- [ ] Three-minute demo video — real console output, not a UI
- [ ] README / write-up: problem, architecture, the number, what we learned, honest caveats
- [ ] Submitted Sunday afternoon, not at the deadline

## A note on the "first commit dated 17 Sept" rule

This code was written and tested ahead of the hackathon start (Pre-Thursday
checklist item: have things installed and a scope agreed in writing before
Thursday). If the actual submission repo requires its first commit to land
on 17 Sept, copy this `tripwire/` folder into that empty repo and make the
first commit there on the day — don't `git init` this folder as-is if doing
so would predate the required commit date.
