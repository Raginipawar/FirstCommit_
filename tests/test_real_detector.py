"""
Unit tests for the supervised per-site detector (detection/real_detector.py).

Uses fabricated RealConsumer objects rather than the actual CSV -- fast,
always run, and tests the detector's own mechanics (train/test split,
fitting, scoring) independently of whether the real dataset is downloaded.
The real, pinned end-to-end number lives in test_real_pipeline.py, gated
behind the real_sgcc_csv_path fixture.
"""

from __future__ import annotations

import numpy as np
import pytest

from detection.real_dataset import RealConsumer
from detection.real_detector import SupervisedSiteDetector


def _make_consumers(n_honest: int, n_theft: int, length: int = 1034, seed: int = 0) -> list[RealConsumer]:
    rng = np.random.default_rng(seed)
    consumers = []
    for i in range(n_honest):
        series = 100 + rng.normal(0, 2, size=length)
        consumers.append(RealConsumer(site_id="site_test", consumer_id=f"honest-{i}", raw_series=series, is_theft=False))
    for i in range(n_theft):
        series = 100 + rng.normal(0, 2, size=length)
        series[600:850] = 30 + rng.normal(0, 1, size=250)  # a real, sustained drop
        consumers.append(RealConsumer(site_id="site_test", consumer_id=f"theft-{i}", raw_series=series, is_theft=True))
    return consumers


class TestSupervisedSiteDetector:
    def test_fit_requires_at_least_ten_consumers(self):
        with pytest.raises(ValueError):
            SupervisedSiteDetector().fit(_make_consumers(3, 2))

    def test_score_before_fit_raises(self):
        with pytest.raises(RuntimeError):
            SupervisedSiteDetector().score_test_set()

    def test_fit_returns_self_for_chaining(self):
        detector = SupervisedSiteDetector()
        consumers = _make_consumers(60, 20)
        assert detector.fit(consumers) is detector

    def test_train_test_split_covers_every_consumer_exactly_once(self):
        consumers = _make_consumers(60, 20)
        detector = SupervisedSiteDetector(test_size=0.3).fit(consumers)
        train_ids = {c.consumer_id for c in detector.train_consumers}
        test_ids = {c.consumer_id for c in detector.test_consumers}
        assert train_ids.isdisjoint(test_ids)
        assert train_ids | test_ids == {c.consumer_id for c in consumers}

    def test_n_train_theft_counts_correctly(self):
        consumers = _make_consumers(60, 20)
        detector = SupervisedSiteDetector(test_size=0.3, random_state=0).fit(consumers)
        expected = sum(1 for c in detector.train_consumers if c.is_theft)
        assert detector.n_train_theft == expected

    def test_score_test_set_covers_every_test_consumer(self):
        consumers = _make_consumers(60, 20)
        detector = SupervisedSiteDetector().fit(consumers)
        flags = detector.score_test_set()
        assert {f.consumer.consumer_id for f in flags} == {c.consumer_id for c in detector.test_consumers}

    def test_probabilities_are_in_valid_range(self):
        consumers = _make_consumers(60, 20)
        detector = SupervisedSiteDetector().fit(consumers)
        flags = detector.score_test_set()
        for f in flags:
            assert 0.0 <= f.probability <= 1.0

    def test_a_well_trained_detector_separates_obvious_theft(self):
        """A clean, obvious sustained-drop pattern with plenty of training
        examples should score noticeably higher than an obviously flat one."""
        consumers = _make_consumers(200, 60)
        detector = SupervisedSiteDetector(random_state=0).fit(consumers)
        flags = detector.score_test_set()
        theft_scores = [f.probability for f in flags if f.consumer.is_theft]
        honest_scores = [f.probability for f in flags if not f.consumer.is_theft]
        assert sum(theft_scores) / len(theft_scores) > sum(honest_scores) / len(honest_scores)

    def test_fewer_training_theft_examples_yields_no_crash_and_valid_output(self):
        """The "low-data" story: a detector trained on very few theft
        examples should still run without error and produce valid scores,
        even if (as expected) it performs worse."""
        consumers = _make_consumers(60, 3)
        detector = SupervisedSiteDetector(test_size=0.3, random_state=0).fit(consumers)
        flags = detector.score_test_set()
        assert len(flags) == len(detector.test_consumers)
