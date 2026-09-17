"""
Evaluation: turn a set of flagged consumer IDs into the detection-rate
number the execution doc calls "the one number judges score" — the
isolated-vs-pooled comparison on the low-data site.

Labels are only used here, for evaluation. Neither the isolation forest
(detector.py) nor the pooled re-check (pooled_recheck.py) ever sees
`is_theft` — this mirrors how a real DISCOM would operate, since it never
has ground truth at detection time either.
"""

from __future__ import annotations

from dataclasses import dataclass

from detection.dataset import Consumer


@dataclass(frozen=True)
class DetectionMetrics:
    total_consumers: int
    total_theft: int
    total_honest: int
    flagged: int
    true_positives: int
    false_positives: int
    false_negatives: int
    detection_rate: float  # recall on theft consumers -- THE number
    precision: float
    false_positive_rate: float

    def summary_line(self, label: str) -> str:
        return (
            f"{label}: detection_rate={self.detection_rate:.1%} "
            f"({self.true_positives}/{self.total_theft} theft caught), "
            f"precision={self.precision:.1%}, "
            f"false_positive_rate={self.false_positive_rate:.1%}"
        )


def evaluate_detection(consumers: list[Consumer], flagged_consumer_ids: set[str]) -> DetectionMetrics:
    """Score a set of flagged consumer IDs against ground-truth theft labels."""
    theft_ids = {c.consumer_id for c in consumers if c.is_theft}
    honest_ids = {c.consumer_id for c in consumers if not c.is_theft}

    true_positives = len(flagged_consumer_ids & theft_ids)
    false_positives = len(flagged_consumer_ids & honest_ids)
    false_negatives = len(theft_ids - flagged_consumer_ids)

    detection_rate = (true_positives / len(theft_ids)) if theft_ids else 0.0
    precision = (true_positives / len(flagged_consumer_ids)) if flagged_consumer_ids else 0.0
    false_positive_rate = (false_positives / len(honest_ids)) if honest_ids else 0.0

    return DetectionMetrics(
        total_consumers=len(consumers),
        total_theft=len(theft_ids),
        total_honest=len(honest_ids),
        flagged=len(flagged_consumer_ids),
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        detection_rate=detection_rate,
        precision=precision,
        false_positive_rate=false_positive_rate,
    )
