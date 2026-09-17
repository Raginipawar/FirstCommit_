"""Unit tests for the synthetic SGCC-style dataset generator (detection/dataset.py)."""

from __future__ import annotations

import numpy as np

from detection.dataset import DAYS, SITE_CONFIGS, generate_all_sites, generate_site


def test_site_configs_have_uneven_volume():
    sizes = [c.n_consumers for c in SITE_CONFIGS]
    assert len(set(sizes)) == len(sizes), "site sizes should differ (uneven volume)"
    assert min(sizes) < max(sizes) / 2, "at least one site should be clearly low-data"


def test_low_data_site_is_the_smallest():
    low_data = next(c for c in SITE_CONFIGS if c.site_id == "site_c_low_data")
    assert low_data.n_consumers == min(c.n_consumers for c in SITE_CONFIGS)


def test_generate_site_produces_requested_consumer_count():
    config = SITE_CONFIGS[0]
    consumers = generate_site(config)
    assert len(consumers) == config.n_consumers


def test_generate_site_matches_requested_theft_rate_closely():
    config = SITE_CONFIGS[0]
    consumers = generate_site(config)
    actual_theft = sum(1 for c in consumers if c.is_theft) / len(consumers)
    assert abs(actual_theft - config.theft_rate) < 0.02


def test_generate_site_is_deterministic_given_a_seed():
    config = SITE_CONFIGS[0]
    a = generate_site(config)
    b = generate_site(config)
    assert [c.is_theft for c in a] == [c.is_theft for c in b]
    assert np.allclose(a[0].series, b[0].series, equal_nan=True)


def test_series_length_matches_days_constant():
    consumers = generate_site(SITE_CONFIGS[0])
    for c in consumers[:5]:
        assert len(c.series) == DAYS


def test_theft_consumers_have_a_pattern_and_start_day():
    consumers = generate_site(SITE_CONFIGS[0])
    for c in consumers:
        if c.is_theft:
            assert c.theft_pattern in ("sustained_drop", "partial_recovery", "intermittent")
            assert c.theft_start_day is not None
        else:
            assert c.theft_pattern is None
            assert c.theft_start_day is None


def test_theft_consumers_actually_show_a_load_drop():
    """Sanity check that injected theft isn't a no-op: baseline should exceed
    the post-injection trough by a meaningful margin."""
    consumers = generate_site(SITE_CONFIGS[0])
    theft_consumers = [c for c in consumers if c.is_theft]
    assert theft_consumers
    for c in theft_consumers[:10]:
        series = c.series[~np.isnan(c.series)]
        baseline = np.median(series[:30])
        trough = np.min(series)
        assert trough < baseline * 0.8, f"{c.consumer_id} theft pattern did not produce a visible drop"


def test_some_readings_are_missing():
    consumers = generate_site(SITE_CONFIGS[0])
    total_missing = sum(int(np.isnan(c.series).sum()) for c in consumers)
    assert total_missing > 0, "expected some missing readings, matching real SGCC data characteristics"


def test_generate_all_sites_returns_every_configured_site():
    sites = generate_all_sites()
    assert set(sites.keys()) == {c.site_id for c in SITE_CONFIGS}
    for config in SITE_CONFIGS:
        assert len(sites[config.site_id]) == config.n_consumers


def test_consumer_and_meter_ids_are_unique_within_a_site():
    consumers = generate_site(SITE_CONFIGS[0])
    assert len({c.consumer_id for c in consumers}) == len(consumers)
    assert len({c.meter_id for c in consumers}) == len(consumers)
