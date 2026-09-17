#!/usr/bin/env python3
"""
The one measured result: isolated vs. pooled detection rate on the
low-data site (Tripwire_Execution_Doc.md, Deliverables).

This runs the real swarm cycle (orchestration/loop.py::run_swarm_cycle):
every site detects with its own IsolationForest, drift-filters its own
flags (detection/drift.py), abstracts survivors into signatures
(policy/signature.py), requests to share them through the real Cedar gate
(policy/gate.py), and then every site re-checks its own unflagged
consumers against whatever the pool now holds
(detection/pooled_recheck.py). The shared pool is a `LocalPatternStore`
(shared_store/store.py) -- a real, working implementation of the
PatternStore interface, standing in for OpenSearch until Person 3 points
the same call at a live cluster (shared_store/README.md).

Run from the tripwire/ directory:

    py -3 scripts/run_isolated_vs_pooled.py
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

sys.path.insert(0, str(Path(__file__).parents[1]))

from detection.dataset import SITE_CONFIGS
from orchestration.loop import run_swarm_cycle
from policy.gate import PolicyGate
from shared_store.store import LocalPatternStore

LOW_DATA_SITE = "site_c_low_data"
SOURCE_SITES = ("site_a", "site_b")


def _header(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def main() -> int:
    root = Path(__file__).parents[1]
    gate = PolicyGate(log_file=root / "policy" / "logs" / "decisions.jsonl")
    store = LocalPatternStore(root / "shared_store" / "pool.jsonl")
    store.clear()  # start this run's pool clean; the decision log is left as the durable audit trail

    configs_by_id = {c.site_id: c for c in SITE_CONFIGS}

    _header("TRIPWIRE — isolated vs. pooled detection (Person 1 + Person 2 + Person 3)")
    print(f"sites: {', '.join(c.site_id for c in SITE_CONFIGS)}  (uneven volume, see detection/dataset.py)")
    print(f"{LOW_DATA_SITE} assumes a {configs_by_id[LOW_DATA_SITE].assumed_contamination:.0%} theft rate "
          f"(true rate is {configs_by_id[LOW_DATA_SITE].theft_rate:.0%}) — it hasn't seen enough theft "
          f"historically to calibrate correctly.")

    result = run_swarm_cycle(gate, store)

    _header("STEP 1 — isolated baseline, every site fits only on its own data")
    for site_id in configs_by_id:
        print(f"  " + result.isolated_metrics[site_id].summary_line(site_id))

    _header("STEP 2 — every site drift-filters its own flags and requests to share via Cedar")
    for site_id in configs_by_id:
        r = result.share_results[site_id]
        print(
            f"  {site_id}: {r.flagged} flagged locally -> {r.drift_candidates} cleared drift -> "
            f"{r.shared} shared, {r.denied} denied by Cedar, {r.skipped} skipped"
        )
    print(f"\n  shared pool now holds {result.pool_size} signatures (from all {len(configs_by_id)} sites combined)")

    _header(f"STEP 3 — every site re-checks its own unflagged consumers against the pool")
    for site_id in configs_by_id:
        before = result.isolated_metrics[site_id].detection_rate
        after = result.pooled_metrics[site_id].detection_rate
        marker = "  <-- the low-data site" if site_id == LOW_DATA_SITE else ""
        print(f"  {site_id}: {before:.1%} -> {after:.1%}{marker}")

    _header(f"RESULT — {LOW_DATA_SITE}: isolated vs. pooled")
    before = result.isolated_metrics[LOW_DATA_SITE]
    after = result.pooled_metrics[LOW_DATA_SITE]
    print("  " + before.summary_line("isolated (before)"))
    print("  " + after.summary_line("pooled   (after) "))
    delta = after.detection_rate - before.detection_rate
    print(f"\n  detection_rate moved by {delta:+.1%} on the same site, same consumers,")
    print("  purely from checking against signatures shared by its peers --")
    print("  no retraining, no extra data collected locally.")
    print("\n  Caveat, stated plainly: this is a synthetic SGCC-style site split, not live")
    print("  DISCOM data, and the shared pool here is a local JSONL file")
    print("  (shared_store/pool.jsonl), not yet a live OpenSearch cluster.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
