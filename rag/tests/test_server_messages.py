"""Tests for what the MCP tools tell the agent when something is empty or broken.

Every empty or failed result has to say what to try next, because the agent
has nothing else to go on.
"""

from __future__ import annotations

import pytest

from src import server
from src.store import EmbeddingModelMismatch


class _Raises:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def search(self, *a, **k):
        raise self.exc

    def get_documents(self, ids):
        raise self.exc


class _Empty:
    def search(self, *a, **k):
        return []

    def get_documents(self, ids):
        return []


class _Some:
    def get_documents(self, ids):
        return [{"id": "a", "document": "alpha", "metadata": {}}]


@pytest.fixture
def use_store(monkeypatch):
    def _set(store):
        monkeypatch.setattr(server, "_store", store)
    return _set


def test_no_results_suggests_next_steps(use_store) -> None:
    use_store(_Empty())
    for out in (server.search("x"), server.get_context("x")):
        assert out == server.NO_RESULTS
        assert "/recall" in out


def test_backend_failure_names_the_error_and_the_fix(use_store) -> None:
    use_store(_Raises(ConnectionError("connection refused")))
    out = server.search("x")
    assert "ConnectionError: connection refused" in out
    assert "ollama list" in out
    assert "indexer.err" in server.get_context("x")


def test_model_mismatch_reaches_the_agent_instead_of_raising(monkeypatch) -> None:
    monkeypatch.setattr(server, "_store", None)

    def _boom():
        raise EmbeddingModelMismatch("Embedding model is b, but collection 'wiki' was embedded with a.")

    monkeypatch.setattr(server, "Store", _boom)
    for out in (server.search("x"), server.get_context("x"), server.get_chunks(["a"])):
        assert "'wiki' was embedded with a" in out


def test_get_chunks_reports_stale_ids(use_store) -> None:
    use_store(_Empty())
    assert "Run search again" in server.get_chunks(["gone"])

    use_store(_Some())
    out = server.get_chunks(["a", "gone1", "gone2"])
    assert "alpha" in out
    assert "2 id(s) no longer exist" in out and "gone1" in out


def test_get_chunks_without_ids_shows_the_call_shape() -> None:
    assert "get_chunks([" in server.get_chunks([])


@pytest.mark.parametrize("since, expected", [
    ("24h", 1_000_000 - 24 * 3600),
    ("7d", 1_000_000 - 7 * 86400),
    (" 2D ", 1_000_000 - 2 * 86400),
    ("999999", 999_999.0),
    ("yesterday", None),
    ("0h", None),
    ("-3d", None),
    ("2000000", None),  # in the future
])
def test_parse_since(since, expected) -> None:
    assert server.parse_since(since, now=1_000_000) == expected


def test_unreadable_since_is_an_error_not_a_silent_unfiltered_list(monkeypatch) -> None:
    class _Audit:
        def get_entries(self, since=None, limit=20):
            raise AssertionError("must not query with an ignored filter")

    monkeypatch.setattr(server, "_audit", _Audit())
    out = server.get_audit_log(since="yesterday")
    assert "Could not read since='yesterday'" in out
    assert '"24h"' in out
