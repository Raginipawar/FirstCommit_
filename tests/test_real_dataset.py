"""
Unit tests for the real SGCC dataset loader (detection/real_dataset.py).

Error-path tests don't need the actual CSV and always run. Success-path
tests need the real file and are gated behind the `real_sgcc_csv_path`
fixture (see conftest.py) -- they skip, rather than fail, when it's not
available.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from detection.real_dataset import RealDatasetError, load_real_sgcc


def test_missing_file_raises_real_dataset_error(tmp_path):
    with pytest.raises(RealDatasetError):
        load_real_sgcc(tmp_path / "does_not_exist.csv")


def test_wrong_columns_raises_real_dataset_error(tmp_path):
    bad_csv = tmp_path / "not_sgcc.csv"
    pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_csv(bad_csv, index=False)
    with pytest.raises(RealDatasetError):
        load_real_sgcc(bad_csv)


def test_site_sizes_too_large_raises(tmp_path):
    csv_path = tmp_path / "tiny_sgcc.csv"
    df = pd.DataFrame(
        {
            "1/1/2014": np.random.rand(10),
            "1/2/2014": np.random.rand(10),
            "CONS_NO": [f"c{i}" for i in range(10)],
            "FLAG": [0] * 9 + [1],
        }
    )
    df.to_csv(csv_path, index=False)
    with pytest.raises(RealDatasetError):
        load_real_sgcc(csv_path, site_sizes={"site_c_low_data": 5, "site_b": 5})


def test_fully_empty_rows_are_dropped(tmp_path):
    csv_path = tmp_path / "sgcc_with_empty_row.csv"
    df = pd.DataFrame(
        {
            "1/1/2014": [1.0, np.nan, 3.0] * 5,
            "1/2/2014": [1.0, np.nan, 3.0] * 5,
            "CONS_NO": [f"c{i}" for i in range(15)],
            "FLAG": [0] * 14 + [1],
        }
    )
    df.to_csv(csv_path, index=False)
    sites = load_real_sgcc(csv_path, site_sizes={"site_c_low_data": 4, "site_b": 4})
    total = sum(len(v) for v in sites.values())
    assert total == 10  # 15 rows minus 5 fully-NaN rows (every 2nd row here)


class TestAgainstTheRealFile:
    def test_site_sizes_match_request(self, real_sgcc_csv_path):
        sites = load_real_sgcc(real_sgcc_csv_path, site_sizes={"site_c_low_data": 600, "site_b": 14000})
        assert len(sites["site_c_low_data"]) == 600
        assert len(sites["site_b"]) == 14000
        assert len(sites["site_a"]) > 0

    def test_no_consumer_appears_in_two_sites(self, real_sgcc_csv_path):
        sites = load_real_sgcc(real_sgcc_csv_path)
        seen = set()
        for consumers in sites.values():
            ids = {c.consumer_id for c in consumers}
            assert seen.isdisjoint(ids)
            seen |= ids

    def test_is_theft_is_a_real_bool(self, real_sgcc_csv_path):
        sites = load_real_sgcc(real_sgcc_csv_path)
        for consumers in sites.values():
            assert all(isinstance(c.is_theft, bool) for c in consumers[:10])

    def test_deterministic_given_the_same_seed(self, real_sgcc_csv_path):
        sites1 = load_real_sgcc(real_sgcc_csv_path, seed=7)
        sites2 = load_real_sgcc(real_sgcc_csv_path, seed=7)
        ids1 = {c.consumer_id for c in sites1["site_c_low_data"]}
        ids2 = {c.consumer_id for c in sites2["site_c_low_data"]}
        assert ids1 == ids2

    def test_low_data_site_has_far_fewer_theft_examples(self, real_sgcc_csv_path):
        sites = load_real_sgcc(real_sgcc_csv_path)
        low_data_theft = sum(1 for c in sites["site_c_low_data"] if c.is_theft)
        site_a_theft = sum(1 for c in sites["site_a"] if c.is_theft)
        assert low_data_theft < site_a_theft / 10
