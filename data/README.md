# Data (Person 1)

Status: **synthetic data generated on demand, real dataset not yet
downloaded.** `../detection/dataset.py` generates a documented synthetic
stand-in (see `../detection/README.md`, "Why synthetic data, not the real
Kaggle download") — nothing needs to be checked into this folder for the
current pipeline to run.

Real source: SGCC Electricity Theft Detection Dataset (Zheng, Yang, Niu,
Dai, Zhou, IEEE Trans. Industrial Informatics) — 42,372 consumers, 1,035
days, theft-labelled. `kaggle.com/datasets/bensalem14/sgcc-dataset`
(needs an authenticated Kaggle API key, not configured in this
environment).

## To persist the current synthetic sites as CSVs

```python
from detection.dataset import generate_all_sites, save_all_sites
save_all_sites(generate_all_sites(), "data/sites")
```

Produces the long-format layout below (one row per consumer-day). Raw
files are gitignored (see `../.gitignore`) since even the synthetic
version regenerates deterministically from the fixed seeds in
`detection/dataset.py::SITE_CONFIGS` — there's nothing to lose by not
committing it.

## To switch to the real dataset later

Implement `detection.dataset.load_real_sgcc(csv_path)` to read the real
Kaggle CSV and reshape each row into a `Consumer` (see that function's
docstring for the exact shape), then split into `SITE_CONFIGS`-like groups
with uneven volume. Everything downstream — `detector.py`, `baseline.py`,
`pooled_recheck.py`, and Person 2's `abstract_to_signature()` — consumes
`dict[str, list[Consumer]]` and does not care which loader produced it.

```
data/
  raw/                  # gitignored — downloaded SGCC CSV(s), once available
  sites/
    site_a.csv
    site_b.csv
    site_c_low_data.csv # the deliberately weak site
```
