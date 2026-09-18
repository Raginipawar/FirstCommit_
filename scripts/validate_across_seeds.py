#!/usr/bin/env python3
"""
Multi-seed validation: turns the one measured isolated-vs-pooled result
into a claim backed by many independent runs, per
docs/Tripwire_Execution_Doc.md's validation methodology.

Re-runs the real swarm cycle (orchestration/loop.py::run_swarm_cycle)
`n_seeds` times, offsetting every site's random seed each time, and
reports whether the pooled improvement holds and whether the pooled
false-positive rate ever exceeds the isolated one. Nothing here is
mocked -- each run is a fresh, real detect -> drift -> abstract ->
Cedar gate -> pool -> recheck cycle against a scratch gate/store so
repeated runs don't compound on each other.

Run from the tripwire/ directory:

    py -3 scripts/validate_across_seeds.py
"""

from __future__ import annotations

import sys
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

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


def run_validation(n_seeds: int = 15) -> dict[str, Any]:
    """Run `n_seeds` independent swarm cycles and summarize the result.

    Returns per-seed records plus aggregate stats: mean/min improvement
    on the low-data site, and whether the pooled false-positive rate
    ever exceeded the isolated one across any seed or any site.
    """
    per_seed = []
    fpr_ever_worse = False

    for offset in range(n_seeds):
        configs = tuple(replace(c, seed=c.seed + offset) for c in SITE_CONFIGS)
        with tempfile.TemporaryDirectory() as tmp:
            gate = PolicyGate(log_file=Path(tmp) / "decisions.jsonl")
            store = LocalPatternStore(Path(tmp) / "pool.jsonl")
            result = run_swarm_cycle(gate, store, configs)

            site_records = {}
            for site_id in result.isolated_metrics:
                isolated = result.isolated_metrics[site_id]
                pooled = result.pooled_metrics[site_id]
                if pooled.false_positive_rate > isolated.false_positive_rate:
                    fpr_ever_worse = True
                site_records[site_id] = {
                    "isolated_detection_rate": isolated.detection_rate,
                    "pooled_detection_rate": pooled.detection_rate,
                    "improvement": pooled.detection_rate - isolated.detection_rate,
                    "isolated_false_positive_rate": isolated.false_positive_rate,
                    "pooled_false_positive_rate": pooled.false_positive_rate,
                }

            low = site_records[LOW_DATA_SITE]
            per_seed.append(
                {
                    "seed_offset": offset,
                    "sites": site_records,
                    "low_data_improvement": low["improvement"],
                }
            )

    improvements = [r["low_data_improvement"] for r in per_seed]
    aggregate = {
        "n_seeds": n_seeds,
        "low_data_site": LOW_DATA_SITE,
        "mean_improvement": sum(improvements) / len(improvements),
        "min_improvement": min(improvements),
        "max_improvement": max(improvements),
        "false_positive_rate_ever_worse_pooled": fpr_ever_worse,
    }
    return {"per_seed": per_seed, "aggregate": aggregate}


if __name__ == "__main__":
    result = run_validation()
    agg = result["aggregate"]
    print(f"Ran {agg['n_seeds']} independent seeds.\n")
    print(f"{LOW_DATA_SITE} improvement (pooled - isolated detection rate):")
    print(f"  mean: {agg['mean_improvement']:.3f}")
    print(f"  min:  {agg['min_improvement']:.3f}")
    print(f"  max:  {agg['max_improvement']:.3f}")
    print(
        "\nPooled false-positive rate ever exceeded isolated: "
        f"{agg['false_positive_rate_ever_worse_pooled']}"
    )
