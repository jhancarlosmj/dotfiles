"""The indexer can index a wiki page (WIKI job), reusing the one embedder."""

from __future__ import annotations

from pathlib import Path

from src.indexer import Indexer
from src.queue_db import JobQueue


def test_indexer_processes_wiki_page(fake_store, tmp_path: Path, monkeypatch) -> None:
    wiki_root = tmp_path / "wiki"
    (wiki_root / "personal" / "sessions").mkdir(parents=True)
    page = wiki_root / "personal" / "sessions" / "2026-06-07-note.md"
    page.write_text(
        "---\ntitle: Test note\ntype: session\nsession_id: abc\n---\n\n"
        "## Summary\n\nwork on the caching eviction path\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_WIKI_ROOT", str(wiki_root))

    idx = Indexer(store=fake_store, queue=JobQueue(db_path=tmp_path / "q.db"))
    idx._process_wiki_page(page)

    # The page's chunks are now in the wiki collection and the keyword index.
    assert fake_store.collection("wiki").count() >= 1
    assert fake_store._fts.search("caching")


def test_indexer_skips_wiki_page_outside_root(fake_store, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RAG_WIKI_ROOT", str(tmp_path / "wiki"))
    stray = tmp_path / "elsewhere" / "note.md"
    stray.parent.mkdir(parents=True)
    stray.write_text("---\ntitle: X\n---\n\n## S\n\ntext\n", encoding="utf-8")

    idx = Indexer(store=fake_store, queue=JobQueue(db_path=tmp_path / "q.db"))
    idx._process_wiki_page(stray)  # must not raise

    assert fake_store.collection("wiki").count() == 0


def _page(wiki_root: Path, sections: list[tuple[str, str]]) -> Path:
    page = wiki_root / "sessions" / "m" / "2026-09-18-old.md"
    page.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(f"## {h}\n\n{t}\n\n" for h, t in sections)
    page.write_text(f"---\ntitle: Old\nsession_id: abc\n---\n\n{body}", encoding="utf-8")
    return page


def test_deleted_wiki_page_leaves_both_index_legs(fake_store, tmp_path: Path, monkeypatch) -> None:
    wiki_root = tmp_path / "wiki"
    monkeypatch.setenv("RAG_WIKI_ROOT", str(wiki_root))
    page = _page(wiki_root, [("Summary", "zebrafish migration notes")])
    idx = Indexer(store=fake_store, queue=JobQueue(db_path=tmp_path / "q.db"))
    idx._process_wiki_page(page)
    assert fake_store._fts.search("zebrafish")

    page.unlink()
    idx._process_wiki_page(page)  # a job for a page that is gone must not raise

    assert fake_store.collection("wiki").count() == 0
    assert not fake_store._fts.search("zebrafish")


def test_shrunk_wiki_page_drops_its_old_tail_chunks(fake_store, tmp_path: Path, monkeypatch) -> None:
    wiki_root = tmp_path / "wiki"
    monkeypatch.setenv("RAG_WIKI_ROOT", str(wiki_root))
    idx = Indexer(store=fake_store, queue=JobQueue(db_path=tmp_path / "q.db"))
    page = _page(wiki_root, [("One", "alpha"), ("Two", "beta"), ("Three", "quokka tail")])
    idx._process_wiki_page(page)
    before = fake_store.collection("wiki").count()

    _page(wiki_root, [("One", "alpha")])
    idx._process_wiki_page(page)

    assert fake_store.collection("wiki").count() < before
    assert not fake_store._fts.search("quokka")


def test_store_delete_also_clears_the_keyword_row(fake_store) -> None:
    fake_store.upsert_batch("wiki", ["p.md#0"], ["wombat facts"], [{"file_path": "/w/p.md"}])
    assert fake_store._fts.search("wombat")
    fake_store.delete("wiki", "p.md#0")
    assert not fake_store._fts.search("wombat")
    assert fake_store.delete_file("wiki", "/w/p.md") == 0
