"""Unit tests for the abstraction layer (policy/signature.py)."""

from __future__ import annotations

import pytest

from policy.signature import (
    GRANULARITY_THRESHOLD,
    AbstractionError,
    abstract_to_signature,
    abstract_to_signature_leaky,
    compute_granularity,
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
    # A load-shape that drops sharply around day 10 and never fully recovers:
    "raw_series": [100, 102, 98, 101, 99, 100, 40, 38, 35, 34, 33, 32, 31, 30, 30],
}

PRECOMPUTED_ANOMALY = {
    "site_id": "site_a",
    "detected_at": "2026-09-18T03:00:00Z",
    "anomaly_score": 0.6,
    "billing_cycle_day": 3,
    "load_drop_magnitude": 0.5,
    "drop_duration_days": 6,
    "recovery_time_days": 1,
    "volatility": 0.05,
}


class TestAbstractToSignature:
    def test_strips_every_identifying_field(self):
        sig = abstract_to_signature(RAW_ANOMALY)
        assert sig.has_meter_id is False
        assert sig.has_consumer_id is False
        assert sig.has_raw_series is False
        assert sig.has_household_field is False
        assert sig.has_location is False

        payload_attrs = sig.to_payload_attrs()
        for key in ("has_meter_id", "has_consumer_id", "has_raw_series",
                    "has_household_field", "has_location"):
            assert payload_attrs[key] is False

    def test_never_carries_raw_identifiers_in_its_own_dict(self):
        sig = abstract_to_signature(RAW_ANOMALY)
        signature_dict = sig.to_dict()
        forbidden_values = {"MTR-04821", "CUST-99231", "residential"}
        for value in signature_dict.values():
            assert value not in forbidden_values
        assert "location" not in signature_dict
        assert "raw_series" not in signature_dict

    def test_kind_is_signature(self):
        sig = abstract_to_signature(RAW_ANOMALY)
        assert sig.kind == "signature"

    def test_granularity_is_within_threshold(self):
        sig = abstract_to_signature(RAW_ANOMALY)
        assert sig.granularity <= GRANULARITY_THRESHOLD

    def test_works_from_precomputed_shape_features_without_raw_series(self):
        sig = abstract_to_signature(PRECOMPUTED_ANOMALY)
        assert sig.kind == "signature"
        assert sig.granularity <= GRANULARITY_THRESHOLD
        assert sig.recovery_shape == "step"  # recovers in 1 day, duration was 6

    def test_missing_site_id_raises(self):
        bad = dict(RAW_ANOMALY)
        del bad["site_id"]
        with pytest.raises(AbstractionError):
            abstract_to_signature(bad)

    def test_missing_shape_data_raises(self):
        bad = {"site_id": "site_z"}
        with pytest.raises(AbstractionError):
            abstract_to_signature(bad)

    def test_short_raw_series_raises(self):
        bad = {"site_id": "site_z", "raw_series": [1, 2, 3]}
        with pytest.raises(AbstractionError):
            abstract_to_signature(bad)

    def test_derived_features_detect_a_real_drop(self):
        # Baseline ~100, trough ~30 -> magnitude should land in the top bucket.
        sig = abstract_to_signature(RAW_ANOMALY)
        assert sig.load_drop_magnitude_bucket >= 3

    def test_timing_bucket_boundaries(self):
        pre = abstract_to_signature({**PRECOMPUTED_ANOMALY, "billing_cycle_day": 5})
        mid = abstract_to_signature({**PRECOMPUTED_ANOMALY, "billing_cycle_day": 15})
        post = abstract_to_signature({**PRECOMPUTED_ANOMALY, "billing_cycle_day": 28})
        assert pre.timing_bucket == "pre-cycle"
        assert mid.timing_bucket == "mid-cycle"
        assert post.timing_bucket == "post-cycle"


class TestAbstractToSignatureLeaky:
    @pytest.mark.parametrize(
        "leak_field,flag_name",
        [
            ("meter_id", "has_meter_id"),
            ("consumer_id", "has_consumer_id"),
            ("raw_series", "has_raw_series"),
            ("household_type", "has_household_field"),
            ("location", "has_location"),
        ],
    )
    def test_each_leak_field_sets_its_flag(self, leak_field, flag_name):
        sig = abstract_to_signature_leaky(RAW_ANOMALY, leak_field)
        assert getattr(sig, flag_name) is True
        assert sig.to_payload_attrs()[flag_name] is True

    def test_leaky_signature_exceeds_granularity_threshold(self):
        # Every raw-leak field carries a heavy fixed penalty specifically so
        # it cannot slip under the threshold even for an otherwise coarse signature.
        sig = abstract_to_signature_leaky(RAW_ANOMALY, "meter_id")
        assert sig.granularity > GRANULARITY_THRESHOLD

    def test_unrecognised_leak_field_raises(self):
        with pytest.raises(AbstractionError):
            abstract_to_signature_leaky(RAW_ANOMALY, "not_a_real_field")

    def test_leak_field_absent_from_anomaly_raises(self):
        anomaly = dict(RAW_ANOMALY)
        del anomaly["meter_id"]
        with pytest.raises(AbstractionError):
            abstract_to_signature_leaky(anomaly, "meter_id")


class TestToRawPayload:
    def test_flags_all_identifying_fields_present(self):
        raw = to_raw_payload(RAW_ANOMALY)
        assert raw.kind == "raw_record"
        assert raw.has_meter_id is True
        assert raw.has_consumer_id is True
        assert raw.has_raw_series is True
        assert raw.has_household_field is True
        assert raw.has_location is True

    def test_granularity_is_far_over_threshold(self):
        raw = to_raw_payload(RAW_ANOMALY)
        assert raw.granularity > GRANULARITY_THRESHOLD


class TestComputeGranularity:
    def test_empty_fields_score_zero(self):
        assert compute_granularity({}) == 0

    def test_unrelated_keys_are_free(self):
        # Bookkeeping fields like signature_id/generated_at cost nothing —
        # only descriptive/raw fields count toward the budget.
        assert compute_granularity({"signature_id": "sig-1", "generated_at": "now"}) == 0
