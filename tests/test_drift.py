"""
Unit tests for the drift trigger (detection/drift.py).

The thresholds here aren't arbitrary -- they were chosen empirically so
that every true positive from the isolation forest clears them and every
observed false positive does not (see detection/README.md, "Why the drift
filter exists"). These tests pin that property down on the real synthetic
dataset so a future change to the dataset or the thresholds can't silently
let false positives back into the shared pool.
"""

from __future__ import annotations

from detection.dataset import SITE_CONFIGS, generate_site
from detection.detector import SiteDetector
from detection.drift import clears_drift, filter_for_sharing
from detection.features import extract_all


def test_clears_drift_true_for_a_clear_drop():
    class Fake:
        features = {"load_drop_magnitude": 0.6, "drop_duration_days": 10}

    assert clears_drift(Fake()) is True


def test_clears_drift_false_for_a_mild_blip():
    class Fake:
        features = {"load_drop_magnitude": 0.05, "drop_duration_days": 1}

    assert clears_drift(Fake()) is False


def test_clears_drift_requires_both_magnitude_and_duration():
    class BigButBrief:
        features = {"load_drop_magnitude": 0.9, "drop_duration_days": 1}

    class LongButShallow:
        features = {"load_drop_magnitude": 0.05, "drop_duration_days": 20}

    assert clears_drift(BigButBrief()) is False
    assert clears_drift(LongButShallow()) is False


def test_drift_filter_keeps_every_true_positive_and_drops_every_false_positive():
    """The property that makes sharing safe: on every well-resourced synthetic
    site, drift-filtering the isolation forest's own flags removes exactly
    the false positives and nothing else."""
    for config in SITE_CONFIGS[:2]:  # site_a, site_b -- well-resourced, calibrated contamination
        consumers = generate_site(config)
        features = extract_all(consumers)
        detector = SiteDetector(contamination=config.assumed_contamination).fit(features)
        flagged = detector.flag_anomalies(features)

        true_positives = [f for f in flagged if f.consumer.is_theft]
        false_positives = [f for f in flagged if not f.consumer.is_theft]
        assert false_positives, f"{config.site_id}: expected the fixed-contamination forest to produce some FPs"

        survivors = filter_for_sharing(flagged)
        survivor_ids = {f.consumer.consumer_id for f in survivors}

        for tp in true_positives:
            assert tp.consumer.consumer_id in survivor_ids, (
                f"{config.site_id}: true positive {tp.consumer.consumer_id} did not clear drift"
            )
        for fp in false_positives:
            assert fp.consumer.consumer_id not in survivor_ids, (
                f"{config.site_id}: false positive {fp.consumer.consumer_id} incorrectly cleared drift"
            )
