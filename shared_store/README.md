# Shared pattern store (Person 3)

Status: **`LocalPatternStore` done and tested; `OpenSearchPatternStore`
written but unverified against a live cluster** (Docker's daemon isn't
running in this environment — see `../orchestration/README.md`).

From `Tripwire_Execution_Doc.md`: "Permitted signatures land in a shared
OpenSearch store that every site can check against without retraining
anything — the pooled knowledge grows, the models don't move."

## What's here

`store.py` defines one `PatternStore` interface (`index()`, `query()`,
`count()`) with two implementations:

- **`LocalPatternStore`** — a JSON-lines file. This is what
  `scripts/run_isolated_vs_pooled.py` and every test actually run against
  today. Zero setup, fully deterministic.
- **`OpenSearchPatternStore`** — a real client against `opensearch-py`
  (`indices.create`/`.index`/`.search`/`.count`, with an index mapping
  matching `Signature.to_dict()`'s fields). Correct against the real API,
  but never connected to an actual cluster here.

`SiteAgent` (`../orchestration/agent.py`) and
`detection.pooled_recheck.build_pattern_index` don't know or care which
one they're talking to — both classes expose the same three methods, so
switching is a one-line change (see `../orchestration/README.md`,
"The two remaining gaps").

## What lands here

Only signatures that already passed Person 2's Cedar gate
(`decision.allowed is True`) are ever indexed — `SiteAgent.share_round()`
enforces this; neither store implementation re-checks it. Index
`signature.to_dict()` — the full descriptive record (bucketed shape
features, `signature_id`, `site_of_origin`), not just the seven
Cedar-facing fields from `signature.to_payload_attrs()`.

Because `abstract_to_signature()` already guarantees `has_meter_id`,
`has_consumer_id`, `has_raw_series`, `has_household_field`, and
`has_location` are all `False` for anything that made it past the gate,
nothing in this store needs a second privacy check on read — the gate is
the only enforcement point, by design (see `../policy/README.md`,
"Design notes").

## To switch to a live OpenSearch cluster

Once Docker (or a real cluster) is reachable:

```python
from shared_store.store import OpenSearchPatternStore

store = OpenSearchPatternStore(hosts=[{"host": "localhost", "port": 9200}])
```

in place of `LocalPatternStore(...)` wherever a store is constructed
(currently only `scripts/run_isolated_vs_pooled.py`). Run the existing
test suite (`tests/test_orchestration.py`, `tests/test_shared_store.py`)
against it to confirm the live cluster behaves the same way the local one
does before relying on it for the demo.
