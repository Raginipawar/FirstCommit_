#!/usr/bin/env python3
"""
The live backend behind the "Live Run" section of the site.

This is not a mock server. Every endpoint imports and calls the exact same
modules `scripts/demo_block_then_pass.py` and `scripts/run_isolated_vs_pooled.py`
call — the real Cedar policy gate, the real IsolationForest detector, the
real drift filter, the real pooled re-check. Nothing here is pre-recorded.
Every request re-runs the pipeline from scratch and returns whatever it
actually produced. /api/run/gate always evaluates the same fixed
MOCK_ANOMALY fixture, so its three decisions are stable run to run. The
swarm-cycle endpoints (/api/run/swarm, /api/run/swarm/stream) draw a fresh
random seed offset every call (see `_randomized_configs`) so each click
of "Run TRIPWIRE now" generates a genuinely new synthetic dataset instead
of replaying the README's one fixed-seed number; the response's
`seed_offset` makes any individual run reproducible on request.

Run from the tripwire/ directory:

    py -3 -m pip install -r requirements.txt
    py -3 -m pip install fastapi "uvicorn[standard]"
    py -3 server.py

Then the frontend (vite dev server on :5173/:5174) can reach it at
http://localhost:8000.
"""

from __future__ import annotations

import json
import random
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any, Iterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from detection.baseline import DetectionMetrics, evaluate_detection
from detection.dataset import SITE_CONFIGS, generate_all_sites
from orchestration.agent import ShareRoundResult, SiteAgent
from orchestration.loop import run_swarm_cycle
from policy.decision_log import summarize
from policy.gate import PolicyGate
from policy.signature import abstract_to_signature, abstract_to_signature_leaky, to_raw_payload
from scripts.validate_across_seeds import LOW_DATA_SITE
from shared_store.store import LocalPatternStore

ROOT = Path(__file__).parent

app = FastAPI(title="TRIPWIRE live pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persists across requests (unlike the scratch gates the swarm-cycle
# endpoints use) so /api/decisions has a real, growing audit trail to read
# from within one server session — the same DecisionLogger every ALLOW/DENY
# from the block-then-pass demo actually gets appended to. Logs to
# policy/logs/decisions.jsonl (gitignored, see .gitignore).
PERSISTENT_GATE = PolicyGate()

SITE_ID = "site_c_low_data"

# Stands in for one flagged reading from the detector, same fixture used by
# scripts/demo_block_then_pass.py — a sharp, sustained load drop that never
# recovers to baseline.
MOCK_ANOMALY = {
    "site_id": SITE_ID,
    "meter_id": "MTR-04821",
    "consumer_id": "CUST-99231",
    "household_type": "residential",
    "location": {"lat": 12.9713, "lon": 77.5946},
    "billing_cycle_day": 12,
    "detected_at": "2026-09-18T03:00:00Z",
    "anomaly_score": 0.91,
    "raw_series": [101, 99, 103, 100, 98, 102, 41, 39, 36, 35, 34, 33, 32, 31, 30],
}


def _metrics_dict(m: DetectionMetrics) -> dict[str, Any]:
    return {
        "total_consumers": m.total_consumers,
        "total_theft": m.total_theft,
        "flagged": m.flagged,
        "true_positives": m.true_positives,
        "detection_rate": m.detection_rate,
        "precision": m.precision,
        "false_positive_rate": m.false_positive_rate,
    }


def _share_dict(r: ShareRoundResult) -> dict[str, Any]:
    return {
        "flagged": r.flagged,
        "drift_candidates": r.drift_candidates,
        "shared": r.shared,
        "denied": r.denied,
        "skipped": r.skipped,
    }


def _randomized_configs() -> tuple[tuple[Any, ...], int]:
    """A fresh random seed offset applied to every site, so 'Run TRIPWIRE
    now' produces a genuinely new dataset each click instead of the same
    fixed-seed numbers every time. The offset is returned alongside the
    configs so the response can say exactly which run this was —
    reproducible on request (same offset -> same result), not hidden."""
    offset = random.randint(0, 1_000_000)
    configs = tuple(replace(c, seed=c.seed + offset) for c in SITE_CONFIGS)
    return configs, offset


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "tripwire-live"}


@app.post("/api/run/gate")
def run_gate() -> dict[str, Any]:
    """Re-runs the exact block-then-pass proof, fresh, against the
    persistent decision log (PERSISTENT_GATE) so every click adds three
    more real, inspectable rows to /api/decisions instead of vanishing."""
    gate = PERSISTENT_GATE

    raw_payload = to_raw_payload(MOCK_ANOMALY)
    step0 = gate.evaluate_share_request(SITE_ID, raw_payload)

    leaky_signature = abstract_to_signature_leaky(MOCK_ANOMALY, "meter_id")
    step1 = gate.evaluate_share_request(SITE_ID, leaky_signature)

    clean_signature = abstract_to_signature(MOCK_ANOMALY)
    step2 = gate.evaluate_share_request(SITE_ID, clean_signature)

    decisions = gate.read_decisions()
    allowed = sum(1 for d in decisions if d["allowed"])
    denied = len(decisions) - allowed

    return {
        "site_id": SITE_ID,
        "raw_attempt": step0.to_dict(),
        "leaky_signature": {
            "granularity": leaky_signature.granularity,
            "decision": step1.to_dict(),
        },
        "clean_signature": {
            "granularity": clean_signature.granularity,
            "load_drop_magnitude_bucket": clean_signature.load_drop_magnitude_bucket,
            "timing_bucket": clean_signature.timing_bucket,
            "recovery_shape": clean_signature.recovery_shape,
            "decision": step2.to_dict(),
        },
        "summary": {"total": len(decisions), "allowed": allowed, "denied": denied},
    }


@app.get("/api/decisions")
def get_decisions() -> dict[str, Any]:
    """The full audit trail so far this server session — every ALLOW/DENY
    logged by PERSISTENT_GATE, oldest first, plus the rolled-up counters
    from policy/decision_log.py::summarize()."""
    records = PERSISTENT_GATE.read_decisions()
    return {"records": records, "summary": summarize(records)}


@app.post("/api/decisions/clear")
def clear_decisions() -> dict[str, str]:
    """Truncates the persistent decision log — lets a demo reset between
    runs without restarting the server."""
    PERSISTENT_GATE.log_path.write_text("", encoding="utf-8")
    return {"status": "cleared"}


@app.post("/api/run/swarm")
def run_swarm() -> dict[str, Any]:
    """Re-runs the full detect -> share -> re-check cycle across all three
    sites, fresh, against a scratch pool so repeated clicks don't compound."""
    with tempfile.TemporaryDirectory() as tmp:
        gate = PolicyGate(log_file=Path(tmp) / "decisions.jsonl")
        store = LocalPatternStore(Path(tmp) / "pool.jsonl")

        configs, seed_offset = _randomized_configs()
        result = run_swarm_cycle(gate, store, configs)

        sites = {}
        for config in configs:
            site_id = config.site_id
            sites[site_id] = {
                "n_consumers": config.n_consumers,
                "assumed_contamination": config.assumed_contamination,
                "true_theft_rate": config.theft_rate,
                "isolated": _metrics_dict(result.isolated_metrics[site_id]),
                "pooled": _metrics_dict(result.pooled_metrics[site_id]),
                "share": _share_dict(result.share_results[site_id]),
            }

        return {"sites": sites, "pool_size": result.pool_size, "seed_offset": seed_offset}


def _sse(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event)}\n\n"


@app.get("/api/run/swarm/stream")
def run_swarm_stream() -> StreamingResponse:
    """Same swarm cycle as /api/run/swarm, but instrumented to emit one SSE
    event per site per phase as it actually happens — detect, then share
    (drift-filter + abstract + Cedar gate), then, once every site has
    shared, the pooled re-check. This is what Screen 2's pipeline diagram
    animates against: each event corresponds to a real call into
    orchestration/agent.py::SiteAgent, not a scripted delay."""

    def events() -> Iterator[str]:
        configs, seed_offset = _randomized_configs()
        with tempfile.TemporaryDirectory() as tmp:
            gate = PolicyGate(log_file=Path(tmp) / "decisions.jsonl")
            store = LocalPatternStore(Path(tmp) / "pool.jsonl")

            sites_data = generate_all_sites(configs)
            agents = {
                c.site_id: SiteAgent(c, sites_data[c.site_id], gate, store)
                for c in configs
            }

            isolated_metrics = {}
            share_results = {}

            for site_id, agent in agents.items():
                flagged = agent.detect()
                isolated_metrics[site_id] = evaluate_detection(
                    sites_data[site_id], agent.isolated_flag_ids()
                )
                yield _sse({"phase": "detect", "site_id": site_id, "flagged": len(flagged)})

                share = agent.share_round(flagged)
                share_results[site_id] = share
                yield _sse(
                    {
                        "phase": "share",
                        "site_id": site_id,
                        "drift_candidates": share.drift_candidates,
                        "shared": share.shared,
                        "denied": share.denied,
                    }
                )

            pooled_metrics = {}
            for site_id, agent in agents.items():
                pooled_ids = agent.receive_and_recheck()
                pooled_metrics[site_id] = evaluate_detection(sites_data[site_id], pooled_ids)
                yield _sse(
                    {
                        "phase": "recheck",
                        "site_id": site_id,
                        "pooled_flagged": len(pooled_ids),
                    }
                )

            sites_out = {}
            for config in configs:
                site_id = config.site_id
                sites_out[site_id] = {
                    "n_consumers": config.n_consumers,
                    "assumed_contamination": config.assumed_contamination,
                    "true_theft_rate": config.theft_rate,
                    "isolated": _metrics_dict(isolated_metrics[site_id]),
                    "pooled": _metrics_dict(pooled_metrics[site_id]),
                    "share": _share_dict(share_results[site_id]),
                }

            yield _sse(
                {
                    "phase": "done",
                    "result": {
                        "sites": sites_out,
                        "pool_size": store.count(),
                        "seed_offset": seed_offset,
                    },
                }
            )

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/api/validate/stream")
def validate_stream(n_seeds: int = 8) -> StreamingResponse:
    """Runs the real swarm cycle `n_seeds` times, each with every site's
    seed offset by one more, and streams one SSE event per completed seed
    plus a final aggregate — scripts/validate_across_seeds.py's method,
    exposed live. Capped at 20 seeds; each seed re-fits three real
    IsolationForests, so this genuinely takes a few seconds per seed."""
    n_seeds = max(1, min(n_seeds, 20))

    def events() -> Iterator[str]:
        per_seed = []
        fpr_ever_worse = False

        for offset in range(n_seeds):
            configs = tuple(
                replace(c, seed=c.seed + offset) for c in SITE_CONFIGS
            )
            with tempfile.TemporaryDirectory() as tmp:
                gate = PolicyGate(log_file=Path(tmp) / "decisions.jsonl")
                store = LocalPatternStore(Path(tmp) / "pool.jsonl")
                result = run_swarm_cycle(gate, store, configs)

                site_records = {}
                for site_id in result.isolated_metrics:
                    isolated = result.isolated_metrics[site_id]
                    pooled = result.pooled_metrics[site_id]
                    if pooled.false_positive_rate > isolated.false_positive_rate:
                        fpr_ever_worse = True
                    site_records[site_id] = {
                        "isolated_detection_rate": isolated.detection_rate,
                        "pooled_detection_rate": pooled.detection_rate,
                        "improvement": pooled.detection_rate - isolated.detection_rate,
                        "isolated_false_positive_rate": isolated.false_positive_rate,
                        "pooled_false_positive_rate": pooled.false_positive_rate,
                    }

                low = site_records[LOW_DATA_SITE]
                record = {
                    "seed_offset": offset,
                    "sites": site_records,
                    "low_data_improvement": low["improvement"],
                }
                per_seed.append(record)
                yield _sse({"phase": "seed", **record})

        improvements = [r["low_data_improvement"] for r in per_seed]
        aggregate = {
            "n_seeds": n_seeds,
            "low_data_site": LOW_DATA_SITE,
            "mean_improvement": sum(improvements) / len(improvements),
            "min_improvement": min(improvements),
            "max_improvement": max(improvements),
            "false_positive_rate_ever_worse_pooled": fpr_ever_worse,
        }
        yield _sse({"phase": "done", "per_seed": per_seed, "aggregate": aggregate})

    return StreamingResponse(events(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
