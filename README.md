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
by promise. Full background: `../ps_approach/Tripwire_Execution_Doc.md`
and `../ps_approach/TeamSaturn_ProjectBrief_DISCOM.pdf`.

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
IEEE) — not just grounded on it, actually validated against the real
downloaded dataset (`detection/real_pipeline.py`), not only a synthetic
stand-in — and the EnsembleNTLDetect framework (Kulkarni et al., ICDMW
2021); the shared store is framed on Google Research's Titans — test-time
memory, no retraining required.

Implementation status behind this diagram, stated plainly: "Strands
agent" is real for both sites via `orchestration/strands_agent.py`
(`scripts/run_strands_swarm.py` runs it), but the fast, deterministic
plain-loop path (`orchestration/loop.py`) is what the website's live
backend actually calls. "Shared OpenSearch pattern store" is not yet
live anywhere — `shared_store/store.py::LocalPatternStore`, a JSONL
file behind the identical interface, is what every path above actually
runs against. See `orchestration/README.md` for the full, current
account of both. The diagram's per-site detector is drawn once for
simplicity; in practice there are two working detectors behind it — a
synthetic-data `IsolationForest` and a real-SGCC-data
`RandomForestClassifier` — see `detection/README.md`, "The real-data
path."

## Team split and current status

| Owner | Component | Status |
|---|---|---|
| **Person 1** | **Detection — site split, per-site detector, isolated-vs-pooled number** | **done — see `detection/README.md`** |
| **Person 2** | **Policy & Abstraction — signature abstraction, Cedar policies, block-then-pass proof, decision logging** | **done — see `policy/README.md`** |
| **Person 3** | **Orchestration & Memory — the loop and the shared store** | **core logic done; Strands wiring done and tested; live OpenSearch genuinely blocked by this host, not unattempted — see `orchestration/README.md`** |

All three components are wired together into one real, tested,
end-to-end pipeline — the isolation forest, the drift trigger, the real
Cedar gate, the shared pattern store, and the pooled re-check all run
through `orchestration/loop.py::run_swarm_cycle`, no mocking anywhere in
the chain:

```bash
py -3 -m pip install -r requirements.txt
py -3 -m pytest tests/ -v                    # 149 tests (106 synthetic-path + 43 real-data-path)
py -3 scripts/demo_block_then_pass.py        # the on-screen block -> pass proof
py -3 scripts/run_isolated_vs_pooled.py      # the measured result, full swarm cycle
py -3 scripts/inspect_log.py                 # inspect every logged decision

# optional — the same swarm cycle, orchestrated by a real Strands agent
# instead of a plain loop (needs Ollama + `ollama pull qwen2.5:1.5b` first,
# see orchestration/README.md, "Gap 1"):
py -3 scripts/run_strands_swarm.py

# optional — the real SGCC dataset instead of the synthetic stand-in
# (needs it downloaded locally first, see data/README.md):
py -3 scripts/run_real_sgcc_pipeline.py "C:\path\to\data set.csv"
```

**The measured result, synthetic data** (reproducible, see
`detection/README.md` for why `site_c_low_data` starts weak and why the
drift filter matters):

```
site_c_low_data: isolated (before) detection_rate=33.3% (2/6 theft caught)
                 pooled   (after)  detection_rate=66.7% (4/6 theft caught)
                 +33.3 points, same site, same consumers, zero added false positives
```

(The well-resourced sites improve too — 93.3%→100% and 97.2%→100% — which
is the real "no central brain" swarm effect from section 3a working as
designed, not something tuned only for the low-data site.)

**The measured result, real SGCC data** (the actual published dataset —
42,372 real consumers, real theft labels; see `detection/README.md`,
"The real-data path," for the full account including why this needed a
supervised classifier instead of an isolation forest):

```
site_c_low_data: isolated (before) detection_rate=35.3% (6/17 theft caught), trained on 41 real theft cases
                 pooled   (after)  detection_rate=64.7% (11/17 theft caught)
                 +29.4 points, on real held-out SGCC test consumers
```

Unlike the synthetic result, this one has a real, disclosed cost: precision
drops from 26.1% to 20.4% (real, noisy data doesn't offer a free lunch).
Stated plainly rather than hidden — see `detection/README.md` for why
that's arguably the more credible of the two numbers.

**What's still open for Person 3**: one of the original two gaps is
closed. `orchestration/strands_agent.py` wraps `SiteAgent` as real
`@tool` functions behind a real `strands.Agent`, backed by a local Ollama
model (no cloud credentials were available) — `scripts/run_strands_swarm.py`
reproduces the exact same 33.3%→66.7% result via genuine LLM tool-calling,
not a fixed loop. The live OpenSearch cluster is still open, and this time
that's a verified, host-level blocker: Docker Desktop is installed here,
but this Windows install runs inside a hypervisor with no nested
virtualization exposed to it, so its daemon can't start regardless of
what gets installed. `LocalPatternStore` remains the tested, working
store both paths run against. Full account of both — see
`orchestration/README.md`.

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
  detection/         # Person 1 — done, two parallel paths
    dataset.py         # synthetic SGCC-style sites, uneven volume
    features.py         # feature engineering, shared with policy/signature.py
    detector.py          # per-site IsolationForest (synthetic path)
    drift.py              # the "surprise" trigger before sharing (synthetic path)
    baseline.py            # detection_rate / precision / false_positive_rate (both paths)
    pooled_recheck.py       # matches unflagged consumers against the pool (synthetic path)
    real_dataset.py          # loads the real SGCC CSV, splits into 3 uneven sites
    real_features.py          # real-data feature engineering (spurious zeros, 1034-day scale)
    real_detector.py           # per-site RandomForestClassifier (real-data path)
    real_pipeline.py            # real-data detect -> share -> re-check, via Person 2's real Cedar gate
  orchestration/     # Person 3 — core loop + Strands wiring done, live OpenSearch open
    agent.py           # SiteAgent: one site's detect->share->recheck loop
    loop.py             # run_swarm_cycle: every site, one shared pool (fast, deterministic; what the website runs)
    strands_agent.py     # the same cycle, orchestrated by a real strands.Agent + local Ollama model
  shared_store/      # Person 3 — local store done, live OpenSearch blocked at the host level
    store.py            # PatternStore, LocalPatternStore, OpenSearchPatternStore
  data/              # Person 1 — synthetic + real SGCC dataset (gitignored raw files)
  tests/             # 149 tests, all against real code (real Cedar, real IsolationForest,
                     # real RandomForestClassifier on real data, real Strands+Ollama)
  scripts/
    demo_block_then_pass.py     # console demo of the block -> pass proof
    run_isolated_vs_pooled.py    # the measured result, synthetic data, plain-loop orchestration
    run_strands_swarm.py          # the measured result again, Strands-agent orchestration
    run_real_sgcc_pipeline.py      # the measured result on the real SGCC dataset
    inspect_log.py                  # decision log CLI
  server.py          # FastAPI backend behind the website's "Live Run" section
  requirements.txt
  pytest.ini
```

## Deliverables checklist (from the execution doc)

- [ ] Public GitHub repo, first commit dated 17 Sept, all three with push access
- [x] Working pipeline: detect → abstract → policy gate → shared store → improved detection, runnable end to end — against `LocalPatternStore`, both via a plain loop (`scripts/run_isolated_vs_pooled.py`) and via a real Strands agent (`scripts/run_strands_swarm.py`); swapping in a live OpenSearch cluster is blocked by this host's lack of nested virtualization, not left undone (`orchestration/README.md`, "Gap 2")
- [x] One measured result: isolated vs. pooled detection rate on the low-data site — synthetic: `scripts/run_isolated_vs_pooled.py`/`run_strands_swarm.py` agree, 33.3%→66.7%; **real SGCC data**: `scripts/run_real_sgcc_pipeline.py`, 35.3%→64.7%
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
