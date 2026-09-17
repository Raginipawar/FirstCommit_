"""
The full swarm cycle: every site detects and shares, then every site
re-checks against whatever the others have shared -- "no central brain...
each site is an independent Strands agent making its own call about its
own data" (Tripwire_Execution_Doc.md, 3a).

This generalizes scripts/run_isolated_vs_pooled.py's original one-site
(site_c_low_data-only) demonstration to every site, which is the more
faithful reading of the swarm design: nothing about the mechanism is
specific to the low-data site, it's just the site where the effect is
most visible because it's the one with room to improve.

`run_swarm_cycle` is one round: everyone detects once, shares once,
re-checks once. Person 3's live version wraps this in an actual continuous
loop (new readings arriving over time) and a persistent `PatternStore` --
see orchestration/README.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from detection.baseline import DetectionMetrics, evaluate_detection
from detection.dataset import SITE_CONFIGS, SiteConfig, generate_all_sites
from orchestration.agent import ShareRoundResult, SiteAgent
from policy.gate import PolicyGate
from shared_store.store import PatternStore


@dataclass(frozen=True)
class SwarmCycleResult:
    isolated_metrics: dict[str, DetectionMetrics]
    pooled_metrics: dict[str, DetectionMetrics]
    share_results: dict[str, ShareRoundResult]
    pool_size: int


def run_swarm_cycle(
    gate: PolicyGate,
    store: PatternStore,
    configs: tuple[SiteConfig, ...] = SITE_CONFIGS,
) -> SwarmCycleResult:
    """Run one full detect -> share -> re-check round across every site.

    `gate` and `store` are shared across all sites deliberately -- they are
    the one Cedar policy boundary and the one shared pool every site talks
    to. Each site's underlying data and detector stay private to its own
    `SiteAgent`.
    """
    sites = generate_all_sites(configs)
    agents = {c.site_id: SiteAgent(c, sites[c.site_id], gate, store) for c in configs}

    isolated_metrics: dict[str, DetectionMetrics] = {}
    share_results: dict[str, ShareRoundResult] = {}

    # Phase 1: every site detects and shares independently -- no site waits
    # on another, matching "no central brain" (3a). Order doesn't matter
    # for correctness; it's sequential here only because this is one process.
    for site_id, agent in agents.items():
        flagged = agent.detect()
        isolated_metrics[site_id] = evaluate_detection(sites[site_id], agent.isolated_flag_ids())
        share_results[site_id] = agent.share_round(flagged)

    # Phase 2: every site re-checks against whatever is in the pool *after*
    # everyone has shared. A site's own signatures are excluded from its
    # own re-check (PatternStore.query(exclude_site=...)) -- a site
    # doesn't need pooled help catching what it already caught itself.
    pooled_metrics: dict[str, DetectionMetrics] = {}
    for site_id, agent in agents.items():
        pooled_ids = agent.receive_and_recheck()
        pooled_metrics[site_id] = evaluate_detection(sites[site_id], pooled_ids)

    return SwarmCycleResult(
        isolated_metrics=isolated_metrics,
        pooled_metrics=pooled_metrics,
        share_results=share_results,
        pool_size=store.count(),
    )
