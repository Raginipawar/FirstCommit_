"""
One substation's loop: detect -> abstract -> request-to-share -> receive ->
re-check (Tripwire_Execution_Doc.md, Person 3's task list).

`SiteAgent` is deterministic Python, not yet an LLM-backed Strands `Agent`
-- see this module's module-level docstring section below and
orchestration/README.md for exactly how thin the gap to a real Strands
tool is. Building it this way first means the actual detect/share/re-check
logic is fully testable and free to run, with no model credentials or API
spend required; wrapping `share_round()` and `receive_and_recheck()` as
`@tool`-decorated functions for a Strands `Agent` later doesn't change
what they do, only who calls them and when.
"""

from __future__ import annotations

from dataclasses import dataclass

from detection.dataset import Consumer, SiteConfig
from detection.detector import FlaggedAnomaly, SiteDetector
from detection.drift import filter_for_sharing
from detection.features import ConsumerFeatures, extract_all, to_anomaly_record
from detection.pooled_recheck import build_pattern_index, recheck_against_pool
from policy.gate import PolicyGate
from policy.signature import AbstractionError, abstract_to_signature
from shared_store.store import PatternStore


@dataclass(frozen=True)
class ShareRoundResult:
    """What happened when this site tried to share its candidate anomalies."""

    site_id: str
    flagged: int
    drift_candidates: int
    shared: int
    denied: int
    skipped: int


class SiteAgent:
    """Wraps one site's detector, this site's slice of the Cedar gate and
    the shared store, and the drift/abstraction glue between them.

    One `SiteAgent` per substation. The `gate` and `store` are shared
    across every agent in a run (they represent the one Cedar policy
    boundary and the one shared pool that all sites talk to) -- only the
    detector and the underlying consumer data are private to each agent,
    matching "each site is a Strands agent running its own detector,
    wrapped around the same private data it always had"
    (Tripwire_Execution_Doc.md, Architecture).
    """

    def __init__(
        self,
        config: SiteConfig,
        consumers: list[Consumer],
        gate: PolicyGate,
        store: PatternStore,
    ) -> None:
        self.site_id = config.site_id
        self.config = config
        self.consumers = consumers
        self.features: list[ConsumerFeatures] = extract_all(consumers)
        self.detector = SiteDetector(contamination=config.assumed_contamination).fit(self.features)
        self.gate = gate
        self.store = store
        self._isolated_flag_ids: set[str] = set()

    def detect(self) -> list[FlaggedAnomaly]:
        """Step 1: this site's own isolated flags, from its own detector alone."""
        flagged = self.detector.flag_anomalies(self.features)
        self._isolated_flag_ids = {f.consumer.consumer_id for f in flagged}
        return flagged

    def isolated_flag_ids(self) -> set[str]:
        """The flags detect() produced, before any pooled information."""
        return set(self._isolated_flag_ids)

    def share_round(self, flagged: list[FlaggedAnomaly]) -> ShareRoundResult:
        """Steps 2-3: drift-filter what's surprising enough, abstract it, and
        request to share each candidate through the Cedar gate.

        Every decision -- allowed or denied -- is already logged by
        `gate.evaluate_share_request`; this method doesn't log anything a
        second time.
        """
        candidates = filter_for_sharing(flagged)
        shared = denied = skipped = 0
        for anomaly in candidates:
            record = to_anomaly_record(anomaly.consumer, anomaly.features, anomaly.anomaly_score)
            try:
                signature = abstract_to_signature(record)
            except AbstractionError:
                skipped += 1
                continue
            decision = self.gate.evaluate_share_request(self.site_id, signature)
            if decision.allowed:
                self.store.index(signature.to_dict())
                shared += 1
            else:
                denied += 1
        return ShareRoundResult(
            site_id=self.site_id,
            flagged=len(flagged),
            drift_candidates=len(candidates),
            shared=shared,
            denied=denied,
            skipped=skipped,
        )

    def receive_and_recheck(self) -> set[str]:
        """Steps 4-5: pull every other site's shared signatures and re-check
        this site's own unflagged consumers against them.

        Returns the updated flagged-consumer-id set (isolated flags plus
        anything newly caught via the pool) -- never smaller than
        `isolated_flag_ids()`, see detection/pooled_recheck.py.
        """
        pooled = self.store.query(exclude_site=self.site_id)
        pattern_index = build_pattern_index(pooled)
        return recheck_against_pool(self.features, self._isolated_flag_ids, pattern_index)
