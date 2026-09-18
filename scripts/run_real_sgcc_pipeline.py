#!/usr/bin/env python3
"""
The real-data version of scripts/run_isolated_vs_pooled.py: real SGCC
consumers, a real supervised classifier per site, real Cedar-gated
sharing, and a real pooled re-check on the low-data site.

Needs the real dataset downloaded locally first (not committed to this
repo — see data/README.md):

    kaggle.com/datasets/bensalem14/sgcc-dataset -> "data set.csv"

Run from the tripwire/ directory:

    py -3 scripts/run_real_sgcc_pipeline.py "C:\\path\\to\\data set.csv"
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

sys.path.insert(0, str(Path(__file__).parents[1]))

from detection.real_pipeline import LOW_DATA_SITE, SOURCE_SITES, run_real_pipeline
from policy.gate import PolicyGate


def _header(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    csv_path = sys.argv[1]

    root = Path(__file__).parents[1]
    gate = PolicyGate(log_file=root / "policy" / "logs" / "decisions.jsonl")

    _header("TRIPWIRE — real SGCC data, supervised classifier, Cedar-gated sharing")
    print("Loading and splitting the real dataset (this takes a few seconds)...")

    result = run_real_pipeline(csv_path, gate)

    _header("STEP 1 — isolated baseline: each site trains only on its own labelled history")
    for site_id in ("site_a", "site_b", LOW_DATA_SITE):
        m = result.isolated_metrics[site_id]
        n_theft_train = result.train_theft_counts[site_id]
        print(
            f"  {site_id}: trained on {n_theft_train} labelled theft cases -> "
            + m.summary_line(site_id)
        )

    _header("STEP 2 — confident, drift-cleared detections shared via Cedar")
    for site_id in SOURCE_SITES:
        print(
            f"  {site_id}: {result.shared_counts[site_id]} shared, "
            f"{result.denied_counts[site_id]} denied by Cedar"
        )
    print(f"\n  shared pool holds {result.pool_size} signatures (from {', '.join(SOURCE_SITES)})")

    _header(f"RESULT — {LOW_DATA_SITE}: isolated vs. pooled, on real held-out test consumers")
    before = result.isolated_metrics[LOW_DATA_SITE]
    after = result.pooled_metrics_low_data
    print("  " + before.summary_line("isolated (before)"))
    print("  " + after.summary_line("pooled   (after) "))
    delta = after.detection_rate - before.detection_rate
    print(f"\n  detection_rate moved by {delta:+.1%} on real, held-out SGCC test consumers,")
    print("  purely from checking against signatures shared by two other sites --")
    print(f"  trained on only {result.train_theft_counts[LOW_DATA_SITE]} of its own real labelled theft cases.")
    print()
    print("  Honest trade-off, stated plainly: unlike the synthetic demo, this real-data")
    print("  result has a precision cost (more false positives alongside the extra true")
    print("  positives) -- real, noisy data doesn't offer a free lunch. See")
    print("  detection/README.md, 'The real-data path,' for the full account.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
