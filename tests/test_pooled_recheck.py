"""Unit + integration tests for the pooled re-check mechanism (detection/pooled_recheck.py)."""

from __future__ import annotations

from detection.baseline import evaluate_detection
from detection.dataset import SITE_CONFIGS, generate_all_sites
from detection.detector import SiteDetector
from detection.drift import filter_for_sharing
from detection.features import extract_all, to_anomaly_record
from detection.pooled_recheck import build_pattern_index, recheck_against_pool
from policy.gate import PolicyGate
from policy.signature import AbstractionError, abstract_to_signature

LOW_DATA_SITE = "site_c_low_data"


def test_build_pattern_index_extracts_shape_keys():
    pooled = [
        {
            "load_drop_magnitude_bucket": 3,
            "drop_duration_bucket": 2,
            "timing_bucket": "mid-cycle",
            "recovery_shape": "step",
            "volatility_bucket": 1,
            "signature_id": "sig-1",
        }
    ]
    index = build_pattern_index(pooled)
    assert index == {(3, 2, "mid-cycle", "step", 1)}


def test_build_pattern_index_ignores_malformed_entries():
    index = build_pattern_index([{"not": "a signature"}])
    assert index == set()


def test_recheck_never_removes_an_existing_flag():
    features = extract_all(generate_all_sites()[LOW_DATA_SITE])
    all_ids = {cf.consumer.consumer_id for cf in features}
    already_flagged = set(list(all_ids)[:5])
    updated = recheck_against_pool(features, already_flagged, pattern_index=set())
    assert already_flagged <= updated


def test_recheck_with_empty_pool_changes_nothing():
    features = extract_all(generate_all_sites()[LOW_DATA_SITE])
    already_flagged = {features[0].consumer.consumer_id}
    updated = recheck_against_pool(features, already_flagged, pattern_index=set())
    assert updated == already_flagged


def test_recheck_can_add_a_consumer_whose_shape_matches_the_pool():
    sites = generate_all_sites()
    features = extract_all(sites[LOW_DATA_SITE])
    target = next(cf for cf in features if cf.consumer.is_theft)
    anomaly = to_anomaly_record(target.consumer, target.features, anomaly_score=1.0)
    signature = abstract_to_signature(anomaly)
    pattern_index = {signature.shape_key()}

    updated = recheck_against_pool(features, already_flagged_ids=set(), pattern_index=pattern_index)
    assert target.consumer.consumer_id in updated


class TestFullPipelineOnRealSyntheticData:
    """End-to-end: real dataset, real IsolationForest, real Cedar gate, real
    drift filter, real pooled re-check. Pinned to the fixed seeds in
    detection/dataset.py::SITE_CONFIGS, so this is deterministic."""

    def test_pooled_detection_rate_is_at_least_the_isolated_rate(self, tmp_path):
        configs_by_id = {c.site_id: c for c in SITE_CONFIGS}
        sites = generate_all_sites()
        site_features = {sid: extract_all(cs) for sid, cs in sites.items()}

        detector_flags = {}
        isolated_flag_ids = {}
        for site_id, consumers in sites.items():
            detector = SiteDetector(contamination=configs_by_id[site_id].assumed_contamination)
            detector.fit(site_features[site_id])
            flagged = detector.flag_anomalies(site_features[site_id])
            detector_flags[site_id] = flagged
            isolated_flag_ids[site_id] = {f.consumer.consumer_id for f in flagged}

        gate = PolicyGate(log_file=tmp_path / "decisions.jsonl")
        pooled_signatures = []
        for site_id in ("site_a", "site_b"):
            for anomaly in filter_for_sharing(detector_flags[site_id]):
                record = to_anomaly_record(anomaly.consumer, anomaly.features, anomaly.anomaly_score)
                try:
                    signature = abstract_to_signature(record)
                except AbstractionError:
                    continue
                decision = gate.evaluate_share_request(site_id, signature)
                if decision.allowed:
                    pooled_signatures.append(signature.to_dict())

        pattern_index = build_pattern_index(pooled_signatures)
        pooled_flag_ids = recheck_against_pool(
            site_features[LOW_DATA_SITE], isolated_flag_ids[LOW_DATA_SITE], pattern_index
        )

        isolated_metrics = evaluate_detection(sites[LOW_DATA_SITE], isolated_flag_ids[LOW_DATA_SITE])
        pooled_metrics = evaluate_detection(sites[LOW_DATA_SITE], pooled_flag_ids)

        assert pooled_metrics.detection_rate >= isolated_metrics.detection_rate
        # This is the actual headline result (see scripts/run_isolated_vs_pooled.py) --
        # pinned here so a change that quietly breaks it fails the suite, not just the demo.
        assert isolated_metrics.detection_rate < 0.5, "expected the low-data site's isolated baseline to be weak"
        assert pooled_metrics.detection_rate > isolated_metrics.detection_rate, (
            "expected pooling to visibly improve the low-data site's detection rate"
        )
        # No false-positive cost: the drift filter should keep the pool clean.
        assert pooled_metrics.false_positive_rate == 0.0
