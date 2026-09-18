"""
Unit tests for the real-data feature engineering (detection/real_features.py).

No CSV needed -- all fabricated arrays, fast, always run.
"""

from __future__ import annotations

import numpy as np

from detection.real_features import (
    REAL_ML_FEATURE_NAMES,
    clears_real_drift,
    declutter_zeros,
    real_ml_feature_vector,
    real_shape_descriptor,
)


def _flat_series(value: float = 100.0, length: int = 1034) -> np.ndarray:
    rng = np.random.default_rng(0)
    return value + rng.normal(0, value * 0.02, size=length)


def _series_with_sustained_drop(baseline: float = 100.0, length: int = 1034, drop_frac: float = 0.6, duration: int = 200) -> np.ndarray:
    s = _flat_series(baseline, length)
    start = length - duration - 50
    s[start : start + duration] = baseline * (1 - drop_frac)
    return s


class TestDeclutterZeros:
    def test_isolated_single_zero_is_filled(self):
        series = np.array([10.0, 10.0, 0.0, 10.0, 10.0])
        out = declutter_zeros(series, max_isolated_run=2)
        assert out[2] != 0.0  # filled in, not left as a glitch

    def test_isolated_short_run_is_filled(self):
        series = np.array([10.0, 10.0, 0.0, 0.0, 10.0, 10.0])
        out = declutter_zeros(series, max_isolated_run=2)
        assert out[2] != 0.0 and out[3] != 0.0

    def test_sustained_zero_run_is_preserved(self):
        series = np.array([10.0] * 5 + [0.0] * 10 + [10.0] * 5)
        out = declutter_zeros(series, max_isolated_run=2)
        assert np.all(out[5:15] == 0.0)

    def test_preexisting_nan_is_filled_too(self):
        series = np.array([10.0, np.nan, 10.0, 10.0])
        out = declutter_zeros(series)
        assert not np.isnan(out).any()

    def test_all_nan_returns_zeros_not_nan(self):
        series = np.array([np.nan, np.nan, np.nan])
        out = declutter_zeros(series)
        assert not np.isnan(out).any()


class TestRealShapeDescriptor:
    def test_flat_series_has_low_magnitude(self):
        shape = real_shape_descriptor(_flat_series())
        assert shape["magnitude"] < 0.15

    def test_sustained_drop_has_high_magnitude_and_duration(self):
        shape = real_shape_descriptor(_series_with_sustained_drop())
        assert shape["magnitude"] >= 0.45
        assert shape["duration"] >= 90

    def test_recovery_shape_is_none_for_a_flat_series(self):
        shape = real_shape_descriptor(_flat_series())
        assert shape["recovery_shape"] == "none"

    def test_recovery_shape_is_none_when_drop_persists_to_the_end(self):
        series = _flat_series()
        series[-200:] = series[0] * 0.2  # sustained drop that never recovers
        shape = real_shape_descriptor(series)
        assert shape["recovery_shape"] == "none"

    def test_bucket_fields_are_present_and_in_range(self):
        shape = real_shape_descriptor(_series_with_sustained_drop())
        assert 0 <= shape["magnitude_bucket"] <= 4
        assert 0 <= shape["duration_bucket"] <= 4
        assert 0 <= shape["volatility_bucket"] <= 3


class TestClearsRealDrift:
    def test_sustained_drop_clears_drift(self):
        shape = real_shape_descriptor(_series_with_sustained_drop())
        assert clears_real_drift(shape) is True

    def test_flat_series_does_not_clear_drift(self):
        shape = real_shape_descriptor(_flat_series())
        assert clears_real_drift(shape) is False

    def test_big_but_brief_drop_does_not_clear_drift(self):
        series = _flat_series()
        series[500:510] = series[0] * 0.1  # big magnitude, only 10 days
        shape = real_shape_descriptor(series)
        assert clears_real_drift(shape) is False

    def test_long_but_shallow_drop_does_not_clear_drift(self):
        series = _flat_series()
        series[200:800] = series[0] * 0.85  # long duration, only a 15% dip
        shape = real_shape_descriptor(series)
        assert clears_real_drift(shape) is False


class TestRealMlFeatureVector:
    def test_returns_correct_length(self):
        vec = real_ml_feature_vector(_flat_series())
        assert vec.shape == (len(REAL_ML_FEATURE_NAMES),)

    def test_no_nan_or_inf_even_with_missing_data(self):
        series = _flat_series()
        series[::20] = np.nan
        vec = real_ml_feature_vector(series)
        assert np.isfinite(vec).all()

    def test_zero_fraction_reflects_raw_zero_rate(self):
        series = _flat_series()
        series[:100] = 0.0
        vec = real_ml_feature_vector(series)
        zero_fraction_idx = REAL_ML_FEATURE_NAMES.index("zero_fraction")
        assert vec[zero_fraction_idx] > 0.05
