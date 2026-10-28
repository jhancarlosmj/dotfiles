"""Tests for the embedding-model pin: a store never mixes vectors from two models."""

from __future__ import annotations

import json

import pytest

from conftest import FakeEmbed
from src.store import EmbeddingModelMismatch, Store


class OtherEmbed(FakeEmbed):
    """Same dimensions as FakeEmbed, different model: the silent-failure case."""

    def name(self) -> str:
        return "other-embed"


def _pins(tmp_path) -> dict:
    return json.loads((tmp_path / "chroma.embedding-pin.json").read_text())


def _store(tmp_path, embed) -> Store:
    return Store(db_path=tmp_path / "chroma", embedding_fn=embed)


def test_new_store_pins_every_collection(tmp_path) -> None:
    _store(tmp_path, FakeEmbed())
    assert _pins(tmp_path) == {"conversations": "fake-embed", "wiki": "fake-embed"}


def test_reopening_with_the_same_model_is_fine(tmp_path) -> None:
    store = _store(tmp_path, FakeEmbed())
    store.collection("wiki").add(ids=["w1"], documents=["alpha"])
    reopened = _store(tmp_path, FakeEmbed())
    assert reopened.collection("wiki").count() == 1


def test_switching_model_on_a_filled_collection_refuses_to_open(tmp_path) -> None:
    store = _store(tmp_path, FakeEmbed())
    store.collection("wiki").add(ids=["w1"], documents=["alpha"])

    with pytest.raises(EmbeddingModelMismatch) as exc:
        _store(tmp_path, OtherEmbed())
    message = str(exc.value)
    assert "'wiki' was embedded with fake-embed" in message
    assert "other-embed" in message
    assert "conversations" not in message  # empty, so it is simply re-pinned
    assert _pins(tmp_path)["wiki"] == "fake-embed"  # a refused open writes nothing


def test_switching_model_on_empty_collections_re_pins(tmp_path) -> None:
    _store(tmp_path, FakeEmbed())
    _store(tmp_path, OtherEmbed())
    assert _pins(tmp_path) == {"conversations": "other-embed", "wiki": "other-embed"}


def test_unpinned_existing_store_adopts_current_model(tmp_path) -> None:
    store = _store(tmp_path, FakeEmbed())
    store.collection("conversations").add(ids=["c1"], documents=["alpha"])
    (tmp_path / "chroma.embedding-pin.json").unlink()  # a store from before pinning

    _store(tmp_path, FakeEmbed())
    assert _pins(tmp_path)["conversations"] == "fake-embed"


def test_clear_collection_re_pins_it_to_the_new_model(tmp_path) -> None:
    store = _store(tmp_path, FakeEmbed())
    for name in ("wiki", "conversations"):
        store.collection(name).add(ids=[f"{name}1"], documents=["alpha"])

    with pytest.raises(EmbeddingModelMismatch):
        _store(tmp_path, OtherEmbed())

    # Reindex path: clear with the old store, then the new model may fill it.
    store._embed_fn = OtherEmbed()
    store._model_id = "other-embed"
    store.clear_collection("wiki")
    assert _pins(tmp_path) == {"conversations": "fake-embed", "wiki": "other-embed"}
