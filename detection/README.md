# Person 1 — Detection

Status: **done, two parallel paths.** The synthetic path below (real
`IsolationForest` per site) shipped first; a real-data path
(`real_*.py`) now also exists, validated against the actual downloaded
SGCC CSV — see "The real-data path" below for why it's a separate set of
modules rather than a drop-in replacement.

```bash
py -3 -m pytest tests/test_dataset.py tests/test_features.py tests/test_detector.py tests/test_drift.py tests/test_baseline.py tests/test_pooled_recheck.py -v
py -3 scripts/run_isolated_vs_pooled.py     # the synthetic-path measured result

# real-data path (needs the CSV downloaded locally -- see data/README.md):
set TRIPWIRE_SGCC_CSV=C:\path\to\data set.csv
py -3 -m pytest tests/test_real_features.py tests/test_real_detector.py tests/test_real_dataset.py tests/test_real_pipeline.py -v
py -3 scripts/run_real_sgcc_pipeline.py "C:\path\to\data set.csv"
```

## What's here

| File | Purpose |
|---|---|
| `dataset.py` | Synthetic SGCC-style consumer generator, split into 3 sites with uneven volume. |
| `features.py` | Feature engineering — reuses `policy.signature.derive_shape_features` so the detector and the abstraction layer describe theft shape identically. |
| `detector.py` | `SiteDetector` — one `IsolationForest` per site, fit only on that site's own data. |
| `drift.py` | The "surprise" trigger from `Tripwire_Execution_Doc.md` 3a — decides which flagged anomalies are surprising enough to become sharing candidates. |
| `baseline.py` | Turns a flagged-consumer set into detection_rate/precision/false_positive_rate against ground truth. Shared by both paths. |
| `pooled_recheck.py` | The synthetic path's pooled-memory check. |
| `real_dataset.py` | Loads the real SGCC CSV, splits into 3 uneven-volume sites. |
| `real_features.py` | Real-data feature engineering — handles two things the synthetic path doesn't need to: spurious zero-readings and a ~1,034-day timescale. |
| `real_detector.py` | `SupervisedSiteDetector` — a per-site `RandomForestClassifier`, trained on that site's own labelled history only. |
| `real_pipeline.py` | Ties the real-data path together: detect → confidence+drift filter → Cedar gate → pool → re-check. |

## The real-data path

### Why it's separate from the synthetic path, not a replacement

Two things about the real dataset broke assumptions the synthetic path
safely made:

1. **Unsupervised detection barely works on it.** `detector.py`'s
   `IsolationForest` approach, evaluated against the real data during
   development, scored barely above chance (best trade-off found: ~59%
   recall at a ~44% false-positive rate) — full time-series and
   noise-corrected variants were tried too, with no better result. This
   isn't a tuning miss: this exact dataset is documented in the literature
   as needing more than simple anomaly detection (the original Zheng et
   al. paper builds a Wide & Deep CNN specifically because naive methods
   don't separate well here). `real_detector.py` uses a **supervised**
   `RandomForestClassifier` instead — the execution doc explicitly allows
   "isolation forest / lightweight classifier," and a classifier trained
   on real labels reaches a real, literature-consistent AUC of ~0.76.
2. **The 120-day vs. 1,034-day timescale mismatch.** `policy/signature.py`'s
   bucket edges for `drop_duration_days` (2/5/10) are tuned for a 120-day
   synthetic series; against a 1,034-day real series, almost everything
   would land in the top bucket. `real_features.py` has its own edges,
   re-tuned for the real timescale (see its docstring).

Despite both differences, the real path still reuses Person 2's actual
`Signature` dataclass, `compute_granularity`, and `PolicyGate` completely
unmodified (`real_pipeline.py::_signature_from_real_shape` constructs a
`Signature` directly with real-data-scaled bucket values) — Cedar's rules
only ever check `kind`, the five `has_*` flags, and `granularity`, none of
which depend on which detector or which bucket edges produced the value.

### Why the real dataset needed its own zero-handling

~13.2% of all real readings are recorded as exactly `0.0`, and — this is
the finding that mattered — **honest customers have a *higher* raw
zero-rate (13.7%) than theft customers (8.3%)**. These are meter/recording
glitches, not signal; a naive "trough = minimum reading" (safe on
synthetic data, which has no such glitches) gets swamped by them.
`real_features.py::declutter_zeros()` treats short zero-runs (≤2 days) as
missing data and fills them; a longer run is left alone, since a
sustained real zero (a bypassed or disconnected meter) is exactly the
pattern worth keeping.

### The measured result (real data)

```
site_a: trained on 1651 labelled theft cases -> detection_rate=57.2%, precision=19.6%
site_b: trained on  837 labelled theft cases -> detection_rate=54.5%, precision=18.2%
site_c_low_data: trained on only 41 labelled theft cases -> detection_rate=35.3%, precision=26.1%

shared pool holds 527 signatures (from site_a, site_b; 0 denied by Cedar)

site_c_low_data isolated (before): detection_rate=35.3% (6/17 theft caught)
site_c_low_data pooled   (after) : detection_rate=64.7% (11/17 theft caught)
+29.4 points, on real, held-out SGCC test consumers
```

Reproduce with `py -3 scripts/run_real_sgcc_pipeline.py "<path to data set.csv>"`,
or see the pinned assertions in `tests/test_real_pipeline.py`.

**Honest difference from the synthetic result, stated plainly:** the
synthetic path's pooled improvement costs nothing (precision and
false-positive-rate stay identical). The real-data result has a genuine
precision trade-off (precision drops from 26.1% to 20.4%, false-positive
rate rises from 10.4% to 26.4%) — real, noisy data doesn't offer a free
lunch, and the four-field shape-key match (magnitude/duration/volatility/
recovery-shape) plus a same-site-confidence guard
(`RECHECK_BORDERLINE_THRESHOLD = 0.2` — only re-check a consumer the
site's own model was *already at least a little suspicious of*) is what
keeps that cost from being much worse: an earlier version without that
confidence guard flagged the large majority of the low-data site's honest
test consumers. This trade-off is worth stating to judges directly rather
than hidden — it's the more credible number of the two, precisely because
it isn't free.

### Why the site split uses a different "low-data" mechanism than the synthetic path

The synthetic path's low-data story comes from `assumed_contamination`
being deliberately miscalibrated (see below). The real path doesn't need
that trick: `site_c_low_data` gets only 600 of the 42,372 real consumers
(fixed seed, `real_dataset.py::DEFAULT_SEED = 7`), which naturally means
only ~41 real labelled theft examples to train on — literally too few to
train as good a classifier as a site with 1,651. This is the plainest
possible version of the problem statement: "they don't see enough theft
cases on their own to learn what it looks like."

### Performance note

`real_features.py::declutter_zeros` was originally implemented with a
pandas `groupby` per consumer -- correct, but ~90 seconds end to end
against all ~42,000 real consumers, too slow for a judge to click through
live. It's now pure vectorized numpy (same behavior, pinned by the same
test suite) -- see that function's docstring.

## Why synthetic data was tried first (before the real dataset was available)

`kaggle.com/datasets/bensalem14/sgcc-dataset` needs an authenticated
Kaggle API key that wasn't configured in this environment initially.
Rather than block on that, `dataset.py` generates data with the same
shape and the same theft vocabulary the execution doc describes — 3
sites, uneven volume, 120 days, occasional missing readings. Once the
real dataset was downloaded, both paths were kept: the synthetic one
remains fast, deterministic, and a clean pedagogical story; the real one
is slower but is the actual published dataset with a genuine, honestly
disclosed precision trade-off.

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
