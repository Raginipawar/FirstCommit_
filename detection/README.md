# Person 1 — Detection

Status: **done**. Real `IsolationForest` per site, a real measured
isolated-vs-pooled number, all tests passing.

```bash
py -3 -m pytest tests/test_dataset.py tests/test_features.py tests/test_detector.py tests/test_drift.py tests/test_baseline.py tests/test_pooled_recheck.py -v
py -3 scripts/run_isolated_vs_pooled.py     # the actual measured result
```

## What's here

| File | Purpose |
|---|---|
| `dataset.py` | Synthetic SGCC-style consumer generator, split into 3 sites with uneven volume. |
| `features.py` | Feature engineering — reuses `policy.signature.derive_shape_features` so the detector and the abstraction layer describe theft shape identically. |
| `detector.py` | `SiteDetector` — one `IsolationForest` per site, fit only on that site's own data. |
| `drift.py` | The "surprise" trigger from `Tripwire_Execution_Doc.md` 3a — decides which flagged anomalies are surprising enough to become sharing candidates. |
| `baseline.py` | Turns a flagged-consumer set into detection_rate/precision/false_positive_rate against ground truth. |
| `pooled_recheck.py` | The pooled-memory check — matches a site's unflagged consumers against shape patterns other sites have shared. |

## Why synthetic data, not the real Kaggle download

`kaggle.com/datasets/bensalem14/sgcc-dataset` needs an authenticated Kaggle
API key that isn't configured in this environment. Rather than block on
that, `dataset.py` generates data with the same shape and the same theft
vocabulary the execution doc describes (a load drop at a billing boundary,
a tamper-consistent shape, sustained or partially-recovering) — 3 sites,
uneven volume, 120 days, occasional missing readings (matching SGCC's own
known data-quality characteristics). `load_real_sgcc()` is a documented
placeholder: swapping in the real dataset later is a one-function change,
since everything downstream consumes the same `Consumer` record shape
regardless of where it came from.

## The measured result

```
site_c_low_data assumes a 2% theft rate (true rate is 7%) — it hasn't seen enough theft
historically to calibrate correctly.

  isolated (before): detection_rate=33.3% (2/6 theft caught), precision=100.0%, false_positive_rate=0.0%
  pooled   (after) : detection_rate=66.7% (4/6 theft caught), precision=100.0%, false_positive_rate=0.0%

  detection_rate moved by +33.3% on the same site, same consumers,
  purely from checking against signatures shared by two other sites --
  no retraining, no extra data collected locally.
```

Reproduce it with `py -3 scripts/run_isolated_vs_pooled.py`, or see the
pinned assertion in
`tests/test_pooled_recheck.py::TestFullPipelineOnRealSyntheticData`.

### Why `site_c_low_data` starts weak

Each `SiteConfig` (`dataset.py`) has two theft-rate numbers:
`theft_rate` (the true rate used to generate that site's data — ground
truth, unknown to the site) and `assumed_contamination` (what the site's
own `IsolationForest` is configured to expect). `site_a` and `site_b`
calibrate these correctly (0.10↔0.10, 0.08↔0.08) because they're
well-resourced. `site_c_low_data`'s true rate is 0.07 but it assumes
0.02 — it hasn't seen enough historical theft to know better, exactly
the resource-gap story in `TeamSaturn_ProjectBrief_DISCOM.pdf` section 2.
A miscalibrated `contamination` means the forest's decision boundary is
too conservative, so it misses real theft cases it would otherwise catch
— that's the weak isolated baseline, produced honestly by a realistic
mechanism, not hand-picked to make the number move.

### Why the drift filter exists

The first version of this pipeline shared *every* isolation-forest flag
verbatim. That was a mistake worth documenting: `IsolationForest`'s
`contamination` parameter forces it to flag a fixed *proportion* of
consumers as anomalous, which includes real false positives whenever a
site's own detector is imperfect (site_a and site_b's isolated baselines
above aren't 100% precision). Sharing those false positives verbatim
poisoned the pool — a false positive's signature often looks like an
ordinary consumer's mildest natural variation, and once shared, it matched
the *majority* of a peer site's honest consumers, cratering precision to
single digits in testing.

The fix is `drift.py`'s `clears_drift()`: before a locally flagged anomaly
becomes a sharing candidate, it must also clear fixed, absolute thresholds
on the actual shape (`load_drop_magnitude >= 0.30` and
`drop_duration_days >= 3`), independent of the isolation forest's relative
ranking. This is exactly the mechanism `Tripwire_Execution_Doc.md` section
3a already calls "the trigger" — it was missing from the first
implementation, not from the design. Empirically, on both well-resourced
synthetic sites, every true positive clears these thresholds and every
observed false positive does not (pinned by
`tests/test_drift.py::test_drift_filter_keeps_every_true_positive_and_drops_every_false_positive`).
A flagged anomaly that doesn't clear drift still counts toward that site's
own isolated detection number — it's excluded only from the *sharing*
path, not from local detection.

## Interface contract with Person 2 (Policy & Abstraction)

`features.to_anomaly_record(consumer, features, anomaly_score)` builds
exactly the dict `policy.signature.abstract_to_signature()` expects — see
`policy/README.md`, "Interface contract with Person 1," for the
authoritative field-by-field version. `tests/test_features.py::test_to_anomaly_record_is_actually_abstractable`
pins this: Person 2's function is called with Person 1's real output, not
a hand-shaped test fixture.

## Interface contract with Person 3 (Orchestration & Memory)

`scripts/run_isolated_vs_pooled.py` is the reference implementation of the
full loop — detect (`SiteDetector`) → drift-filter (`filter_for_sharing`)
→ abstract (`abstract_to_signature`) → policy gate (`PolicyGate`) → shared
pool (currently an in-memory list) → re-check (`recheck_against_pool`).
Person 3's job is to replace the in-memory list with a persistent
OpenSearch-backed store and each site's loop with a Strands agent — the
five function calls in between don't need to change; see
`orchestration/README.md`.
