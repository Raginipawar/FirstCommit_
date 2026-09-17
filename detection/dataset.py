"""
Synthetic stand-in for the SGCC Electricity Theft Detection Dataset (Zheng,
Yang, Niu, Dai, Zhou — IEEE Trans. Industrial Informatics), split into
synthetic sites the way Tripwire_Execution_Doc.md's Person 1 task calls for:
"Split SGCC dataset into 3-4 synthetic sites, uneven data volume."

Why synthetic and not the real Kaggle download
------------------------------------------------
Pulling the real dataset (kaggle.com/datasets/bensalem14/sgcc-dataset)
needs an authenticated Kaggle API key, which isn't configured in this
environment. Rather than block on that, this module generates data with
the same shape and the same theft-signature vocabulary the execution doc
describes (a load drop at a billing boundary, a tamper-consistent shape,
sustained or partially-recovering) so the rest of the pipeline — detector,
policy gate, pooled re-check — is fully buildable and testable now.

`load_real_sgcc()` below is a documented placeholder: once a teammate has
Kaggle credentials, implement it to read the real CSV and reshape it into
the same `Consumer` records this module already produces, and nothing
downstream (detector.py, baseline.py, pooled_recheck.py) needs to change.
Swapping the data source is a one-function change, by design.

Site layout (uneven volume, per the execution doc)
----------------------------------------------------
Three sites: two reasonably well-resourced, one deliberately low-data —
this is the site whose isolated baseline is supposed to start weak and
whose pooled number is supposed to visibly improve.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import numpy as np

DAYS = 120  # shorter than SGCC's real 1,035 days -- plenty to see a load-shape anomaly, fast to run
BILLING_CYCLE_LENGTH = 30

_HOUSEHOLD_TYPES = ("residential", "small_commercial", "agricultural")

# Theft consumers get one of these injected shapes. Names match the
# vocabulary in Tripwire_Execution_Doc.md and TeamSaturn_ProjectBrief_DISCOM.pdf.
_THEFT_PATTERNS = ("sustained_drop", "partial_recovery", "intermittent")


@dataclass(frozen=True)
class SiteConfig:
    site_id: str
    n_consumers: int
    theft_rate: float  # TRUE theft rate used to generate this site's data (ground truth)
    assumed_contamination: float  # what THIS SITE believes its theft rate is -- may be wrong
    seed: int


# Two well-resourced sites, one deliberately low-data site — the uneven
# volume the execution doc explicitly asks for.
#
# `assumed_contamination` is what each site's own IsolationForest is
# configured to expect, as opposed to `theft_rate`, the true rate used to
# generate the data. A well-resourced site has enough historical theft
# cases to calibrate this correctly. site_c_low_data does not: "it doesn't
# see enough theft cases on their own to learn what it looks like"
# (Tripwire_Execution_Doc.md, Problem Statement) -- here, concretely, that
# means it badly under-estimates its own theft rate, so its detector's
# decision boundary is set too conservatively and it starts out catching
# theft badly. This is the isolated baseline the execution doc calls "the
# weak number, before sharing."
SITE_CONFIGS: tuple[SiteConfig, ...] = (
    SiteConfig(site_id="site_a", n_consumers=600, theft_rate=0.10, assumed_contamination=0.10, seed=1),
    SiteConfig(site_id="site_b", n_consumers=450, theft_rate=0.08, assumed_contamination=0.08, seed=2),
    SiteConfig(site_id="site_c_low_data", n_consumers=90, theft_rate=0.07, assumed_contamination=0.02, seed=3),
)


@dataclass
class Consumer:
    """One synthetic SGCC-style consumer record for one site."""

    site_id: str
    consumer_id: str
    meter_id: str
    household_type: str
    lat: float
    lon: float
    billing_cycle_day: int
    series: np.ndarray  # length DAYS, daily consumption, may contain NaN
    is_theft: bool
    theft_pattern: str | None = field(default=None)
    theft_start_day: int | None = field(default=None)


def _inject_theft_pattern(series: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, str, int]:
    """Overwrite part of a clean series with a tamper-consistent shape."""
    series = series.copy()
    baseline = float(np.median(series[:30]))
    pattern = rng.choice(_THEFT_PATTERNS)
    start = int(rng.integers(25, DAYS - 20))
    drop_fraction = rng.uniform(0.35, 0.75)  # fraction of baseline retained
    dropped_level = baseline * (1.0 - drop_fraction)

    if pattern == "sustained_drop":
        # Load drops and never recovers -- classic meter tamper.
        series[start:] = dropped_level + rng.normal(0, baseline * 0.03, size=DAYS - start)

    elif pattern == "partial_recovery":
        # Drops sharply, then creeps back toward (but not to) baseline --
        # someone easing consumption back up while still under-declaring.
        duration = int(rng.integers(15, 35))
        end = min(DAYS, start + duration)
        series[start:end] = dropped_level + rng.normal(0, baseline * 0.03, size=end - start)
        if end < DAYS:
            recovery_target = baseline * rng.uniform(0.7, 0.9)
            ramp = np.linspace(dropped_level, recovery_target, DAYS - end)
            series[end:] = ramp + rng.normal(0, baseline * 0.03, size=DAYS - end)

    else:  # intermittent
        # Drops, fully recovers, drops again -- tampering only some of the time.
        duration = int(rng.integers(10, 20))
        end = min(DAYS, start + duration)
        series[start:end] = dropped_level + rng.normal(0, baseline * 0.03, size=end - start)
        second_start = end + int(rng.integers(5, 15))
        if second_start < DAYS:
            second_end = min(DAYS, second_start + duration)
            series[second_start:second_end] = dropped_level + rng.normal(
                0, baseline * 0.03, size=second_end - second_start
            )

    series = np.clip(series, 0.0, None)
    return series, pattern, start


def _generate_clean_series(rng: np.random.Generator) -> np.ndarray:
    """A normal (non-theft) consumer: stable baseline, weekly seasonality, noise."""
    baseline = rng.lognormal(mean=np.log(12.0), sigma=0.5)  # kWh/day, right-skewed like real usage
    day_idx = np.arange(DAYS)
    weekly = 1.0 + 0.08 * np.sin(2 * np.pi * day_idx / 7.0)
    seasonal_drift = 1.0 + 0.05 * np.sin(2 * np.pi * day_idx / DAYS)
    noise = rng.normal(1.0, 0.06, size=DAYS)
    series = baseline * weekly * seasonal_drift * noise
    return np.clip(series, 0.0, None)


def _apply_missing_data(series: np.ndarray, rng: np.random.Generator, rate: float = 0.015) -> np.ndarray:
    """Real smart-meter feeds drop occasional readings; SGCC has this too."""
    series = series.copy()
    missing_mask = rng.random(DAYS) < rate
    series[missing_mask] = np.nan
    return series


def generate_site(config: SiteConfig) -> list[Consumer]:
    """Generate one synthetic site's consumers, matching `config`."""
    rng = np.random.default_rng(config.seed)
    n_theft = max(1, round(config.n_consumers * config.theft_rate))
    theft_flags = np.array([True] * n_theft + [False] * (config.n_consumers - n_theft))
    rng.shuffle(theft_flags)

    consumers: list[Consumer] = []
    for i in range(config.n_consumers):
        series = _generate_clean_series(rng)
        is_theft = bool(theft_flags[i])
        pattern = None
        start = None
        if is_theft:
            series, pattern, start = _inject_theft_pattern(series, rng)
        series = _apply_missing_data(series, rng)

        consumers.append(
            Consumer(
                site_id=config.site_id,
                consumer_id=f"{config.site_id}-CUST-{i:05d}",
                meter_id=f"{config.site_id}-MTR-{i:05d}",
                household_type=str(rng.choice(_HOUSEHOLD_TYPES, p=[0.7, 0.2, 0.1])),
                lat=float(rng.uniform(8.0, 28.0)),  # roughly India's latitude span
                lon=float(rng.uniform(72.0, 88.0)),
                billing_cycle_day=int(rng.integers(1, BILLING_CYCLE_LENGTH + 1)),
                series=series,
                is_theft=is_theft,
                theft_pattern=pattern,
                theft_start_day=start,
            )
        )
    return consumers


def generate_all_sites(configs: tuple[SiteConfig, ...] = SITE_CONFIGS) -> dict[str, list[Consumer]]:
    return {c.site_id: generate_site(c) for c in configs}


def load_real_sgcc(csv_path: str | Path) -> dict[str, list[Consumer]]:
    """Placeholder for the real dataset.

    Once a teammate has Kaggle credentials for
    kaggle.com/datasets/bensalem14/sgcc-dataset, implement this to read the
    real CSV (consumer x day matrix + FLAG theft column) and reshape each
    row into a `Consumer`, then split into SITE_CONFIGS-shaped groups
    (uneven volume, one deliberately small "low-data" site) the same way
    `generate_all_sites` does. Everything downstream — detector.py,
    baseline.py, pooled_recheck.py — consumes `dict[str, list[Consumer]]`
    and does not care whether it came from here or from the synthetic
    generator above.
    """
    raise NotImplementedError(
        "real SGCC loading needs a Kaggle-authenticated CSV download; "
        "use generate_all_sites() until that's available"
    )


def save_site_csv(consumers: list[Consumer], out_path: str | Path) -> None:
    """Persist one site's consumers as a long-format CSV under data/sites/."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "site_id", "consumer_id", "meter_id", "household_type", "lat", "lon",
                "billing_cycle_day", "is_theft", "theft_pattern", "theft_start_day", "day", "consumption",
            ]
        )
        for c in consumers:
            for day, value in enumerate(c.series):
                writer.writerow(
                    [
                        c.site_id, c.consumer_id, c.meter_id, c.household_type, c.lat, c.lon,
                        c.billing_cycle_day, int(c.is_theft), c.theft_pattern or "", c.theft_start_day or "",
                        day, "" if np.isnan(value) else value,
                    ]
                )


def save_all_sites(sites: dict[str, list[Consumer]], out_dir: str | Path) -> None:
    out_dir = Path(out_dir)
    for site_id, consumers in sites.items():
        save_site_csv(consumers, out_dir / f"{site_id}.csv")


def iter_theft_consumers(consumers: list[Consumer]) -> Iterator[Consumer]:
    return (c for c in consumers if c.is_theft)
