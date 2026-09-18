"""
The shared pattern store: where permitted signatures land once Person 2's
Cedar gate allows them, and where every site reads from during its
pooled-memory re-check.

Two implementations behind one `PatternStore` interface, so
`orchestration/agent.py` and `detection/pooled_recheck.py` never need to
know or care which one is in use:

- `LocalPatternStore` — a JSON-lines file. Zero setup, deterministic,
  fully tested. This is what the rest of the repo actually runs against
  today.
- `OpenSearchPatternStore` — a real client against the real `opensearch-py`
  library, matching Tripwire_Execution_Doc.md's "stand up OpenSearch as
  the shared pattern store." Implemented against the genuine API, but
  **not exercised against a live cluster in this environment** — and this
  was actually attempted, not skipped: Docker Desktop's daemon here fails
  to start because this Windows install is itself running inside a
  hypervisor with no nested virtualization exposed to it (`wsl --status`
  reports "ensure virtualization is enabled in the BIOS", and `systeminfo`
  confirms a hypervisor is already present) — a host-level constraint, not
  a missing `docker desktop start`. See `../orchestration/README.md`,
  "Gap 2," for the full account. Swap it in the moment a cluster is
  reachable (LocalStack, a real OpenSearch container, or an AWS-hosted
  domain, on a host where that's actually possible); no other file needs
  to change, since both classes satisfy the same three methods.

Only ever index signatures that already cleared `PolicyGate.evaluate_share_request`
(`decision.allowed is True`) — neither implementation re-checks that, by
design (see policy/README.md, "Design notes": Cedar is the single
enforcement point, on purpose).
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class PatternStore(ABC):
    """The three operations every site's loop needs from the shared store."""

    @abstractmethod
    def index(self, signature: dict[str, Any]) -> None:
        """Add one already-permitted signature to the pool."""

    @abstractmethod
    def query(self, *, exclude_site: str | None = None) -> list[dict[str, Any]]:
        """Every signature in the pool, optionally excluding one site's own."""

    @abstractmethod
    def count(self) -> int:
        """How many signatures are currently pooled."""


class LocalPatternStore(PatternStore):
    """A JSON-lines file standing in for OpenSearch.

    Deliberately dumb: no indexing, no query language, just "read every
    line back in." That's fine at this scale (a few hundred signatures)
    and means the rest of the pipeline can be developed and tested without
    Docker, a cluster, or network access.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def index(self, signature: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(signature, ensure_ascii=False) + "\n")

    def query(self, *, exclude_site: str | None = None) -> list[dict[str, Any]]:
        records = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if exclude_site is not None and record.get("site_of_origin") == exclude_site:
                    continue
                records.append(record)
        return records

    def count(self) -> int:
        return len(self.query())

    def clear(self) -> None:
        """Truncate the store. Used by tests and to reset between demo runs."""
        self.path.write_text("", encoding="utf-8")


_DEFAULT_INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "signature_id": {"type": "keyword"},
            "site_of_origin": {"type": "keyword"},
            "kind": {"type": "keyword"},
            "generated_at": {"type": "date"},
            "load_drop_magnitude_bucket": {"type": "integer"},
            "drop_duration_bucket": {"type": "integer"},
            "timing_bucket": {"type": "keyword"},
            "recovery_shape": {"type": "keyword"},
            "volatility_bucket": {"type": "integer"},
            "anomaly_score_bucket": {"type": "integer"},
            "granularity": {"type": "integer"},
            "has_meter_id": {"type": "boolean"},
            "has_consumer_id": {"type": "boolean"},
            "has_raw_series": {"type": "boolean"},
            "has_household_field": {"type": "boolean"},
            "has_location": {"type": "boolean"},
        }
    }
}


class OpenSearchPatternStore(PatternStore):
    """Real OpenSearch-backed store.

    Untested against a live cluster in this environment -- see this
    module's docstring. Point it at LocalStack, a local `opensearch`
    container, or a real cluster once one is reachable:

        store = OpenSearchPatternStore(hosts=[{"host": "localhost", "port": 9200}])

    Everything else in the pipeline (`orchestration/agent.py`,
    `detection/pooled_recheck.py`) calls only `index()`, `query()`, and
    `count()`, so it works unmodified against either this or
    `LocalPatternStore`.
    """

    def __init__(
        self,
        hosts: list[dict[str, Any]] | None = None,
        index_name: str = "tripwire-signatures",
        **client_kwargs: Any,
    ) -> None:
        from opensearchpy import OpenSearch  # imported lazily -- optional dependency path

        self.index_name = index_name
        self.client = OpenSearch(hosts=hosts or [{"host": "localhost", "port": 9200}], **client_kwargs)
        if not self.client.indices.exists(index=self.index_name):
            self.client.indices.create(index=self.index_name, body=_DEFAULT_INDEX_MAPPING)

    def index(self, signature: dict[str, Any]) -> None:
        self.client.index(
            index=self.index_name,
            id=signature["signature_id"],
            body=signature,
            refresh=True,  # small pool, correctness over throughput
        )

    def query(self, *, exclude_site: str | None = None) -> list[dict[str, Any]]:
        if exclude_site is None:
            body = {"query": {"match_all": {}}}
        else:
            body = {"query": {"bool": {"must_not": [{"term": {"site_of_origin": exclude_site}}]}}}
        response = self.client.search(index=self.index_name, body=body, size=10_000)
        return [hit["_source"] for hit in response["hits"]["hits"]]

    def count(self) -> int:
        return int(self.client.count(index=self.index_name)["count"])
