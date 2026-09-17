"""
Per-site anomaly detector: an isolation forest trained only on that site's
own consumers, exactly as Tripwire_Execution_Doc.md specifies ("a
lightweight anomaly detector trained only on that site's own data — this
is the isolated baseline, and it is deliberately weak on low-data sites").

Deliberately unsupervised: `fit()` never sees the `is_theft` label. Labels
are only used afterwards, in baseline.py, to measure how well the
detector's flags line up with real theft — the same evaluation pattern the
EnsembleNTLDetect paper (Kulkarni et al., ICDMW 2021) uses for NTL
detection, where labelled theft cases are scarce and the detector has to
generalise from shape, not from being told the answer.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import IsolationForest

from detection.dataset import Consumer
from detection.features import ConsumerFeatures, extract_all

DEFAULT_CONTAMINATION = 0.10  # a DISCOM's rough working assumption for theft prevalence
DEFAULT_RANDOM_STATE = 0


@dataclass(frozen=True)
class FlaggedAnomaly:
    """One consumer the detector considers anomalous, ready to abstract."""

    consumer: Consumer
    anomaly_score: float  # 0..1, higher = more anomalous, min-max normalised over the fitted site
    features: dict[str, float]


class SiteDetector:
    """Wraps one site's IsolationForest: fit on that site's own data, nothing else.

    A low-data site's forest sees far fewer examples of what "normal" looks
    like at that site, which is exactly what makes its isolated baseline
    weak — there just isn't enough data for it to have learned a tight
    boundary around normal consumption yet.
    """

    def __init__(
        self,
        contamination: float = DEFAULT_CONTAMINATION,
        random_state: int = DEFAULT_RANDOM_STATE,
    ) -> None:
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=200,
        )
        self._fitted = False
        self._score_min = 0.0
        self._score_max = 1.0

    def fit(self, consumer_features: list[ConsumerFeatures]) -> "SiteDetector":
        if len(consumer_features) < 2:
            raise ValueError("need at least 2 consumers to fit an isolation forest")
        X = np.stack([cf.vector for cf in consumer_features])
        self.model.fit(X)

        raw_scores = -self.model.score_samples(X)  # higher = more anomalous
        self._score_min = float(raw_scores.min())
        self._score_max = float(raw_scores.max())
        self._fitted = True
        return self

    def _normalize(self, raw_scores: np.ndarray) -> np.ndarray:
        span = self._score_max - self._score_min
        if span <= 1e-12:
            return np.zeros_like(raw_scores)
        return np.clip((raw_scores - self._score_min) / span, 0.0, 1.0)

    def score(self, consumer_features: list[ConsumerFeatures]) -> np.ndarray:
        """Normalized anomaly scores (0..1) for a batch of consumers, no flagging."""
        if not self._fitted:
            raise RuntimeError("call fit() before score()")
        X = np.stack([cf.vector for cf in consumer_features])
        raw_scores = -self.model.score_samples(X)
        return self._normalize(raw_scores)

    def flag_anomalies(self, consumer_features: list[ConsumerFeatures]) -> list[FlaggedAnomaly]:
        """The detector's own isolated call: which consumers look anomalous.

        Uses IsolationForest.predict() (-1 = anomaly, 1 = normal), which
        respects the `contamination` this detector was constructed with —
        this is the isolated baseline flag set, before any pooled
        information is consulted.
        """
        if not self._fitted:
            raise RuntimeError("call fit() before flag_anomalies()")
        X = np.stack([cf.vector for cf in consumer_features])
        predictions = self.model.predict(X)  # -1 anomaly, 1 normal
        scores = self.score(consumer_features)

        flagged = []
        for cf, pred, score in zip(consumer_features, predictions, scores):
            if pred == -1:
                flagged.append(FlaggedAnomaly(consumer=cf.consumer, anomaly_score=float(score), features=cf.features))
        return flagged


def fit_and_flag(consumers: list[Consumer], contamination: float = DEFAULT_CONTAMINATION) -> tuple[SiteDetector, list[FlaggedAnomaly]]:
    """Convenience: extract features, fit a detector, and return its isolated flags."""
    features = extract_all(consumers)
    detector = SiteDetector(contamination=contamination).fit(features)
    return detector, detector.flag_anomalies(features)
