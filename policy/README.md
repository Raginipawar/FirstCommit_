# Person 2 — Policy & Abstraction

Status: **done**, working against the real Cedar engine (`cedarpy`), all
tests passing, runnable demo. This is the boundary the whole pitch depends
on: raw detector output can never leave a site, only abstracted signatures
can, and that boundary is enforced by Cedar, not by a promise.

## What's here

| File | Purpose |
|---|---|
| `signature.py` | Abstraction layer: raw anomaly → signature vector. Strips every identifying field, buckets continuous features, computes a `granularity` score. |
| `policies/sharing.cedarschema` | The Cedar entity/action schema (`Site`, `Payload`, action `"share"`). |
| `policies/sharing.cedar` | The two Cedar rules: unconditional `forbid` on identifying fields, `permit` for clean signatures under the granularity threshold. |
| `gate.py` | `PolicyGate` — loads the policy+schema once, evaluates one share request at a time via the real Cedar engine, logs every decision. |
| `decision_log.py` | Append-only JSONL decision log + query/summarize helpers. Never stores raw identifier values, only the coarse flags Cedar saw. |
| `__init__.py` | Public re-exports — see below. |

Runnable from `tripwire/`:

```bash
py -3 -m pip install -r requirements.txt
py -3 -m pytest tests/ -v                    # 45 tests, all against the real Cedar engine
py -3 scripts/demo_block_then_pass.py        # the on-screen block -> pass proof
py -3 scripts/inspect_log.py                 # read back everything that was logged
```

## Why Cedar sees so little

Cedar is only ever handed seven fields per payload — `kind` and five
`has_*` booleans and a `granularity` integer. It never sees a load-shape
value, a bucket label, or anything else descriptive. That's deliberate:
the entire point of the abstraction layer is that the *content* of a
signature is a Python-side concern, and the *boundary* — may this thing
leave the site at all — is a Cedar-side concern, checkable independently
of whatever the signature format grows into later.

```
Site::"site_c_low_data" --share--> Payload {
    kind: "signature" | "raw_record",
    has_meter_id, has_consumer_id, has_raw_series,
    has_household_field, has_location: Bool,
    granularity: Long,
}
```

Two rules, in `sharing.cedar`:

1. **`forbid`** — any `has_*` flag true is an unconditional deny. In Cedar,
   `forbid` always wins over `permit` regardless of rule order or what gets
   added later, so this can't be quietly weakened by a future looser rule.
2. **`permit`** — `kind == "signature"` and `granularity <= 10`. This is
   what actually lets a clean signature through, and it also catches
   payloads that have no *named* identifier left but are still too
   fine-grained (e.g. an unbucketed raw anomaly score) — the granularity
   check is a second, independent safety net, not a duplicate of rule 1.

If you change the `10` in `sharing.cedar`, also change
`GRANULARITY_THRESHOLD` in `signature.py` —
`tests/test_policy_gate.py::test_threshold_matches_code` fails loudly if
the two drift apart.

## Interface contract with Person 1 (Detection)

Person 1's detector should hand each flagged anomaly to
`policy.signature.abstract_to_signature()` as a plain dict shaped like:

```python
{
    "site_id": "site_c_low_data",       # required
    "meter_id": "MTR-04821",             # identifying, will be stripped
    "consumer_id": "CUST-99231",         # identifying, will be stripped
    "household_type": "residential",     # identifying, will be stripped
    "location": {"lat": 12.97, "lon": 77.59},  # identifying, will be stripped
    "billing_cycle_day": 12,             # 1-31, used to bucket timing
    "detected_at": "2026-09-18T03:00:00Z",
    "anomaly_score": 0.91,               # 0..1 detector confidence

    # EITHER a raw load-shape series (>= 6 points, shape features derived
    # automatically: baseline = mean of the first third of the series)...
    "raw_series": [101, 99, 103, ..., 30],

    # ...OR, if Person 1's detector already computes shape features
    # directly, skip raw_series and pass these four instead:
    "load_drop_magnitude": 0.63,   # fraction drop from baseline, 0..1
    "drop_duration_days": 4,
    "recovery_time_days": 12,
    "volatility": 0.22,            # coefficient of variation of the series
}
```

Only `site_id` plus one of the two shape-feature options is required —
everything else has a sane default. `abstract_to_signature()` raises
`policy.signature.AbstractionError` if neither is present, so a malformed
detector output fails fast and visibly rather than silently producing a
meaningless signature.

If Person 1's isolation-forest/classifier output doesn't map cleanly onto
`load_drop_magnitude` / `drop_duration_days` / `recovery_time_days` /
`volatility`, that's a five-minute conversation, not a redesign — those four
names are the only coupling point between the two components.

## Interface contract with Person 3 (Orchestration & Memory)

Person 3's per-site Strands agent loop should look like:

```python
from policy import PolicyGate, abstract_to_signature

gate = PolicyGate()  # loads sharing.cedar + sharing.cedarschema once, reuse this instance

def on_anomaly_detected(anomaly: dict) -> None:
    signature = abstract_to_signature(anomaly)
    decision = gate.evaluate_share_request(anomaly["site_id"], signature)

    if decision.allowed:
        shared_store.index(signature.to_dict())   # Person 3: push to OpenSearch
    else:
        # already logged to policy/logs/decisions.jsonl — nothing further
        # to do here except maybe surface decision.reasons[0] on screen
        pass
```

Notes for wiring this into the detect → abstract → request-to-share →
receive → re-check loop:

- **One `PolicyGate` instance per process**, not one per request — it
  parses the Cedar policy/schema on construction, and re-parsing per call
  is wasted work Cedar itself warns against (`cedarpy` accepts pre-parsed
  `PolicySet`/`Schema` handles for exactly this reason).
- `gate.evaluate_share_request(site_id, signature)` **always** logs,
  whether it returns allow or deny — Person 3 doesn't need a separate
  logging step, and shouldn't add one (it would double-log).
- `decision.allowed` is the only thing that should gate whether a
  signature reaches the shared store. Don't re-derive that decision from
  `signature.has_meter_id` etc. in orchestration code — Cedar is the
  single source of truth for "can this leave the site," on purpose.
- The **receive → re-check** half of the loop (a site pulling signatures
  *out* of the shared store to check new consumption against) does not go
  through this gate. The gate only guards the write path — pooled
  signatures are already sanitized by construction once they're in the
  store.
- `PolicyDecision.to_dict()` / `str(decision)` are both safe to print or
  ship to whatever the demo's console output layer ends up being — neither
  ever contains a raw identifier value.

## Interface contract with the shared store (OpenSearch, Person 3)

Only `signature.to_dict()` (never `to_payload_attrs()`, which is the
minimal Cedar-facing subset) should be indexed once `decision.allowed` is
`True`. `to_dict()` includes `signature_id` and `site_of_origin` so the
pooled store can be queried per-site or de-duplicated, plus the descriptive
bucketed fields Person 1/3 need to actually compare new anomalies against
what's been pooled.

## Design notes / things a mentor or judge might ask

**"Why forbid *and* permit instead of just one permit rule?"** Cedar's
default is implicit deny, so a bare `permit` rule alone would already
reject raw records. The explicit `forbid` exists so the deny is
*unconditional and rule-ordering-proof* — someone adding a broader `permit`
later (e.g. "permit everything from a trusted site") cannot accidentally
open the identifier leak back up, because `forbid` always wins in Cedar.

**"What does granularity actually measure?"** It's not a duplicate of the
identifier checks. Every bucketed/categorical field in a signature
(`load_drop_magnitude_bucket`, `timing_bucket`, `recovery_shape`, etc.)
costs a flat 1 point. Any field that indicates something raw or
unbucketed leaked through — including non-identifying ones, like a raw
`anomaly_score` float instead of `anomaly_score_bucket` — costs a heavy
fixed penalty (25) that blows past the threshold (10) on its own. A
correctly abstracted signature typically scores 5-6; a leaky one scores
30+. See `tests/test_signature.py::TestComputeGranularity` and
`abstract_to_signature_leaky`'s docstring for exactly how this is computed.

**"Is the decision log itself safe to share?"** Yes by construction — it
only ever contains what Cedar saw (`kind`, five booleans, an integer,
plus site/resource ids and timestamps), never the raw anomaly. See
`tests/test_policy_gate.py::test_denial_log_never_contains_the_raw_identifier_value`.

**"What's explicitly out of scope here?"** Differential privacy on the
signatures themselves (Part V of the project brief calls this out as
medium-term future work, not this weekend's scope), and any policy
decision on the *read* path (receive → re-check) — only the *write* path
(request-to-share) is gated.
