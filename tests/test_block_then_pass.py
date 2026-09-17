"""
Integration test for the block-then-pass proof — the one thing this
hackathon's demo has to show working: "a signature that leaks an ID gets
denied, a sanitised version gets permitted" (Tripwire_Execution_Doc.md,
Person 2's task list).

This test exercises the real chain: raw anomaly -> abstraction -> Cedar
authorization -> decision log, with no mocking anywhere in that chain. It's
deliberately the same shape as scripts/demo_block_then_pass.py so the
console demo and the test suite can't silently drift apart.
"""

from __future__ import annotations

import pytest

from policy.decision_log import summarize
from policy.gate import PolicyGate
from policy.signature import abstract_to_signature, abstract_to_signature_leaky, to_raw_payload

SITE_ID = "site_c_low_data"

RAW_ANOMALY = {
    "site_id": SITE_ID,
    "meter_id": "MTR-04821",
    "consumer_id": "CUST-99231",
    "household_type": "residential",
    "location": {"lat": 12.9, "lon": 77.6},
    "billing_cycle_day": 15,
    "detected_at": "2026-09-18T03:00:00Z",
    "anomaly_score": 0.91,
    "raw_series": [100, 102, 98, 101, 99, 100, 40, 38, 35, 34, 33, 32, 31, 30, 30],
}


@pytest.fixture()
def gate(tmp_path) -> PolicyGate:
    return PolicyGate(log_file=tmp_path / "decisions.jsonl")


def test_full_block_then_pass_sequence(gate: PolicyGate):
    # Step 0: the worst case — nobody abstracted anything at all.
    raw_decision = gate.evaluate_share_request(SITE_ID, to_raw_payload(RAW_ANOMALY))
    assert raw_decision.allowed is False

    # Step 1 ("block"): a site's abstraction has a bug and a signature still
    # carries the meter ID. The gate must deny it, and the denial reason
    # must name the actual leaked field so it's inspectable on screen.
    leaky_signature = abstract_to_signature_leaky(RAW_ANOMALY, "meter_id")
    block_decision = gate.evaluate_share_request(SITE_ID, leaky_signature)
    assert block_decision.allowed is False
    assert block_decision.decision == "Deny"
    assert "has_meter_id" in block_decision.reasons[0]

    # Step 2 ("pass"): the same underlying anomaly, abstracted correctly this
    # time. Same site, same anomaly, only the abstraction differs — this is
    # the direct before/after the execution doc calls for.
    clean_signature = abstract_to_signature(RAW_ANOMALY)
    pass_decision = gate.evaluate_share_request(SITE_ID, clean_signature)
    assert pass_decision.allowed is True
    assert pass_decision.decision == "Allow"

    # The log now holds a complete, reproducible record of exactly this
    # sequence — raw denied, leaky denied, clean permitted.
    records = gate.log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(records) == 3

    summary = summarize(gate.read_decisions())
    assert summary["total"] == 3
    assert summary["denied"] == 2
    assert summary["allowed"] == 1


def test_block_then_pass_holds_for_every_kind_of_leak(gate: PolicyGate):
    """The proof isn't a one-off for meter_id specifically — every identifying
    field independently blocks, and the same anomaly abstracted cleanly
    independently passes, regardless of which field a buggy site forgot."""
    for leak_field in ("meter_id", "consumer_id", "raw_series", "household_type", "location"):
        leaky = abstract_to_signature_leaky(RAW_ANOMALY, leak_field)
        blocked = gate.evaluate_share_request(SITE_ID, leaky)
        assert blocked.allowed is False, f"expected leak of {leak_field!r} to be denied"

    clean = abstract_to_signature(RAW_ANOMALY)
    passed = gate.evaluate_share_request(SITE_ID, clean)
    assert passed.allowed is True
