"""A clean reindex must clear the keyword rows for that collection only."""
from src.fts import FtsIndex


def _index(tmp_path):
    fts = FtsIndex(tmp_path / "fts.db")
    fts.upsert_many([
        ("w1", "wiki", "alpha wiki text", {"file_path": "/a.md"}),
        ("w2", "wiki", "beta wiki text", {"file_path": "/b.md"}),
        ("c1", "conversations", "gamma conversation text", {"session_id": "s"}),
    ])
    return fts


def test_clear_collection_removes_only_that_collection(tmp_path):
    fts = _index(tmp_path)
    assert fts.count() == 3

    removed = fts.clear_collection("wiki")

    assert removed == 2
    assert fts.count() == 1
    assert not fts.search("alpha", collections=["wiki"])
    assert fts.search("gamma", collections=["conversations"])


def test_clear_collection_is_idempotent(tmp_path):
    fts = _index(tmp_path)
    fts.clear_collection("wiki")
    assert fts.clear_collection("wiki") == 0
    assert fts.count() == 1
