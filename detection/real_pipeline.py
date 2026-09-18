"""
The real end-to-end pipeline: real SGCC data -> per-site supervised
classifier -> confident, drift-cleared detections -> Cedar-gated sharing
-> pooled re-check on the low-data site.

Mirrors orchestration/loop.py's structure (detect -> share -> re-check),
adapted for the supervised-classifier path. Deliberately reuses
`policy.signature.Signature`, `policy.signature.compute_granularity`, and
`policy.gate.PolicyGate` completely unmodified: Cedar's rules only ever
check `kind`, the five `has_*` flags, and `granularity` (a field-name-
counting function, not one that cares about a bucket's value or the
timescale that produced it) -- none of that depends on which detector or
which bucket edges built the Signature. The bucket *values* come from
real_features.py's real-data-scaled thresholds, not policy/signature.py's
synthetic-scaled ones; see real_features.py's docstring for why those
need to differ.

Only site_c_low_data's isolated-vs-pooled comparison is reported here
(matching what was validated during development) -- generalizing to every
site re-checking, the way orchestration/loop.py::run_swarm_cycle does for
the synthetic path, is a reasonable next step but adds real runtime cost
computing shape descriptors for every site's full test set; out of scope
for what this needed to prove.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from detection.baseline import DetectionMetrics, evaluate_detection
from detection.real_dataset import load_real_sgcc
from detection.real_detector import SupervisedFlag, SupervisedSiteDetector
from detection.real_features import clears_real_drift, real_shape_descriptor
from policy.gate import PolicyGate
from policy.signature import Signature, compute_granularity

SOURCE_SITES = ("site_a", "site_b")
LOW_DATA_SITE = "site_c_low_data"

ISOLATED_THRESHOLD = 0.5  # a test consumer's own site classifier calls it theft above this
SHARE_CONFIDENCE_THRESHOLD = 0.7  # only share a detection the classifier itself is quite sure about
RECHECK_BORDERLINE_THRESHOLD = 0.2  # only worth checking against the pool if the site's own model was even a little suspicious

_TIMING_BUCKET_PLACEHOLDER = "mid-cycle"  # the real dataset has no billing-cycle field; held constant for every real signature


def _signature_from_real_shape(site_id: str, shape: dict) -> Signature:
    """Build a Signature from a real-data shape descriptor.

    Only the fields Cedar's granularity check and the shape_key() matcher
    use are populated meaningfully; has_* flags are all False because
    nothing here ever touches CONS_NO, the raw series, or any other
    identifying field -- the shape descriptor is computed and discarded,
    never attached to the Signature itself.
    """
    granularity_fields = {
        "load_drop_magnitude_bucket": shape["magnitude_bucket"],
        "drop_duration_bucket": shape["duration_bucket"],
        "timing_bucket": _TIMING_BUCKET_PLACEHOLDER,
        "recovery_shape": shape["recovery_shape"],
        "volatility_bucket": shape["volatility_bucket"],
        "anomaly_score_bucket": 0,
    }
    return Signature(
        signature_id=f"sig-real-{uuid.uuid4().hex[:12]}",
        site_of_origin=site_id,
        kind="signature",
        generated_at=datetime.now(timezone.utc).isoformat(),
        load_drop_magnitude_bucket=shape["magnitude_bucket"],
        drop_duration_bucket=shape["duration_bucket"],
        timing_bucket=_TIMING_BUCKET_PLACEHOLDER,
        recovery_shape=shape["recovery_shape"],
        volatility_bucket=shape["volatility_bucket"],
        anomaly_score_bucket=0,
        granularity=compute_granularity(granularity_fields),
        has_meter_id=False,
        has_consumer_id=False,
        has_raw_series=False,
        has_household_field=False,
        has_location=False,
    )


@dataclass(frozen=True)
class RealPipelineResult:
    isolated_metrics: dict[str, DetectionMetrics]
    pooled_metrics_low_data: DetectionMetrics
    train_theft_counts: dict[str, int]
    pool_size: int
    shared_counts: dict[str, int]
    denied_counts: dict[str, int]


def _share_confident_detections(
    site_id: str,
    flags: list[SupervisedFlag],
    gate: PolicyGate,
) -> tuple[list[dict], int, int]:
    """Drift-filter and Cedar-gate a site's confident detections.

    Returns (permitted signature dicts, shared count, denied count).
    Nothing here is denied in practice (every signature built by
    `_signature_from_real_shape` is clean by construction), but the call
    still goes through the real gate rather than skipping it -- Cedar is
    the single enforcement point, on principle, even when the outcome is
    predictable.
    """
    confident = [f for f in flags if f.probability >= SHARE_CONFIDENCE_THRESHOLD]
    permitted: list[dict] = []
    denied = 0
    for f in confident:
        shape = real_shape_descriptor(f.consumer.raw_series)
        if not clears_real_drift(shape):
            continue
        signature = _signature_from_real_shape(site_id, shape)
        decision = gate.evaluate_share_request(site_id, signature)
        if decision.allowed:
            permitted.append(signature.to_dict())
        else:
            denied += 1
    return permitted, len(permitted), denied


def _pool_shape_keys(pool_signatures: list[dict]) -> set[tuple]:
    return {
        (
            s["load_drop_magnitude_bucket"],
            s["drop_duration_bucket"],
            s["timing_bucket"],
            s["recovery_shape"],
            s["volatility_bucket"],
        )
        for s in pool_signatures
    }


def run_real_pipeline(csv_path: str | Path, gate: PolicyGate) -> RealPipelineResult:
    """Run the full real-data cycle once. See this module's docstring for
    what "once" covers (every site's isolated baseline + sharing; only
    site_c_low_data's pooled re-check)."""
    sites = load_real_sgcc(csv_path)

    detectors: dict[str, SupervisedSiteDetector] = {}
    isolated_metrics: dict[str, DetectionMetrics] = {}
    train_theft_counts: dict[str, int] = {}
    flags_by_site: dict[str, list[SupervisedFlag]] = {}

    for site_id, consumers in sites.items():
        detector = SupervisedSiteDetector().fit(consumers)
        detectors[site_id] = detector
        train_theft_counts[site_id] = detector.n_train_theft

        flags = detector.score_test_set()
        flags_by_site[site_id] = flags
        flagged_ids = {f.consumer.consumer_id for f in flags if f.probability >= ISOLATED_THRESHOLD}
        isolated_metrics[site_id] = evaluate_detection(detector.test_consumers, flagged_ids)

    pool_signatures: list[dict] = []
    shared_counts: dict[str, int] = {}
    denied_counts: dict[str, int] = {}
    for site_id in SOURCE_SITES:
        permitted, shared, denied = _share_confident_detections(site_id, flags_by_site[site_id], gate)
        pool_signatures.extend(permitted)
        shared_counts[site_id] = shared
        denied_counts[site_id] = denied

    pool_keys = _pool_shape_keys(pool_signatures)

    low_data_flags = flags_by_site[LOW_DATA_SITE]
    isolated_ids = {f.consumer.consumer_id for f in low_data_flags if f.probability >= ISOLATED_THRESHOLD}
    pooled_ids = set(isolated_ids)
    for f in low_data_flags:
        if f.consumer.consumer_id in pooled_ids:
            continue
        if f.probability < RECHECK_BORDERLINE_THRESHOLD:
            continue  # not even borderline-suspicious to this site's own model -- don't bother checking the pool
        shape = real_shape_descriptor(f.consumer.raw_series)
        key = (
            shape["magnitude_bucket"],
            shape["duration_bucket"],
            _TIMING_BUCKET_PLACEHOLDER,
            shape["recovery_shape"],
            shape["volatility_bucket"],
        )
        if key in pool_keys:
            pooled_ids.add(f.consumer.consumer_id)

    pooled_metrics = evaluate_detection(detectors[LOW_DATA_SITE].test_consumers, pooled_ids)

    return RealPipelineResult(
        isolated_metrics=isolated_metrics,
        pooled_metrics_low_data=pooled_metrics,
        train_theft_counts=train_theft_counts,
        pool_size=len(pool_signatures),
        shared_counts=shared_counts,
        denied_counts=denied_counts,
    )
