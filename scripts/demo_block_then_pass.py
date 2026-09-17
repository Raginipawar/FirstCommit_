#!/usr/bin/env python3
"""
Console demo: the block-then-pass proof, on screen, using the real Cedar
policy engine. This is Person 2's slice of the "What the Demo Shows" section
of Tripwire_Execution_Doc.md:

    "It generates a theft signature, and that signature has to pass a
    policy check before it can be shared: if it still carries a customer
    ID, it gets blocked on screen, gets rewritten, and the clean version
    passes through."

Run it from the tripwire/ directory:

    py -3 scripts/demo_block_then_pass.py

There is no mocking of the Cedar decision anywhere in this script — the
ALLOW/DENY you see is the real `cedarpy.is_authorized` result against
policy/policies/sharing.cedar.

This script stands in for Person 1's detector with a hand-written anomaly
(see MOCK_ANOMALY below) and stops at the policy gate — it does not touch
the shared store or re-run detection, since standing up OpenSearch and
wiring the full detect -> abstract -> share -> receive -> re-check loop is
Person 3's task (Tripwire_Execution_Doc.md, Person 3 - Orchestration &
Memory). Swap MOCK_ANOMALY for Person 1's real detector output once it
exists; nothing else in this script needs to change.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

try:  # Windows terminals often default to a legacy codepage that can't
    sys.stdout.reconfigure(encoding="utf-8")  # render non-ASCII paths or the
except AttributeError:  # em-dashes used throughout this script's output.
    pass

sys.path.insert(0, str(Path(__file__).parents[1]))

from policy.decision_log import summarize
from policy.gate import PolicyGate
from policy.signature import abstract_to_signature, abstract_to_signature_leaky, to_raw_payload

SITE_ID = "site_c_low_data"

# Stands in for one flagged reading from Person 1's detector: a sharp,
# sustained load drop starting a few days before the billing boundary that
# never recovers to baseline -- a classic tamper-consistent shape.
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


def _pause(seconds: float = 0.6) -> None:
    if "--fast" not in sys.argv:
        time.sleep(seconds)


def _header(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def main() -> int:
    log_file = Path(__file__).parents[1] / "policy" / "logs" / "decisions.jsonl"
    gate = PolicyGate(log_file=log_file)

    _header("TRIPWIRE — Policy & Abstraction demo (Person 2)")
    print(f"site        : {SITE_ID}")
    print(f"policy file : policy/policies/sharing.cedar")
    print(f"schema file : policy/policies/sharing.cedarschema")
    print(f"log file    : {gate.log_path}")
    _pause()

    _header("STEP 0 — an untouched detector output tries to share directly")
    raw_payload = to_raw_payload(MOCK_ANOMALY)
    print(f"payload kind = {raw_payload.kind!r}, granularity = {raw_payload.granularity}")
    _pause(0.3)
    decision0 = gate.evaluate_share_request(SITE_ID, raw_payload)
    print(decision0)
    print(f"  reason: {decision0.reasons[0]}")
    assert not decision0.allowed, "raw records must never be permitted"
    _pause()

    _header("STEP 1 — BLOCK: a buggy abstraction leaves the meter ID attached")
    leaky_signature = abstract_to_signature_leaky(MOCK_ANOMALY, "meter_id")
    print(f"payload kind = {leaky_signature.kind!r}, granularity = {leaky_signature.granularity}")
    _pause(0.3)
    decision1 = gate.evaluate_share_request(SITE_ID, leaky_signature)
    print(decision1)
    print(f"  reason: {decision1.reasons[0]}")
    assert not decision1.allowed, "a signature carrying a meter ID must be denied"
    print("  >>> BLOCKED ON SCREEN — this signature does not leave the site.")
    _pause()

    _header("STEP 2 — rewrite: strip the identifier, re-abstract properly")
    clean_signature = abstract_to_signature(MOCK_ANOMALY)
    print(f"payload kind = {clean_signature.kind!r}, granularity = {clean_signature.granularity}")
    print(f"  load_drop_magnitude_bucket = {clean_signature.load_drop_magnitude_bucket}")
    print(f"  timing_bucket              = {clean_signature.timing_bucket}")
    print(f"  recovery_shape             = {clean_signature.recovery_shape}")
    _pause()

    _header("STEP 3 — PASS: the sanitised signature clears the gate")
    decision2 = gate.evaluate_share_request(SITE_ID, clean_signature)
    print(decision2)
    print(f"  reason: {decision2.reasons[0]}")
    assert decision2.allowed, "a correctly abstracted signature must be permitted"
    print("  >>> PASSED — eligible for the shared pattern store.")
    _pause()

    _header("Decision log summary (policy/logs/decisions.jsonl)")
    summary = summarize(gate.read_decisions())
    print(f"total checked : {summary['total']}")
    print(f"allowed       : {summary['allowed']}")
    print(f"denied        : {summary['denied']}")
    print(f"denial reasons: {summary['denial_reasons']}")
    print()
    print("Same anomaly, same site — the only thing that changed between the")
    print("BLOCK and the PASS is whether the abstraction actually stripped the")
    print("identifying field. That's the proof Cedar enforces the boundary by")
    print("rule, not by promise.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
