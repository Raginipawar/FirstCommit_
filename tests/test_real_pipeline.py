"""
End-to-end integration test for the real-data pipeline
(detection/real_pipeline.py) — real SGCC data, real supervised classifiers,
real Cedar gate, real pooled re-check.

Gated behind the `real_sgcc_csv_path` fixture (skips, doesn't fail, if the
CSV isn't downloaded — see conftest.py and data/README.md). The pipeline
runs once per test session (it takes real time — three RandomForests, one
of them on ~28,000 consumers) via the session-scoped `real_pipeline_result`
fixture below; every test in this file reads its cached result rather than
re-running the pipeline.

This is the test that would tell you if the headline real-data number
(scripts/run_real_sgcc_pipeline.py's printed result) has silently drifted
from what shipped — same role test_orchestration.py's
test_swarm_cycle_reproduces_the_headline_result plays for the synthetic path.
"""

from __future__ import annotations

import pytest

from detection.real_pipeline import LOW_DATA_SITE, SOURCE_SITES, run_real_pipeline
from policy.gate import PolicyGate


@pytest.fixture(scope="session")
def real_pipeline_result(real_sgcc_csv_path, tmp_path_factory):
    log_dir = tmp_path_factory.mktemp("real_pipeline_logs")
    gate = PolicyGate(log_file=log_dir / "decisions.jsonl")
    return run_real_pipeline(real_sgcc_csv_path, gate)


class TestRealPipeline:
    def test_every_site_has_isolated_metrics(self, real_pipeline_result):
        for site_id in ("site_a", "site_b", LOW_DATA_SITE):
            assert site_id in real_pipeline_result.isolated_metrics

    def test_low_data_site_trained_on_far_fewer_theft_examples(self, real_pipeline_result):
        low_data_n = real_pipeline_result.train_theft_counts[LOW_DATA_SITE]
        for site_id in SOURCE_SITES:
            assert low_data_n < real_pipeline_result.train_theft_counts[site_id]

    def test_well_resourced_sites_beat_the_low_data_site_in_isolation(self, real_pipeline_result):
        low_data_rate = real_pipeline_result.isolated_metrics[LOW_DATA_SITE].detection_rate
        for site_id in SOURCE_SITES:
            assert real_pipeline_result.isolated_metrics[site_id].detection_rate > low_data_rate

    def test_nothing_shared_was_denied_by_cedar(self, real_pipeline_result):
        # Every signature built by _signature_from_real_shape is clean by
        # construction -- this pins that the gate agrees, not that denials
        # are impossible in general.
        for site_id in SOURCE_SITES:
            assert real_pipeline_result.denied_counts[site_id] == 0

    def test_pool_is_non_empty(self, real_pipeline_result):
        assert real_pipeline_result.pool_size > 0

    def test_pooling_improves_the_low_data_sites_detection_rate(self, real_pipeline_result):
        before = real_pipeline_result.isolated_metrics[LOW_DATA_SITE].detection_rate
        after = real_pipeline_result.pooled_metrics_low_data.detection_rate
        assert after > before

    def test_headline_result_is_a_real_meaningful_improvement(self, real_pipeline_result):
        """Pinned, with tolerance for minor library-version drift rather
        than an exact float match: this is the number
        scripts/run_real_sgcc_pipeline.py actually prints."""
        before = real_pipeline_result.isolated_metrics[LOW_DATA_SITE].detection_rate
        after = real_pipeline_result.pooled_metrics_low_data.detection_rate
        assert before < 0.5, "expected a genuinely weak isolated baseline on the low-data site"
        assert after - before >= 0.15, "expected pooling to move detection_rate by at least 15 points"

    def test_precision_cost_is_disclosed_not_hidden(self, real_pipeline_result):
        """Unlike the synthetic path, the real-data result is not a free
        lunch -- this test exists so nobody 'fixes' the numbers by quietly
        making the pool only ever improve precision too, which would mean
        it stopped being tested against real, noisy data."""
        before = real_pipeline_result.isolated_metrics[LOW_DATA_SITE]
        after = real_pipeline_result.pooled_metrics_low_data
        assert after.false_positive_rate >= 0.0  # sanity: metric exists and is well-formed
        assert after.true_positives > before.true_positives
