"""Unit tests for detection metrics (detection/baseline.py)."""

from __future__ import annotations

from detection.baseline import evaluate_detection
from detection.dataset import Consumer
import numpy as np


def _consumer(consumer_id: str, is_theft: bool) -> Consumer:
    return Consumer(
        site_id="site_test",
        consumer_id=consumer_id,
        meter_id=f"MTR-{consumer_id}",
        household_type="residential",
        lat=0.0,
        lon=0.0,
        billing_cycle_day=15,
        series=np.zeros(10),
        is_theft=is_theft,
    )


def test_perfect_detection():
    consumers = [_consumer("c1", True), _consumer("c2", True), _consumer("c3", False)]
    metrics = evaluate_detection(consumers, {"c1", "c2"})
    assert metrics.detection_rate == 1.0
    assert metrics.precision == 1.0
    assert metrics.false_positive_rate == 0.0


def test_missed_theft_lowers_detection_rate_not_precision():
    consumers = [_consumer("c1", True), _consumer("c2", True), _consumer("c3", False)]
    metrics = evaluate_detection(consumers, {"c1"})
    assert metrics.detection_rate == 0.5
    assert metrics.precision == 1.0
    assert metrics.false_negatives == 1


def test_false_positive_lowers_precision_not_detection_rate():
    consumers = [_consumer("c1", True), _consumer("c2", False), _consumer("c3", False)]
    metrics = evaluate_detection(consumers, {"c1", "c2"})
    assert metrics.detection_rate == 1.0
    assert metrics.precision == 0.5
    assert metrics.false_positive_rate == 0.5


def test_no_flags_at_all():
    consumers = [_consumer("c1", True), _consumer("c2", False)]
    metrics = evaluate_detection(consumers, set())
    assert metrics.detection_rate == 0.0
    assert metrics.precision == 0.0  # defined as 0, not NaN, when nothing is flagged
    assert metrics.false_negatives == 1


def test_no_theft_consumers_at_all_detection_rate_is_zero_not_nan():
    consumers = [_consumer("c1", False), _consumer("c2", False)]
    metrics = evaluate_detection(consumers, {"c1"})
    assert metrics.detection_rate == 0.0
    assert metrics.total_theft == 0


def test_summary_line_is_readable():
    consumers = [_consumer("c1", True), _consumer("c2", False)]
    metrics = evaluate_detection(consumers, {"c1"})
    line = metrics.summary_line("site_test")
    assert "site_test" in line
    assert "100.0%" in line
