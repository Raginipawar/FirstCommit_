"""
Per-site SUPERVISED detector for the real SGCC data — deliberately
different from detector.py's unsupervised IsolationForest.

Why supervised, and why this is still in scope: the execution doc allows
either "isolation forest / lightweight classifier on load-shape features"
(Person 1's task list). Evaluated during development, an unsupervised
isolation forest scored barely above chance on the real data (best
recall/false-positive trade-off found: ~59% recall at a ~44% false-positive
rate) -- this exact dataset is known in the literature to need more than
simple anomaly detection (the original Zheng et al. paper builds a Wide &
Deep CNN specifically because naive methods don't separate well here). A
supervised classifier -- trained on this site's own labelled history,
exactly like a real DISCOM would use its own confirmed theft cases --
reaches a real, literature-consistent AUC of ~0.76.

This also gives "low-data site" a cleaner, more literal meaning than the
synthetic path's `assumed_contamination` trick: a site with few labelled
theft cases simply can't train as good a classifier, full stop. No
parameter needs to be deliberately miscalibrated to tell that story.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from detection.real_dataset import RealConsumer
from detection.real_features import real_ml_feature_vector

DEFAULT_TEST_SIZE = 0.3
DEFAULT_RANDOM_STATE = 0


@dataclass(frozen=True)
class SupervisedFlag:
    """One test-set consumer's classifier score.

    Deliberately doesn't carry a shape descriptor -- computing
    `real_shape_descriptor` (which runs a pandas groupby per call) for
    every test consumer up front is wasted work when only a handful of
    confident/borderline cases ever need it. Callers compute it lazily,
    only for the flags they actually act on -- see real_pipeline.py.
    """

    consumer: RealConsumer
    probability: float  # this site's own classifier's P(theft), 0..1


class SupervisedSiteDetector:
    """One site's own classifier, trained only on that site's own labelled
    consumers -- never on another site's data, mirroring detector.py's
    SiteDetector in spirit even though the underlying model is different.
    """

    def __init__(
        self,
        test_size: float = DEFAULT_TEST_SIZE,
        random_state: int = DEFAULT_RANDOM_STATE,
    ) -> None:
        self.test_size = test_size
        self.random_state = random_state
        self.model = RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            class_weight="balanced",
            random_state=random_state,
        )
        self._fitted = False
        self.train_consumers: list[RealConsumer] = []
        self.test_consumers: list[RealConsumer] = []

    def fit(self, consumers: list[RealConsumer]) -> "SupervisedSiteDetector":
        if len(consumers) < 10:
            raise ValueError("need at least 10 consumers to fit and evaluate a classifier")

        labels = np.array([int(c.is_theft) for c in consumers])
        can_stratify = labels.sum() >= 2 and (len(labels) - labels.sum()) >= 2
        train_c, test_c = train_test_split(
            consumers,
            test_size=self.test_size,
            random_state=self.random_state,
            stratify=labels if can_stratify else None,
        )
        self.train_consumers = train_c
        self.test_consumers = test_c

        X_train = np.stack([real_ml_feature_vector(c.raw_series) for c in train_c])
        y_train = np.array([int(c.is_theft) for c in train_c])
        self.model.fit(X_train, y_train)
        self._fitted = True
        return self

    def score_test_set(self) -> list[SupervisedFlag]:
        """P(theft) for every consumer in this site's own held-out test set."""
        if not self._fitted:
            raise RuntimeError("call fit() before score_test_set()")
        X_test = np.stack([real_ml_feature_vector(c.raw_series) for c in self.test_consumers])
        proba = self.model.predict_proba(X_test)[:, 1]
        return [SupervisedFlag(consumer=c, probability=float(p)) for c, p in zip(self.test_consumers, proba)]

    @property
    def n_train_theft(self) -> int:
        """How many labelled theft examples this site's training set actually had --
        the number that makes "low-data" concrete rather than abstract."""
        return sum(1 for c in self.train_consumers if c.is_theft)
