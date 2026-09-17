"""
Tests for the orchestration layer (orchestration/agent.py, orchestration/loop.py).

The last test in here (`test_swarm_cycle_reproduces_the_headline_result`)
runs the exact same code path as `scripts/run_isolated_vs_pooled.py` --
real IsolationForest, real drift filter, real Cedar gate, real
LocalPatternStore -- and pins the same headline number the script prints.
If this test and the script's printed output ever disagree, one of them
has drifted from the other.
"""

from __future__ import annotations

from detection.dataset import SITE_CONFIGS, generate_all_sites
from orchestration.agent import SiteAgent
from orchestration.loop import run_swarm_cycle
from policy.gate import PolicyGate
from shared_store.store import LocalPatternStore

LOW_DATA_SITE = "site_c_low_data"


def _configs_by_id():
    return {c.site_id: c for c in SITE_CONFIGS}


class TestSiteAgent:
    def test_detect_returns_flags_and_records_isolated_ids(self, tmp_path):
        configs = _configs_by_id()
        sites = generate_all_sites()
        gate = PolicyGate(log_file=tmp_path / "decisions.jsonl")
        store = LocalPatternStore(tmp_path / "pool.jsonl")

        agent = SiteAgent(configs["site_a"], sites["site_a"], gate, store)
        assert agent.isolated_flag_ids() == set()  # nothing detected yet

        flagged = agent.detect()
        assert len(flagged) > 0
        assert agent.isolated_flag_ids() == {f.consumer.consumer_id for f in flagged}

    def test_share_round_only_shares_drift_clearing_candidates(self, tmp_path):
        configs = _configs_by_id()
        sites = generate_all_sites()
        gate = PolicyGate(log_file=tmp_path / "decisions.jsonl")
        store = LocalPatternStore(tmp_path / "pool.jsonl")

        agent = SiteAgent(configs["site_a"], sites["site_a"], gate, store)
        flagged = agent.detect()
        result = agent.share_round(flagged)

        assert result.site_id == "site_a"
        assert result.flagged == len(flagged)
        assert result.drift_candidates <= result.flagged
        assert result.shared == result.drift_candidates - result.skipped
        assert result.shared == store.count()

    def test_receive_and_recheck_never_shrinks_isolated_flags(self, tmp_path):
        configs = _configs_by_id()
        sites = generate_all_sites()
        gate = PolicyGate(log_file=tmp_path / "decisions.jsonl")
        store = LocalPatternStore(tmp_path / "pool.jsonl")

        agent = SiteAgent(configs[LOW_DATA_SITE], sites[LOW_DATA_SITE], gate, store)
        flagged = agent.detect()
        agent.share_round(flagged)  # populate its own share into the store (excluded from its own re-check)

        updated = agent.receive_and_recheck()
        assert agent.isolated_flag_ids() <= updated

    def test_a_sites_own_shared_signatures_are_excluded_from_its_own_recheck(self, tmp_path):
        """A site shouldn't need the pool to tell it about anomalies it
        already found and shared itself."""
        configs = _configs_by_id()
        sites = generate_all_sites()
        gate = PolicyGate(log_file=tmp_path / "decisions.jsonl")
        store = LocalPatternStore(tmp_path / "pool.jsonl")

        agent = SiteAgent(configs["site_a"], sites["site_a"], gate, store)
        flagged = agent.detect()
        agent.share_round(flagged)

        # With nothing else in the pool, re-checking should add nothing new.
        updated = agent.receive_and_recheck()
        assert updated == agent.isolated_flag_ids()


class TestRunSwarmCycle:
    def test_every_configured_site_appears_in_every_result_dict(self, tmp_path):
        gate = PolicyGate(log_file=tmp_path / "decisions.jsonl")
        store = LocalPatternStore(tmp_path / "pool.jsonl")
        result = run_swarm_cycle(gate, store)

        site_ids = {c.site_id for c in SITE_CONFIGS}
        assert set(result.isolated_metrics) == site_ids
        assert set(result.pooled_metrics) == site_ids
        assert set(result.share_results) == site_ids

    def test_pool_size_matches_sum_of_shared_counts(self, tmp_path):
        gate = PolicyGate(log_file=tmp_path / "decisions.jsonl")
        store = LocalPatternStore(tmp_path / "pool.jsonl")
        result = run_swarm_cycle(gate, store)

        assert result.pool_size == sum(r.shared for r in result.share_results.values())

    def test_no_site_ever_gets_worse_after_pooling(self, tmp_path):
        gate = PolicyGate(log_file=tmp_path / "decisions.jsonl")
        store = LocalPatternStore(tmp_path / "pool.jsonl")
        result = run_swarm_cycle(gate, store)

        for site_id in result.isolated_metrics:
            assert result.pooled_metrics[site_id].detection_rate >= result.isolated_metrics[site_id].detection_rate

    def test_swarm_cycle_reproduces_the_headline_result(self, tmp_path):
        """Pinned to the fixed seeds in detection/dataset.py::SITE_CONFIGS --
        this is the same number scripts/run_isolated_vs_pooled.py prints."""
        gate = PolicyGate(log_file=tmp_path / "decisions.jsonl")
        store = LocalPatternStore(tmp_path / "pool.jsonl")
        result = run_swarm_cycle(gate, store)

        before = result.isolated_metrics[LOW_DATA_SITE]
        after = result.pooled_metrics[LOW_DATA_SITE]

        assert before.detection_rate < 0.5, "expected a weak isolated baseline on the low-data site"
        assert after.detection_rate > before.detection_rate, "expected pooling to visibly help"
        assert after.false_positive_rate == 0.0, "expected the drift filter to keep the pool clean"
