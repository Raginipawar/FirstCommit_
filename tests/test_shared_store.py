"""Unit tests for the local shared pattern store (shared_store/store.py)."""

from __future__ import annotations

from shared_store.store import LocalPatternStore


def _sig(signature_id: str, site: str) -> dict:
    return {"signature_id": signature_id, "site_of_origin": site, "kind": "signature", "granularity": 5}


def test_index_and_query_round_trip(tmp_path):
    store = LocalPatternStore(tmp_path / "pool.jsonl")
    store.index(_sig("sig-1", "site_a"))
    store.index(_sig("sig-2", "site_b"))

    records = store.query()
    assert len(records) == 2
    assert {r["signature_id"] for r in records} == {"sig-1", "sig-2"}


def test_query_excludes_one_sites_own_signatures(tmp_path):
    store = LocalPatternStore(tmp_path / "pool.jsonl")
    store.index(_sig("sig-1", "site_a"))
    store.index(_sig("sig-2", "site_b"))
    store.index(_sig("sig-3", "site_a"))

    records = store.query(exclude_site="site_a")
    assert {r["signature_id"] for r in records} == {"sig-2"}


def test_count_matches_number_indexed(tmp_path):
    store = LocalPatternStore(tmp_path / "pool.jsonl")
    assert store.count() == 0
    store.index(_sig("sig-1", "site_a"))
    store.index(_sig("sig-2", "site_a"))
    assert store.count() == 2


def test_clear_empties_the_store(tmp_path):
    store = LocalPatternStore(tmp_path / "pool.jsonl")
    store.index(_sig("sig-1", "site_a"))
    store.clear()
    assert store.count() == 0
    assert store.query() == []


def test_a_second_store_pointed_at_the_same_file_sees_the_same_data(tmp_path):
    """This is what makes it "shared" -- any process/agent pointed at the
    same path reads what any other process/agent wrote."""
    path = tmp_path / "pool.jsonl"
    writer = LocalPatternStore(path)
    writer.index(_sig("sig-1", "site_a"))

    reader = LocalPatternStore(path)
    assert reader.count() == 1
    assert reader.query()[0]["signature_id"] == "sig-1"


def test_creating_a_store_at_a_missing_path_creates_the_file(tmp_path):
    path = tmp_path / "nested" / "pool.jsonl"
    store = LocalPatternStore(path)
    assert path.exists()
    assert store.count() == 0
