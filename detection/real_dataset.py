"""
Loads the real SGCC Electricity Theft Detection Dataset (Zheng, Yang, Niu,
Dai, Zhou — IEEE Trans. Industrial Informatics), in place of the synthetic
stand-in in dataset.py.

Not committed to the repo: the raw CSV is ~160MB (well past what's
reasonable to check into git, and it isn't ours to redistribute anyway —
see data/README.md for the download link). Point `load_real_sgcc()` at
wherever you saved it locally.

Confirmed structure of the Kaggle download used here (`bensalem14/sgcc-
dataset`, file `data set.csv`): 42,372 consumer rows, 1,034 daily columns
(1/1/2014 through 10/31/2016) plus `CONS_NO` (an already-pseudonymised
consumer id, not a real name) and `FLAG` (1 = theft, 0 = honest).
~25.6% of cells are missing (blank), and ~13.2% of *present* cells are
recorded as exactly 0.0 — see real_features.py's docstring for why that
second number matters and how it's handled.

Site split: three sites, uneven volume, exactly as
Tripwire_Execution_Doc.md asks for — but here "low-data" means what the
problem statement actually says it means: too few of *this site's own*
labelled theft examples to train a good model. `site_c_low_data` gets only
600 of the 42,372 real consumers (about 45-50 real theft cases before any
train/test split); `site_a` and `site_b` split the rest unevenly. The
split is a fixed-seed random permutation, not a design choice pretending
some consumers are "more rural" than others -- the real theft patterns and
real labels are what they are; only *how much of the real population* each
site sees is fabricated here, which is exactly what "split into synthetic
sites" (execution doc, section 11) asks for on a real dataset.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

DEFAULT_SEED = 7
DEFAULT_SITE_SIZES = {"site_c_low_data": 600, "site_b": 14000}  # site_a gets the remainder


@dataclass(frozen=True)
class RealConsumer:
    """One real SGCC consumer, assigned to a synthetic site.

    Shares its attribute names (`consumer_id`, `is_theft`) with
    detection.dataset.Consumer on purpose -- detection/baseline.py's
    evaluate_detection() works on either without modification.
    """

    site_id: str
    consumer_id: str  # CONS_NO from the dataset -- already pseudonymised
    raw_series: np.ndarray  # length 1034, may still contain NaN/spurious zeros; see real_features.py
    is_theft: bool


class RealDatasetError(RuntimeError):
    """Raised when the real SGCC CSV can't be found or doesn't match the expected shape."""


def load_real_sgcc(
    csv_path: str | Path,
    site_sizes: dict[str, int] = DEFAULT_SITE_SIZES,
    seed: int = DEFAULT_SEED,
) -> dict[str, list[RealConsumer]]:
    """Load the real SGCC CSV and split it into three uneven-volume sites.

    :param csv_path: path to the downloaded `data set.csv` (or equivalent).
    :param site_sizes: sizes for the two smaller-named sites; whatever
        remains after those two goes to `site_a`. Keys not in
        `{"site_c_low_data", "site_b"}` are ignored.
    :param seed: fixed seed for the random permutation that assigns
        consumers to sites -- deterministic, reproducible.
    """
    path = Path(csv_path)
    if not path.exists():
        raise RealDatasetError(
            f"no file at {path}. Download it from "
            "kaggle.com/datasets/bensalem14/sgcc-dataset and pass its path here "
            "-- see data/README.md."
        )

    df = pd.read_csv(path)
    if "CONS_NO" not in df.columns or "FLAG" not in df.columns:
        raise RealDatasetError(
            f"{path} doesn't look like the SGCC dataset -- expected CONS_NO and FLAG columns, "
            f"got columns ending in {list(df.columns[-5:])}"
        )

    date_cols = [c for c in df.columns if c not in ("CONS_NO", "FLAG")]
    df = df[~df[date_cols].isna().all(axis=1)].reset_index(drop=True)  # drop fully-empty rows (5 in the source file)

    series_matrix = df[date_cols].to_numpy(dtype=float)
    consumer_ids = df["CONS_NO"].astype(str).to_numpy()
    flags = df["FLAG"].to_numpy()

    rng = np.random.default_rng(seed)
    order = rng.permutation(len(df))

    n_low_data = site_sizes.get("site_c_low_data", DEFAULT_SITE_SIZES["site_c_low_data"])
    n_b = site_sizes.get("site_b", DEFAULT_SITE_SIZES["site_b"])
    if n_low_data + n_b >= len(df):
        raise RealDatasetError(
            f"site_c_low_data ({n_low_data}) + site_b ({n_b}) must be smaller than "
            f"the dataset's {len(df)} usable rows, so site_a gets a non-empty remainder"
        )

    index_ranges = {
        "site_c_low_data": order[:n_low_data],
        "site_b": order[n_low_data : n_low_data + n_b],
        "site_a": order[n_low_data + n_b :],
    }

    sites: dict[str, list[RealConsumer]] = {}
    for site_id, idx in index_ranges.items():
        sites[site_id] = [
            RealConsumer(
                site_id=site_id,
                consumer_id=consumer_ids[i],
                raw_series=series_matrix[i],
                is_theft=bool(flags[i]),
            )
            for i in idx
        ]
    return sites
