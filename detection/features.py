"""
Feature engineering for the per-site anomaly detector.

Reuses `policy.signature.derive_shape_features` for the four canonical
shape descriptors (load_drop_magnitude, drop_duration_days,
recovery_time_days, volatility) instead of recomputing them independently.
That's deliberate: whatever the isolation forest is trained to notice and
whatever Person 2's abstraction layer buckets into a signature need to
describe the same shape, or a detected anomaly and its own signature would
disagree with each other. One function, two callers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import numpy as np

from detection.dataset import Consumer
from policy.signature import derive_shape_features

# Feature order matters: this is the exact column order fed to IsolationForest.
ML_FEATURE_NAMES = (
    "mean",
    "std",
    "min_max_ratio",
    "weekday_weekend_ratio",
    "load_drop_magnitude",
    "drop_duration_days",
    "recovery_time_days",
    "volatility",
)


def fill_missing(series: np.ndarray) -> np.ndarray:
    """Forward-fill then back-fill NaNs -- real smart-meter feeds drop readings.

    Falls back to the series' own mean if every value is missing (shouldn't
    happen at the missing-data rate dataset.py uses, but keeps this
    function total rather than raising on a pathological input).
    """
    series = series.astype(float).copy()
    if np.all(np.isnan(series)):
        return np.zeros_like(series)

    # Forward fill.
    last_valid = None
    for i in range(len(series)):
        if np.isnan(series[i]):
            if last_valid is not None:
                series[i] = last_valid
        else:
            last_valid = series[i]

    # Back fill anything still missing at the start.
    next_valid = None
    for i in range(len(series) - 1, -1, -1):
        if np.isnan(series[i]):
            if next_valid is not None:
                series[i] = next_valid
        else:
            next_valid = series[i]

    return series


def extract_shape_features(series: np.ndarray) -> dict[str, float]:
    """The four canonical shape features, computed via Person 2's own logic."""
    clean = fill_missing(series)
    return derive_shape_features({"raw_series": clean.tolist()})


def extract_ml_features(series: np.ndarray) -> dict[str, float]:
    """The full feature vector handed to the isolation forest.

    Combines simple summary statistics (mean/std/min-max ratio/weekday vs.
    weekend ratio) with the same four shape features `abstract_to_signature`
    will later bucket -- an isolation forest with no shape information at
    all can only separate consumers by consumption level, which is a much
    weaker signal for theft than "did this load shape change."
    """
    clean = fill_missing(series)
    mean = float(np.mean(clean))
    std = float(np.std(clean))
    min_val = float(np.min(clean))
    max_val = float(np.max(clean))
    min_max_ratio = 0.0 if max_val <= 0 else min_val / max_val

    weekday_mask = np.array([(i % 7) < 5 for i in range(len(clean))])
    weekday_mean = float(np.mean(clean[weekday_mask])) if weekday_mask.any() else mean
    weekend_mean = float(np.mean(clean[~weekday_mask])) if (~weekday_mask).any() else mean
    weekday_weekend_ratio = 1.0 if weekend_mean <= 0 else weekday_mean / weekend_mean

    shape = extract_shape_features(clean)

    return {
        "mean": mean,
        "std": std,
        "min_max_ratio": min_max_ratio,
        "weekday_weekend_ratio": weekday_weekend_ratio,
        **shape,
    }


def feature_vector(features: dict[str, float]) -> np.ndarray:
    """Order a feature dict into the fixed column order IsolationForest expects."""
    return np.array([features[name] for name in ML_FEATURE_NAMES], dtype=float)


def to_anomaly_record(consumer: Consumer, features: dict[str, float], anomaly_score: float) -> dict[str, Any]:
    """Build the exact dict shape `policy.signature.abstract_to_signature` expects.

    See policy/README.md's "Interface contract with Person 1" -- this is
    that contract, implemented.
    """
    return {
        "site_id": consumer.site_id,
        "meter_id": consumer.meter_id,
        "consumer_id": consumer.consumer_id,
        "household_type": consumer.household_type,
        "location": {"lat": consumer.lat, "lon": consumer.lon},
        "billing_cycle_day": consumer.billing_cycle_day,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "anomaly_score": anomaly_score,
        "load_drop_magnitude": features["load_drop_magnitude"],
        "drop_duration_days": features["drop_duration_days"],
        "recovery_time_days": features["recovery_time_days"],
        "volatility": features["volatility"],
    }


@dataclass(frozen=True)
class ConsumerFeatures:
    """A consumer's ML feature vector, cached alongside its identity."""

    consumer: Consumer
    features: dict[str, float]
    vector: np.ndarray


def extract_all(consumers: list[Consumer]) -> list[ConsumerFeatures]:
    out = []
    for c in consumers:
        feats = extract_ml_features(c.series)
        out.append(ConsumerFeatures(consumer=c, features=feats, vector=feature_vector(feats)))
    return out
