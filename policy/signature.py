"""
Abstraction layer: anomaly -> signature vector.

This is the boundary between "whatever Person 1's detector produced" and
"the coarse, policy-checkable object Person 2's Cedar gate is allowed to see".
Nothing downstream of `abstract_to_signature` ever touches a meter ID, a
consumer ID, a raw time series, a household field, or a location again.

Input contract (what Person 1's detector should hand us)
---------------------------------------------------------
A raw anomaly dict, produced per flagged reading, shaped like::

    {
        "site_id": "site_c_low_data",
        "meter_id": "MTR-04821",              # identifying
        "consumer_id": "CUST-99231",           # identifying
        "household_type": "residential",       # identifying
        "location": {"lat": 12.9, "lon": 77.6},# identifying
        "raw_series": [123.4, 118.0, ...],     # raw, optional if shape
                                                # features are precomputed
        "billing_cycle_day": 15,               # 1-31, day of billing cycle
        "detected_at": "2026-09-18T03:00:00Z", # ISO timestamp
        "anomaly_score": 0.91,                 # 0..1, detector confidence
        # optional precomputed shape features, used if raw_series is absent:
        "load_drop_magnitude": 0.63,           # fraction drop from baseline
        "drop_duration_days": 4,
        "recovery_time_days": 12,
        "volatility": 0.22,
    }

Only `site_id` is required beyond enough information to derive the shape
features (either `raw_series`, or the four precomputed fields above).

Output contract (what the Cedar gate and shared store see)
------------------------------------------------------------
A signature dict: bucketed/categorical shape descriptors, a `granularity`
score, five `has_*` boolean flags (always False for a *correctly* built
signature), and enough bookkeeping (`signature_id`, `site_of_origin`,
`generated_at`) to log and route it. See `PAYLOAD_ATTR_KEYS` for exactly
which keys the Cedar policy gate reads.
"""

from __future__ import annotations

import statistics
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# Must match the literal `10` in policy/policies/sharing.cedar — kept in sync
# by tests/test_policy_gate.py::test_threshold_matches_code.
GRANULARITY_THRESHOLD = 10

# Bucket edges: value <= edge[i] -> bucket i, else keep climbing.
_MAGNITUDE_EDGES = (0.10, 0.25, 0.45, 0.70)  # -> 5 buckets, 0..4
_DURATION_EDGES = (2, 5, 10)  # days -> 4 buckets, 0..3
_VOLATILITY_EDGES = (0.10, 0.20, 0.35)  # -> 4 buckets, 0..3
_SCORE_EDGES = (0.50, 0.70, 0.85, 0.95)  # -> 5 buckets, 0..4

_RECOVERY_SHAPES = ("none", "gradual", "step")
_TIMING_BUCKETS = ("pre-cycle", "mid-cycle", "post-cycle")

# Every bucketed/categorical descriptor costs a flat 1 point of granularity.
_BUCKET_FIELD_WEIGHT = 1
_BUCKETED_FIELDS = (
    "load_drop_magnitude_bucket",
    "drop_duration_bucket",
    "timing_bucket",
    "recovery_shape",
    "volatility_bucket",
    "anomaly_score_bucket",
)

# Any of these keys surviving into a signature means something raw or
# high-precision leaked through the abstraction, whether or not it happens
# to be a named identifier. Each one blows well past the threshold on its
# own, by design.
_RAW_LEAK_PENALTY = 25
_RAW_LEAK_KEYS = (
    "meter_id",
    "consumer_id",
    "household_type",
    "location",
    "raw_series",
    "billing_cycle_day",
    "anomaly_score",  # unbucketed float, too precise to pool
    "load_drop_magnitude",  # unbucketed float
    "recovery_time_days",  # unbucketed int
    "volatility",  # unbucketed float
)

# The subset of a signature's keys that the Cedar Payload entity actually
# carries. Everything else in the signature is for logging/debugging only —
# Cedar never sees the shape descriptors, only whether the payload is clean
# and how granular it is.
PAYLOAD_ATTR_KEYS = (
    "kind",
    "has_meter_id",
    "has_consumer_id",
    "has_raw_series",
    "has_household_field",
    "has_location",
    "granularity",
)


class AbstractionError(ValueError):
    """Raised when a raw anomaly doesn't carry enough information to abstract."""


def _bucketize(value: float, edges: tuple[float, ...]) -> int:
    for i, edge in enumerate(edges):
        if value <= edge:
            return i
    return len(edges)


def derive_shape_features(anomaly: dict[str, Any]) -> dict[str, float]:
    """Compute (or pass through) the four raw shape features from an anomaly.

    Prefers precomputed fields if present; otherwise derives them from
    `raw_series` using a simple baseline = mean of the first third of the
    series (the "normal" period before the anomaly develops).
    """
    precomputed = {
        "load_drop_magnitude",
        "drop_duration_days",
        "recovery_time_days",
        "volatility",
    } & anomaly.keys()
    if precomputed == {
        "load_drop_magnitude",
        "drop_duration_days",
        "recovery_time_days",
        "volatility",
    }:
        return {
            "load_drop_magnitude": float(anomaly["load_drop_magnitude"]),
            "drop_duration_days": float(anomaly["drop_duration_days"]),
            "recovery_time_days": float(anomaly["recovery_time_days"]),
            "volatility": float(anomaly["volatility"]),
        }

    series = anomaly.get("raw_series")
    if not series or len(series) < 6:
        raise AbstractionError(
            "anomaly needs either all four precomputed shape features "
            "(load_drop_magnitude, drop_duration_days, recovery_time_days, "
            "volatility) or a raw_series with at least 6 points"
        )

    baseline_window = series[: max(2, len(series) // 3)]
    baseline = statistics.fmean(baseline_window)
    trough = min(series)
    magnitude = 0.0 if baseline <= 0 else max(0.0, (baseline - trough) / baseline)

    drop_threshold = baseline * 0.7
    below = [v < drop_threshold for v in series]
    duration = float(sum(1 for v in below if v))

    recovery_days = float(len(series))
    for i in range(len(series) - 1, -1, -1):
        if series[i] < drop_threshold:
            recovery_days = float(len(series) - 1 - i)
            break

    mean = statistics.fmean(series)
    volatility = 0.0 if mean <= 0 else statistics.pstdev(series) / mean

    return {
        "load_drop_magnitude": magnitude,
        "drop_duration_days": duration,
        "recovery_time_days": recovery_days,
        "volatility": volatility,
    }


def _timing_bucket(anomaly: dict[str, Any]) -> str:
    day = anomaly.get("billing_cycle_day")
    if day is None:
        return "mid-cycle"
    day = int(day)
    if day <= 10:
        return "pre-cycle"
    if day <= 21:
        return "mid-cycle"
    return "post-cycle"


def _recovery_shape(recovery_time_days: float, drop_duration_days: float) -> str:
    if recovery_time_days <= 0:
        return "none"
    if drop_duration_days > 0 and recovery_time_days <= drop_duration_days:
        return "step"
    return "gradual"


def compute_granularity(fields: dict[str, Any]) -> int:
    """Sum the granularity cost of every field present in a payload dict.

    Bucketed/categorical descriptors cost a flat point each. Any field whose
    presence indicates raw or unbucketed data costs a heavy flat penalty,
    regardless of its value — leaking a float is exactly as bad as leaking
    an ID as far as the granularity budget is concerned.
    """
    score = 0
    for key in fields:
        if key in _BUCKETED_FIELDS:
            score += _BUCKET_FIELD_WEIGHT
        elif key in _RAW_LEAK_KEYS:
            score += _RAW_LEAK_PENALTY
    return score


def _has_flags(fields: dict[str, Any]) -> dict[str, bool]:
    return {
        "has_meter_id": "meter_id" in fields and fields["meter_id"] not in (None, ""),
        "has_consumer_id": "consumer_id" in fields and fields["consumer_id"] not in (None, ""),
        "has_raw_series": "raw_series" in fields and bool(fields["raw_series"]),
        "has_household_field": "household_type" in fields and fields["household_type"] not in (None, ""),
        "has_location": "location" in fields and fields["location"] not in (None, {}),
    }


@dataclass
class Signature:
    """A signature ready to be offered to the shared pattern store.

    `to_payload_attrs()` is the only part of this Cedar ever evaluates.
    Everything else here is for logging, debugging, and Person 3's
    orchestration loop.
    """

    signature_id: str
    site_of_origin: str
    kind: str
    generated_at: str
    load_drop_magnitude_bucket: int
    drop_duration_bucket: int
    timing_bucket: str
    recovery_shape: str
    volatility_bucket: int
    anomaly_score_bucket: int
    granularity: int
    has_meter_id: bool
    has_consumer_id: bool
    has_raw_series: bool
    has_household_field: bool
    has_location: bool
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "signature_id": self.signature_id,
            "site_of_origin": self.site_of_origin,
            "kind": self.kind,
            "generated_at": self.generated_at,
            "load_drop_magnitude_bucket": self.load_drop_magnitude_bucket,
            "drop_duration_bucket": self.drop_duration_bucket,
            "timing_bucket": self.timing_bucket,
            "recovery_shape": self.recovery_shape,
            "volatility_bucket": self.volatility_bucket,
            "anomaly_score_bucket": self.anomaly_score_bucket,
            "granularity": self.granularity,
            "has_meter_id": self.has_meter_id,
            "has_consumer_id": self.has_consumer_id,
            "has_raw_series": self.has_raw_series,
            "has_household_field": self.has_household_field,
            "has_location": self.has_location,
        }
        d.update(self.extra)
        return d

    def to_payload_attrs(self) -> dict[str, Any]:
        """The subset of fields the Cedar Payload entity is built from."""
        d = self.to_dict()
        return {k: d[k] for k in PAYLOAD_ATTR_KEYS}

    def shape_key(self) -> tuple[int, int, str, str, int]:
        """The bucketed "what does this theft pattern look like" fingerprint.

        Two signatures with the same shape_key describe the same abstract
        theft shape, independent of which site or which consumer produced
        them — this is the join key Person 1's pooled re-check and Person
        3's shared-store lookups use to compare a new anomaly against what
        peers have already shared, without ever touching a raw value.
        """
        return (
            self.load_drop_magnitude_bucket,
            self.drop_duration_bucket,
            self.timing_bucket,
            self.recovery_shape,
            self.volatility_bucket,
        )


SHAPE_KEY_FIELDS = (
    "load_drop_magnitude_bucket",
    "drop_duration_bucket",
    "timing_bucket",
    "recovery_shape",
    "volatility_bucket",
)


def shape_key_from_dict(signature_dict: dict[str, Any]) -> tuple[int, int, str, str, int]:
    """Same fingerprint as `Signature.shape_key()`, for a plain dict.

    Use this on records read back from the shared store (e.g. Person 3's
    OpenSearch query results), which come back as dicts, not `Signature`
    objects.
    """
    return tuple(signature_dict[k] for k in SHAPE_KEY_FIELDS)  # type: ignore[return-value]


def abstract_to_signature(anomaly: dict[str, Any]) -> Signature:
    """Correctly abstract a raw anomaly into a shareable signature.

    Strips every identifying field, buckets every continuous shape feature,
    and computes the resulting granularity. This is the "sanitised version"
    in the block-then-pass demo — it is expected to pass the Cedar gate.
    """
    if "site_id" not in anomaly:
        raise AbstractionError("anomaly is missing required field 'site_id'")

    shape = derive_shape_features(anomaly)
    timing = _timing_bucket(anomaly)
    recovery_shape = _recovery_shape(shape["recovery_time_days"], shape["drop_duration_days"])

    signature_fields = {
        "load_drop_magnitude_bucket": _bucketize(shape["load_drop_magnitude"], _MAGNITUDE_EDGES),
        "drop_duration_bucket": _bucketize(shape["drop_duration_days"], _DURATION_EDGES),
        "timing_bucket": timing,
        "recovery_shape": recovery_shape,
        "volatility_bucket": _bucketize(shape["volatility"], _VOLATILITY_EDGES),
        "anomaly_score_bucket": _bucketize(float(anomaly.get("anomaly_score", 0.0)), _SCORE_EDGES),
    }

    return Signature(
        signature_id=f"sig-{uuid.uuid4().hex[:12]}",
        site_of_origin=anomaly["site_id"],
        kind="signature",
        generated_at=datetime.now(timezone.utc).isoformat(),
        load_drop_magnitude_bucket=signature_fields["load_drop_magnitude_bucket"],
        drop_duration_bucket=signature_fields["drop_duration_bucket"],
        timing_bucket=timing,
        recovery_shape=recovery_shape,
        volatility_bucket=signature_fields["volatility_bucket"],
        anomaly_score_bucket=signature_fields["anomaly_score_bucket"],
        granularity=compute_granularity(signature_fields),
        has_meter_id=False,
        has_consumer_id=False,
        has_raw_series=False,
        has_household_field=False,
        has_location=False,
    )


def abstract_to_signature_leaky(anomaly: dict[str, Any], leak_field: str) -> Signature:
    """Simulate a careless/buggy abstraction that forgot to strip one field.

    Runs the real abstraction, then re-attaches a single raw field from the
    original anomaly, exactly as a site with a bug in its abstraction layer
    might. `leak_field` must be one of `_RAW_LEAK_KEYS` and present in
    `anomaly`. This is the "signature that leaks an ID" half of the
    block-then-pass demo — it is expected to be denied.
    """
    if leak_field not in _RAW_LEAK_KEYS:
        raise AbstractionError(f"{leak_field!r} is not a recognised raw/identifying field")
    if leak_field not in anomaly:
        raise AbstractionError(f"anomaly does not contain {leak_field!r} to leak")

    clean = abstract_to_signature(anomaly)
    leaked_value = anomaly[leak_field]

    extra = dict(clean.extra)
    extra[leak_field] = leaked_value
    flags = _has_flags({leak_field: leaked_value})
    granularity = compute_granularity({leak_field: leaked_value, **{
        k: v for k, v in clean.to_dict().items() if k in _BUCKETED_FIELDS
    }})

    return Signature(
        signature_id=clean.signature_id,
        site_of_origin=clean.site_of_origin,
        kind=clean.kind,
        generated_at=clean.generated_at,
        load_drop_magnitude_bucket=clean.load_drop_magnitude_bucket,
        drop_duration_bucket=clean.drop_duration_bucket,
        timing_bucket=clean.timing_bucket,
        recovery_shape=clean.recovery_shape,
        volatility_bucket=clean.volatility_bucket,
        anomaly_score_bucket=clean.anomaly_score_bucket,
        granularity=granularity,
        has_meter_id=flags["has_meter_id"] or clean.has_meter_id,
        has_consumer_id=flags["has_consumer_id"] or clean.has_consumer_id,
        has_raw_series=flags["has_raw_series"] or clean.has_raw_series,
        has_household_field=flags["has_household_field"] or clean.has_household_field,
        has_location=flags["has_location"] or clean.has_location,
        extra=extra,
    )


def to_raw_payload(anomaly: dict[str, Any]) -> Signature:
    """Wrap an untouched anomaly as a `kind="raw_record"` payload.

    Used to demonstrate that raw detector output is rejected outright —
    never even a candidate for the permit rule, let alone the granularity
    check. Real sites never call this on the sharing path; it exists so the
    demo and tests can prove the boundary catches the worst case too.
    """
    if "site_id" not in anomaly:
        raise AbstractionError("anomaly is missing required field 'site_id'")

    flags = _has_flags(anomaly)
    granularity = compute_granularity(anomaly)

    return Signature(
        signature_id=f"raw-{uuid.uuid4().hex[:12]}",
        site_of_origin=anomaly["site_id"],
        kind="raw_record",
        generated_at=datetime.now(timezone.utc).isoformat(),
        load_drop_magnitude_bucket=-1,
        drop_duration_bucket=-1,
        timing_bucket="n/a",
        recovery_shape="n/a",
        volatility_bucket=-1,
        anomaly_score_bucket=-1,
        granularity=granularity,
        **flags,
        extra={k: v for k, v in anomaly.items() if k != "site_id"},
    )
