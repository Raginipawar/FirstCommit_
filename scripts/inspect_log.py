#!/usr/bin/env python3
"""
CLI for inspecting the policy decision log — this is what "log every policy
decision, make it inspectable" (Person 2's task list) means in practice: any
teammate, mentor, or judge can see exactly why a given payload was allowed or
denied without reading Python.

Examples:

    py -3 scripts/inspect_log.py
    py -3 scripts/inspect_log.py --site site_c_low_data
    py -3 scripts/inspect_log.py --decision deny
    py -3 scripts/inspect_log.py --tail 5
    py -3 scripts/inspect_log.py --summary-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:  # see scripts/demo_block_then_pass.py for why this is needed on Windows
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

sys.path.insert(0, str(Path(__file__).parents[1]))

from policy.decision_log import filter_records, iter_records, summarize

_DEFAULT_LOG = Path(__file__).parents[1] / "policy" / "logs" / "decisions.jsonl"


def _format_record(r: dict) -> str:
    tag = "ALLOW" if r.get("allowed") else "DENY "
    reasons = r.get("reasons") or []
    reason = reasons[0] if reasons else ""
    matched = ",".join(r.get("matched_policies", [])) or "none"
    return (
        f"[{tag}] {r.get('checked_at', '?')}  "
        f"{r.get('site_id', '?')} -> {r.get('resource_id', '?')}  "
        f"kind={r.get('kind', '?')} granularity={r.get('granularity', '?')} "
        f"matched={matched}"
        + (f"\n         reason: {reason}" if reason else "")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log-file", default=str(_DEFAULT_LOG), help="path to decisions.jsonl")
    parser.add_argument("--site", default=None, help="filter to one site_id")
    parser.add_argument("--decision", default=None, choices=["allow", "deny"], help="filter to allow or deny")
    parser.add_argument("--kind", default=None, help="filter to a payload kind (raw_record / signature)")
    parser.add_argument("--tail", type=int, default=None, help="show only the last N matching records")
    parser.add_argument("--summary-only", action="store_true", help="print only the aggregate summary")
    args = parser.parse_args()

    log_path = Path(args.log_file)
    if not log_path.exists():
        print(f"No decision log at {log_path} yet — run scripts/demo_block_then_pass.py first.")
        return 1

    records = list(iter_records(log_path))
    filtered = filter_records(records, site_id=args.site, decision=args.decision, kind=args.kind)

    if not args.summary_only:
        shown = filtered if args.tail is None else filtered[-args.tail:]
        if not shown:
            print("No decisions match that filter.")
        for r in shown:
            print(_format_record(r))
        print()

    summary = summarize(filtered)
    print(f"--- summary ({len(filtered)} of {len(records)} total records) ---")
    print(f"allowed        : {summary['allowed']}")
    print(f"denied         : {summary['denied']}")
    print(f"allow rate     : {summary['allow_rate']:.1%}")
    print(f"by site        : {summary['by_site']}")
    print(f"by kind        : {summary['by_kind']}")
    print(f"denial reasons : {summary['denial_reasons']}")
    print(f"matched policies: {summary['matched_policy_counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
