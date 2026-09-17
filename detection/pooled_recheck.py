"""
The pooled-memory check: "each site checks new consumption against its own
model and the pooled library" (TeamSaturn_ProjectBrief_DISCOM.pdf, section
9). This is the mechanism behind the execution doc's before/after number —
"a low-data site catching a peer's surprise signal" — implemented as a
direct shape-key lookup against signatures other sites already shared.

Deliberately reuses Person 2's own abstraction and shape_key(), rather than
a separate similarity metric: two consumers "match" here exactly when their
signatures would bucket to the same shape_key, i.e. exactly when Person 2's
Cedar gate would have treated them as the same kind of pattern. Detection
and policy share one definition of "same shape" instead of two that could
quietly disagree.
"""

from __future__ import annotations

from detection.features import ConsumerFeatures, to_anomaly_record
from policy.signature import AbstractionError, Signature, abstract_to_signature


def build_pattern_index(pooled_signatures: list[dict]) -> set[tuple]:
    """Shape-key fingerprints of every signature already in the shared pool.

    `pooled_signatures` should be `Signature.to_dict()` results that already
    passed Person 2's Cedar gate (`decision.allowed is True`) -- this
    function doesn't re-check that; it trusts whatever the caller collected
    from the pool.
    """
    index: set[tuple] = set()
    for sig in pooled_signatures:
        try:
            key = (
                sig["load_drop_magnitude_bucket"],
                sig["drop_duration_bucket"],
                sig["timing_bucket"],
                sig["recovery_shape"],
                sig["volatility_bucket"],
            )
        except KeyError:
            continue
        index.add(key)
    return index


def recheck_against_pool(
    consumer_features: list[ConsumerFeatures],
    already_flagged_ids: set[str],
    pattern_index: set[tuple],
) -> set[str]:
    """A site's own isolated flags, plus anyone whose shape matches the pool.

    Never removes a flag the site's own isolation forest already made --
    the pool can only add detections a low-data site's own model missed,
    never take away ones it already found. This is what makes the
    resulting detection_rate mathematically >= the isolated one: see
    tests/test_pooled_recheck.py::test_pooled_detection_rate_never_drops.
    """
    updated = set(already_flagged_ids)
    for cf in consumer_features:
        if cf.consumer.consumer_id in updated:
            continue
        anomaly_record = to_anomaly_record(cf.consumer, cf.features, anomaly_score=0.0)
        try:
            signature: Signature = abstract_to_signature(anomaly_record)
        except AbstractionError:
            continue
        if signature.shape_key() in pattern_index:
            updated.add(cf.consumer.consumer_id)
    return updated
