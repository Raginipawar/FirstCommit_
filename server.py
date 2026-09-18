#!/usr/bin/env python3
"""
The live backend behind the "Live Run" section of the site.

This is not a mock server. Every endpoint imports and calls the exact same
modules `scripts/demo_block_then_pass.py` and `scripts/run_isolated_vs_pooled.py`
call — the real Cedar policy gate, the real IsolationForest detector, the
real drift filter, the real pooled re-check. Nothing here is pre-recorded.
Every request re-runs the pipeline from scratch and returns whatever it
actually produced, which — because `detection/dataset.py` seeds its
per-site random generators — will be the same real numbers the README
documents, every time, unless the underlying detection code changes.

Run from the tripwire/ directory:

    py -3 -m pip install -r requirements.txt
    py -3 -m pip install fastapi "uvicorn[standard]"
    py -3 server.py

Then the frontend (vite dev server on :5173/:5174) can reach it at
http://localhost:8000.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from detection.baseline import DetectionMetrics
from detection.dataset import SITE_CONFIGS
from orchestration.agent import ShareRoundResult
from orchestration.loop import run_swarm_cycle
from policy.gate import PolicyGate
from policy.signature import abstract_to_signature, abstract_to_signature_leaky, to_raw_payload
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


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "tripwire-live"}


@app.post("/api/run/gate")
def run_gate() -> dict[str, Any]:
    """Re-runs the exact block-then-pass proof, fresh, against a scratch log
    file so repeated demo clicks don't pile up on top of each other."""
    with tempfile.TemporaryDirectory() as tmp:
        gate = PolicyGate(log_file=Path(tmp) / "decisions.jsonl")

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


@app.post("/api/run/swarm")
def run_swarm() -> dict[str, Any]:
    """Re-runs the full detect -> share -> re-check cycle across all three
    sites, fresh, against a scratch pool so repeated clicks don't compound."""
    with tempfile.TemporaryDirectory() as tmp:
        gate = PolicyGate(log_file=Path(tmp) / "decisions.jsonl")
        store = LocalPatternStore(Path(tmp) / "pool.jsonl")

        result = run_swarm_cycle(gate, store)

        sites = {}
        for config in SITE_CONFIGS:
            site_id = config.site_id
            sites[site_id] = {
                "n_consumers": config.n_consumers,
                "assumed_contamination": config.assumed_contamination,
                "true_theft_rate": config.theft_rate,
                "isolated": _metrics_dict(result.isolated_metrics[site_id]),
                "pooled": _metrics_dict(result.pooled_metrics[site_id]),
                "share": _share_dict(result.share_results[site_id]),
            }

        return {"sites": sites, "pool_size": result.pool_size}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
