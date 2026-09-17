"""Unit tests for the decision log (policy/decision_log.py)."""

from __future__ import annotations

import pytest

from policy.decision_log import DecisionLogger, filter_records, iter_records, summarize
from policy.gate import PolicyDecision


def _decision(site_id="site_a", allowed=True, kind="signature", reasons=("ok",)):
    return PolicyDecision(
        allowed=allowed,
        decision="Allow" if allowed else "Deny",
        site_id=site_id,
        resource_id="sig-test",
        kind=kind,
        granularity=5,
        matched_policies=("policy1",) if allowed else ("policy0",),
        errors=(),
        reasons=reasons,
        checked_at="2026-09-18T00:00:00Z",
        payload_attrs={"kind": kind, "granularity": 5},
    )


def test_log_appends_one_line_per_decision(tmp_path):
    logger = DecisionLogger(tmp_path / "decisions.jsonl")
    logger.log(_decision())
    logger.log(_decision(allowed=False))
    lines = logger.log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_read_all_round_trips_decisions(tmp_path):
    logger = DecisionLogger(tmp_path / "decisions.jsonl")
    logger.log(_decision(site_id="site_a"))
    logger.log(_decision(site_id="site_b", allowed=False))
    records = logger.read_all()
    assert len(records) == 2
    assert records[0]["site_id"] == "site_a"
    assert records[1]["site_id"] == "site_b"
    assert records[1]["allowed"] is False


def test_read_all_on_missing_file_returns_empty_list(tmp_path):
    logger = DecisionLogger(tmp_path / "does_not_exist.jsonl")
    assert logger.read_all() == []


def test_clear_truncates_the_log(tmp_path):
    logger = DecisionLogger(tmp_path / "decisions.jsonl")
    logger.log(_decision())
    logger.clear()
    assert logger.read_all() == []


def test_iter_records_streams_same_data_as_read_all(tmp_path):
    logger = DecisionLogger(tmp_path / "decisions.jsonl")
    logger.log(_decision())
    logger.log(_decision(allowed=False))
    assert list(iter_records(logger.log_path)) == logger.read_all()


def test_filter_records_by_site_and_decision(tmp_path):
    logger = DecisionLogger(tmp_path / "decisions.jsonl")
    logger.log(_decision(site_id="site_a", allowed=True))
    logger.log(_decision(site_id="site_a", allowed=False))
    logger.log(_decision(site_id="site_b", allowed=True))

    records = logger.read_all()
    assert len(filter_records(records, site_id="site_a")) == 2
    assert len(filter_records(records, decision="deny")) == 1
    assert len(filter_records(records, site_id="site_a", decision="allow")) == 1


def test_summarize_counts_allow_and_deny(tmp_path):
    logger = DecisionLogger(tmp_path / "decisions.jsonl")
    logger.log(_decision(allowed=True))
    logger.log(_decision(allowed=True))
    logger.log(_decision(allowed=False, reasons=("identifying field(s) present: has_meter_id",)))

    summary = summarize(logger.read_all())
    assert summary["total"] == 3
    assert summary["allowed"] == 2
    assert summary["denied"] == 1
    assert summary["allow_rate"] == pytest.approx(2 / 3)


def test_summarize_tracks_matched_policy_counts(tmp_path):
    logger = DecisionLogger(tmp_path / "decisions.jsonl")
    logger.log(_decision(allowed=True))
    logger.log(_decision(allowed=False))

    summary = summarize(logger.read_all())
    assert summary["matched_policy_counts"]["policy1"] == 1
    assert summary["matched_policy_counts"]["policy0"] == 1
