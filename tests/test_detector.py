"""Unit tests for the per-site isolation forest wrapper (detection/detector.py)."""

from __future__ import annotations

import pytest

from detection.dataset import SITE_CONFIGS, generate_site
from detection.detector import SiteDetector, fit_and_flag
from detection.features import extract_all


@pytest.fixture()
def site_a_features():
    consumers = generate_site(SITE_CONFIGS[0])  # site_a, theft_rate=0.10
    return extract_all(consumers)


def test_fit_requires_at_least_two_consumers():
    with pytest.raises(ValueError):
        SiteDetector().fit([])


def test_score_before_fit_raises(site_a_features):
    with pytest.raises(RuntimeError):
        SiteDetector().score(site_a_features)


def test_flag_anomalies_before_fit_raises(site_a_features):
    with pytest.raises(RuntimeError):
        SiteDetector().flag_anomalies(site_a_features)


def test_fit_returns_self_for_chaining(site_a_features):
    detector = SiteDetector()
    assert detector.fit(site_a_features) is detector


def test_scores_are_normalized_between_zero_and_one(site_a_features):
    detector = SiteDetector().fit(site_a_features)
    scores = detector.score(site_a_features)
    assert scores.min() >= 0.0
    assert scores.max() <= 1.0


def test_flagged_anomalies_have_the_highest_scores(site_a_features):
    detector = SiteDetector().fit(site_a_features)
    flagged = detector.flag_anomalies(site_a_features)
    all_scores = detector.score(site_a_features)
    flagged_ids = {f.consumer.consumer_id for f in flagged}

    threshold = min(f.anomaly_score for f in flagged)
    for cf, score in zip(site_a_features, all_scores):
        if cf.consumer.consumer_id not in flagged_ids:
            assert score <= threshold + 1e-9


def test_lower_contamination_flags_fewer_consumers(site_a_features):
    strict = SiteDetector(contamination=0.02).fit(site_a_features)
    loose = SiteDetector(contamination=0.20).fit(site_a_features)
    assert len(strict.flag_anomalies(site_a_features)) < len(loose.flag_anomalies(site_a_features))


def test_a_well_resourced_site_catches_most_of_its_own_theft(site_a_features):
    """site_a's assumed_contamination (0.10) matches its true theft_rate (0.10)
    -- it should catch the large majority of its theft consumers on its own."""
    detector = SiteDetector(contamination=0.10).fit(site_a_features)
    flagged = detector.flag_anomalies(site_a_features)
    flagged_ids = {f.consumer.consumer_id for f in flagged}
    theft_ids = {cf.consumer.consumer_id for cf in site_a_features if cf.consumer.is_theft}
    recall = len(flagged_ids & theft_ids) / len(theft_ids)
    assert recall > 0.8


def test_fit_and_flag_convenience_function():
    consumers = generate_site(SITE_CONFIGS[0])
    detector, flagged = fit_and_flag(consumers, contamination=0.10)
    assert isinstance(detector, SiteDetector)
    assert len(flagged) > 0
