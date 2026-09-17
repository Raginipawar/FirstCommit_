"""Unit tests for feature extraction (detection/features.py)."""

from __future__ import annotations

import numpy as np

from detection.dataset import generate_site, SITE_CONFIGS
from detection.features import (
    ML_FEATURE_NAMES,
    extract_all,
    extract_ml_features,
    extract_shape_features,
    feature_vector,
    fill_missing,
    to_anomaly_record,
)


def test_fill_missing_forward_and_back_fills():
    series = np.array([1.0, np.nan, 3.0, np.nan, np.nan, 6.0])
    filled = fill_missing(series)
    assert not np.isnan(filled).any()
    assert filled[1] == 1.0  # forward-filled
    assert filled[3] == 3.0 and filled[4] == 3.0  # forward-filled from index 2


def test_fill_missing_back_fills_a_leading_gap():
    series = np.array([np.nan, np.nan, 5.0, 6.0])
    filled = fill_missing(series)
    assert filled[0] == 5.0 and filled[1] == 5.0


def test_fill_missing_all_nan_returns_zeros_not_nan():
    series = np.array([np.nan, np.nan, np.nan])
    filled = fill_missing(series)
    assert not np.isnan(filled).any()
    assert np.all(filled == 0.0)


def test_extract_shape_features_matches_policy_signature_keys():
    consumers = generate_site(SITE_CONFIGS[0])
    shape = extract_shape_features(consumers[0].series)
    assert set(shape.keys()) == {
        "load_drop_magnitude",
        "drop_duration_days",
        "recovery_time_days",
        "volatility",
    }


def test_extract_ml_features_has_all_expected_columns():
    consumers = generate_site(SITE_CONFIGS[0])
    features = extract_ml_features(consumers[0].series)
    assert set(ML_FEATURE_NAMES) <= set(features.keys())


def test_theft_consumers_have_higher_magnitude_than_honest_on_average():
    consumers = generate_site(SITE_CONFIGS[0])
    theft_magnitudes = [extract_ml_features(c.series)["load_drop_magnitude"] for c in consumers if c.is_theft]
    honest_magnitudes = [extract_ml_features(c.series)["load_drop_magnitude"] for c in consumers if not c.is_theft]
    assert np.mean(theft_magnitudes) > np.mean(honest_magnitudes)


def test_feature_vector_preserves_declared_order():
    features = {name: float(i) for i, name in enumerate(ML_FEATURE_NAMES)}
    vec = feature_vector(features)
    assert list(vec) == [float(i) for i in range(len(ML_FEATURE_NAMES))]


def test_extract_all_pairs_each_consumer_with_its_own_vector():
    consumers = generate_site(SITE_CONFIGS[0])[:5]
    results = extract_all(consumers)
    assert len(results) == 5
    for cf, consumer in zip(results, consumers):
        assert cf.consumer is consumer
        assert cf.vector.shape == (len(ML_FEATURE_NAMES),)


def test_to_anomaly_record_matches_policy_signature_input_contract():
    consumers = generate_site(SITE_CONFIGS[0])
    consumer = consumers[0]
    features = extract_ml_features(consumer.series)
    record = to_anomaly_record(consumer, features, anomaly_score=0.8)

    assert record["site_id"] == consumer.site_id
    assert record["meter_id"] == consumer.meter_id
    assert record["consumer_id"] == consumer.consumer_id
    assert record["location"] == {"lat": consumer.lat, "lon": consumer.lon}
    assert 0.0 <= record["anomaly_score"] <= 1.0
    for key in ("load_drop_magnitude", "drop_duration_days", "recovery_time_days", "volatility"):
        assert key in record


def test_to_anomaly_record_is_actually_abstractable():
    """The whole point of the interface contract: Person 2's function must
    accept Person 1's output without modification."""
    from policy.signature import abstract_to_signature

    consumers = generate_site(SITE_CONFIGS[0])
    consumer = consumers[0]
    features = extract_ml_features(consumer.series)
    record = to_anomaly_record(consumer, features, anomaly_score=0.8)

    signature = abstract_to_signature(record)
    assert signature.kind == "signature"
    assert signature.has_meter_id is False
