"""
Tests for orchestration/strands_agent.py -- the real Strands-orchestrated
swarm cycle, backed by a local Ollama model (see that module's docstring
for why Ollama rather than a cloud provider).

These need an actual Ollama daemon with the model pulled -- there is no
way to exercise real LLM tool-calling behaviour against a mock, and a
mock would just prove the mock works. Skipped automatically wherever
Ollama isn't reachable (this repo's default CI, most reviewers' machines),
the same pattern shared_store/store.py uses for the untested-against-a-
live-cluster OpenSearchPatternStore.

Run for real:

    ollama pull qwen2.5:1.5b
    py -3 -m pytest tests/test_strands_agent.py -v
"""

from __future__ import annotations

import urllib.request

import pytest

from detection.dataset import SITE_CONFIGS
from orchestration.strands_agent import DEFAULT_MODEL_ID, run_swarm_cycle_via_strands
from policy.gate import PolicyGate
from shared_store.store import LocalPatternStore

LOW_DATA_SITE = "site_c_low_data"


def _ollama_reachable() -> bool:
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=1.5)
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _ollama_reachable(),
    reason=f"Ollama isn't running on localhost:11434 (needs `ollama pull {DEFAULT_MODEL_ID}` first)",
)


def test_strands_agent_swarm_cycle(tmp_path):
    """`run_swarm_cycle_via_strands` retries internally (see its
    docstring and orchestration/strands_agent.py's module docstring,
    point 3, for why: an earlier design shared one Agent's conversation
    across both phases and failed often; giving each phase a fresh Agent
    fixed that, but the retry is kept as a safety margin rather than
    trusting a small local model's tool-calling compliance on faith."""
    gate = PolicyGate(log_file=tmp_path / "decisions.jsonl")
    store = LocalPatternStore(tmp_path / "pool.jsonl")

    result = run_swarm_cycle_via_strands(gate, store, SITE_CONFIGS)
    cycle = result.cycle

    site_ids = {c.site_id for c in SITE_CONFIGS}
    assert set(cycle.isolated_metrics) == site_ids
    assert set(cycle.pooled_metrics) == site_ids

    # Not pinned to exact numbers -- detection/dataset.py's drift filter has
    # run-to-run variance of its own even via the plain loop (see
    # test_orchestration.py's relational, not exact, assertions).
    before = cycle.isolated_metrics[LOW_DATA_SITE]
    after = cycle.pooled_metrics[LOW_DATA_SITE]

    assert before.detection_rate < 0.5, "expected a weak isolated baseline on the low-data site"
    assert after.detection_rate > before.detection_rate, "expected pooling to visibly help"
    assert after.false_positive_rate == 0.0, "expected the drift filter to keep the pool clean"

    for site_id in cycle.isolated_metrics:
        assert cycle.pooled_metrics[site_id].detection_rate >= cycle.isolated_metrics[site_id].detection_rate
