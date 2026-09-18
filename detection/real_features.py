"""
Feature engineering for the REAL SGCC dataset — a separate, parallel path
from features.py (the synthetic-data path), because the real dataset needs
different handling at two points, discovered empirically (see
detection/README.md, "Why the real-data path is separate"):

1. **Spurious zero readings.** ~13% of all real readings are recorded as
   exactly 0.0, and honest customers have a *higher* raw zero-rate (13.7%)
   than theft customers (8.3%) — these are meter/recording glitches, not
   signal. A naive "trough = minimum reading" (what the synthetic path
   uses, safely, since synthetic data has no such glitches) gets swamped by
   them. `declutter_zeros()` treats short zero-runs as missing data;
   longer runs are left alone, since a sustained real zero (a bypassed or
   disconnected meter) is exactly the kind of pattern worth keeping.

2. **Timescale.** The real series is ~1,034 days; the synthetic one is
   120. Reusing policy/signature.py's day-count bucket edges (tuned for a
   120-day series) against a 1,034-day series would make nearly everything
   fall in the top bucket. `REAL_DURATION_EDGES` below are re-tuned for
   this series length; everything else about the bucketing approach is the
   same idea as policy/signature.py.

Despite the separate bucket edges, the OUTPUT is still a
`policy.signature.Signature` — the same dataclass, the same
`to_payload_attrs()`, the same Cedar gate. Cedar's rules only ever check
`kind`, the five `has_*` flags, and `granularity` (a field-name-counting
function, not a value-scale-dependent one) — none of that cares what
timescale produced the bucket values. See real_pipeline.py for exactly
how a `Signature` gets constructed from these features.
"""

from __future__ import annotations

import numpy as np

# Re-tuned for a ~1,034-day series (vs. policy/signature.py's 120-day edges).
REAL_MAGNITUDE_EDGES = (0.10, 0.25, 0.45, 0.70)  # fraction is scale-free, same edges as synthetic
REAL_DURATION_EDGES = (30, 90, 200, 400)  # days below threshold, out of ~1,034
REAL_VOLATILITY_EDGES = (0.10, 0.20, 0.35)

# Only a real, sharp, *sustained* drop is worth sharing -- see
# detection/README.md, "Why the drift filter exists," for the synthetic
# version of this same lesson. Re-tuned here because "3 days" out of 120
# and "3 days" out of 1,034 are not the same signal.
REAL_DRIFT_MAGNITUDE_THRESHOLD = 0.45
REAL_DRIFT_DURATION_THRESHOLD = 90.0

# ML_FEATURE_NAMES order matters -- this is the fixed column order fed to
# the RandomForestClassifier in real_detector.py.
REAL_ML_FEATURE_NAMES = (
    "mean", "std", "min", "max", "p5", "p95",
    "zero_fraction", "coefficient_of_variation",
    "recent_relative_usage", "early_relative_usage",
)


def declutter_zeros(series: np.ndarray, max_isolated_run: int = 2) -> np.ndarray:
    """Treat short runs of exact-zero readings as missing data; fill them
    (and any pre-existing NaNs) by forward/back-fill.

    A run of `max_isolated_run` or fewer consecutive zeros is almost always
    a recording glitch (see this module's docstring for the measured
    evidence); a longer run is left as real, since a sustained zero really
    could be a bypassed meter -- exactly the pattern worth detecting.

    Pure numpy, not pandas: this runs once per consumer, and with ~42,000
    real consumers a pandas groupby-per-call implementation measured at
    ~90s end to end for the full pipeline -- too slow for a judge to click
    through live. This vectorized version does the same run-length
    detection with numpy boundary arithmetic instead.
    """
    s = np.asarray(series, dtype=float)
    n = len(s)
    is_zero = s == 0
    if is_zero.any():
        padded = np.concatenate(([False], is_zero, [False]))
        edges = np.diff(padded.astype(np.int8))
        run_starts = np.flatnonzero(edges == 1)
        run_ends = np.flatnonzero(edges == -1)  # exclusive
        short = (run_ends - run_starts) <= max_isolated_run
        s = s.copy()
        for start, end in zip(run_starts[short], run_ends[short]):
            s[start:end] = np.nan
    return _forward_back_fill(s)


def _forward_back_fill(s: np.ndarray) -> np.ndarray:
    """Vectorized equivalent of pandas' `.ffill().bfill()` on a 1-D array."""
    n = len(s)
    valid = ~np.isnan(s)
    if not valid.any():
        return np.zeros(n)

    fwd_idx = np.where(valid, np.arange(n), 0)
    np.maximum.accumulate(fwd_idx, out=fwd_idx)
    filled = s[fwd_idx]

    if np.isnan(filled[0]):
        # Leading NaNs (before the first valid reading) survive forward-fill;
        # back-fill them from the next valid value.
        bwd_idx = np.where(valid, np.arange(n), n - 1)
        bwd_idx = np.minimum.accumulate(bwd_idx[::-1])[::-1]
        filled = np.where(np.isnan(filled), s[bwd_idx], filled)
    return filled


def _bucketize(value: float, edges: tuple[float, ...]) -> int:
    for i, edge in enumerate(edges):
        if value <= edge:
            return i
    return len(edges)


def real_shape_descriptor(raw_series: np.ndarray) -> dict:
    """The real-data equivalent of policy.signature.derive_shape_features,
    plus its own bucketing (re-tuned edges) and recovery_shape derivation.

    Returns both raw values (magnitude, duration) and bucketed/categorical
    fields, so callers can use raw values for drift-checking and bucketed
    fields for building a Signature.
    """
    s = declutter_zeros(raw_series)
    baseline = float(np.median(s))
    trough = float(np.percentile(s, 5))  # robust to a single remaining outlier, unlike min()
    magnitude = 0.0 if baseline <= 0 else max(0.0, (baseline - trough) / baseline)

    drop_threshold = baseline * 0.7
    below = s < drop_threshold
    duration = float(below.sum())

    recovery_days = 0.0
    for i in range(len(s) - 1, -1, -1):
        if s[i] < drop_threshold:
            recovery_days = float(len(s) - 1 - i)
            break
    else:
        recovery_days = 0.0  # never dropped at all

    if duration == 0:
        recovery_shape = "none"
    elif recovery_days <= 0:
        recovery_shape = "none"  # still below threshold at the very end of the series
    elif recovery_days <= duration:
        recovery_shape = "step"
    else:
        recovery_shape = "gradual"

    mean = float(np.mean(s))
    volatility = 0.0 if mean <= 0 else float(np.std(s) / mean)

    return {
        "magnitude": magnitude,
        "duration": duration,
        "volatility": volatility,
        "recovery_shape": recovery_shape,
        "magnitude_bucket": _bucketize(magnitude, REAL_MAGNITUDE_EDGES),
        "duration_bucket": _bucketize(duration, REAL_DURATION_EDGES),
        "volatility_bucket": _bucketize(volatility, REAL_VOLATILITY_EDGES),
    }


def clears_real_drift(shape: dict) -> bool:
    """The real-data drift trigger: only a big, sustained drop is a sharing
    candidate. See this module's docstring for why the thresholds differ
    from the synthetic path's."""
    return (
        shape["magnitude"] >= REAL_DRIFT_MAGNITUDE_THRESHOLD
        and shape["duration"] >= REAL_DRIFT_DURATION_THRESHOLD
    )


def real_ml_feature_vector(raw_series: np.ndarray) -> np.ndarray:
    """The 10-number feature vector fed to the supervised classifier.

    Deliberately richer than the 3-4 shape features alone -- an
    unsupervised isolation forest on just shape features scored barely
    above chance on this dataset during evaluation (see
    detection/README.md); a supervised classifier on this richer feature
    set is what actually gets a usable result (AUC ~0.76).
    """
    s_raw = np.asarray(raw_series, dtype=float)
    s = declutter_zeros(s_raw)
    median = np.median(s)
    median_safe = median if median != 0 else 1.0

    n = len(s)
    window = min(180, n // 2) or 1
    recent = s[-window:]
    early = s[:window]

    return np.array([
        np.mean(s), np.std(s), np.min(s), np.max(s),
        np.percentile(s, 5), np.percentile(s, 95),
        float(np.mean(s_raw == 0)),  # zero_fraction computed on the RAW series -- the glitch rate itself is a feature
        np.std(s) / median_safe,
        np.mean(recent) / median_safe,
        np.mean(early) / median_safe,
    ], dtype=float)
