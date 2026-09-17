"""
Decision logging: every Cedar authorization check, permitted or denied, is
appended as one JSON line. Nothing is ever overwritten or deleted from this
file by the gate itself — it's meant to be the audit trail a judge (or a
regulator) could read start to finish.

Deliberately stores `payload_attrs` (the coarse flags Cedar actually saw:
kind, has_meter_id, has_consumer_id, has_raw_series, has_household_field,
has_location, granularity) and never the underlying raw values. A denied
request is fully explainable from this log — you can see *that* has_meter_id
was true — without the log itself becoming a second place a real meter ID
could leak from.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator

# Local import kept inside functions where needed to avoid a circular import
# with gate.py (gate.py imports DecisionLogger from this module).


class DecisionLogger:
    """Appends PolicyDecision records to a JSONL file and reads them back."""

    def __init__(self, log_file: str | Path) -> None:
        self.log_path = Path(log_file)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, decision: Any) -> None:
        """Append one decision. Accepts anything with a `.to_dict()` method."""
        record = decision.to_dict()
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        records = []
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def clear(self) -> None:
        """Truncate the log. Used by tests and the demo script to start clean."""
        self.log_path.write_text("", encoding="utf-8")


def iter_records(log_file: str | Path) -> Iterator[dict[str, Any]]:
    """Stream records from a decision log without loading it all into memory."""
    path = Path(log_file)
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def filter_records(
    records: Iterable[dict[str, Any]],
    *,
    site_id: str | None = None,
    decision: str | None = None,
    kind: str | None = None,
) -> list[dict[str, Any]]:
    """Filter decision records by site, decision (Allow/Deny), and/or payload kind."""
    out = []
    for r in records:
        if site_id is not None and r.get("site_id") != site_id:
            continue
        if decision is not None and r.get("decision", "").lower() != decision.lower():
            continue
        if kind is not None and r.get("kind") != kind:
            continue
        out.append(r)
    return out


def summarize(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Roll a list of decision records up into judge-readable counters.

    Returns totals, a per-site breakdown, a per-denial-reason breakdown, and
    which of the two policy rules (forbid vs. permit) fired most often —
    exactly the numbers the block-then-pass proof and the README's write-up
    need to cite.
    """
    records = list(records)
    total = len(records)
    allowed = sum(1 for r in records if r.get("allowed"))
    denied = total - allowed

    by_site: Counter[str] = Counter(r.get("site_id", "unknown") for r in records)
    by_kind: Counter[str] = Counter(r.get("kind", "unknown") for r in records)
    denial_reasons: Counter[str] = Counter(
        r.get("reasons", ["unknown"])[0] if r.get("reasons") else "unknown"
        for r in records
        if not r.get("allowed")
    )
    matched_policy_counts: Counter[str] = Counter()
    for r in records:
        for p in r.get("matched_policies", []):
            matched_policy_counts[p] += 1

    return {
        "total": total,
        "allowed": allowed,
        "denied": denied,
        "allow_rate": (allowed / total) if total else 0.0,
        "by_site": dict(by_site),
        "by_kind": dict(by_kind),
        "denial_reasons": dict(denial_reasons),
        "matched_policy_counts": dict(matched_policy_counts),
    }
