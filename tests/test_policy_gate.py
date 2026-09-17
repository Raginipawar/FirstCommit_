"""Unit tests for the Cedar policy gate (policy/gate.py).

Uses the real Cedar engine via cedarpy — no mocking of the authorization
decision itself. Every test points the gate at a scratch log file (via
`tmp_path`) so test runs never touch or depend on policy/logs/decisions.jsonl.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from policy.gate import PolicyDecision, PolicyGate
from policy.signature import (
    GRANULARITY_THRESHOLD,
    abstract_to_signature,
    abstract_to_signature_leaky,
    to_raw_payload,
)

RAW_ANOMALY = {
    "site_id": "site_c_low_data",
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


def test_clean_signature_is_allowed(gate: PolicyGate):
    sig = abstract_to_signature(RAW_ANOMALY)
    decision = gate.evaluate_share_request("site_c_low_data", sig)
    assert decision.allowed is True
    assert decision.decision == "Allow"
    assert "policy1" in decision.matched_policies or len(decision.matched_policies) >= 1


def test_leaky_signature_is_denied(gate: PolicyGate):
    sig = abstract_to_signature_leaky(RAW_ANOMALY, "meter_id")
    decision = gate.evaluate_share_request("site_c_low_data", sig)
    assert decision.allowed is False
    assert decision.decision == "Deny"
    assert "has_meter_id" in decision.reasons[0]


@pytest.mark.parametrize(
    "leak_field",
    ["meter_id", "consumer_id", "raw_series", "household_type", "location"],
)
def test_every_leak_field_is_independently_denied(gate: PolicyGate, leak_field):
    sig = abstract_to_signature_leaky(RAW_ANOMALY, leak_field)
    decision = gate.evaluate_share_request("site_c_low_data", sig)
    assert decision.allowed is False


def test_raw_record_is_denied_outright(gate: PolicyGate):
    raw = to_raw_payload(RAW_ANOMALY)
    decision = gate.evaluate_share_request("site_c_low_data", raw)
    assert decision.allowed is False
    assert decision.decision == "Deny"


def test_every_decision_is_logged(gate: PolicyGate):
    sig = abstract_to_signature(RAW_ANOMALY)
    gate.evaluate_share_request("site_c_low_data", sig)

    leaky = abstract_to_signature_leaky(RAW_ANOMALY, "meter_id")
    gate.evaluate_share_request("site_c_low_data", leaky)

    assert gate.log_path.exists()
    lines = gate.log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_denial_log_never_contains_the_raw_identifier_value(gate: PolicyGate):
    sig = abstract_to_signature_leaky(RAW_ANOMALY, "meter_id")
    gate.evaluate_share_request("site_c_low_data", sig)

    log_contents = gate.log_path.read_text(encoding="utf-8")
    assert "MTR-04821" not in log_contents
    assert "has_meter_id" in log_contents


def test_decision_is_reproducible_for_the_same_payload(gate: PolicyGate):
    sig = abstract_to_signature(RAW_ANOMALY)
    d1 = gate.evaluate_share_request("site_c_low_data", sig)
    d2 = gate.evaluate_share_request("site_c_low_data", sig)
    assert d1.allowed == d2.allowed == True


def test_str_representation_is_readable(gate: PolicyGate):
    sig = abstract_to_signature(RAW_ANOMALY)
    decision = gate.evaluate_share_request("site_c_low_data", sig)
    text = str(decision)
    assert "ALLOW" in text
    assert "site_c_low_data" in text
    assert sig.signature_id in text


def test_threshold_matches_code():
    """policy/policies/sharing.cedar and policy/signature.py must not drift.

    Cedar policies can't reference a shared Python constant, so the
    threshold is a literal in the .cedar file. This test is the guardrail:
    if someone changes GRANULARITY_THRESHOLD without updating the policy
    (or vice versa), this fails loudly instead of the numbers silently
    disagreeing.
    """
    cedar_text = (Path(__file__).parents[1] / "policy" / "policies" / "sharing.cedar").read_text()
    match = re.search(r"resource\.granularity\s*<=\s*(\d+)", cedar_text)
    assert match, "could not find the granularity threshold in sharing.cedar"
    assert int(match.group(1)) == GRANULARITY_THRESHOLD
