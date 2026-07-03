"""tests/memory/test_store.py -- Protocol Store (Fase 9, tarea 9.1). Spec
memory-store, Requirement 'Interfaz Store con impl SQLite'.
"""

from __future__ import annotations

from erickfp.api.types import Entry
from erickfp.memory.store import Store


class FakeStore:
    """Store de prueba minima: satisface el Protocol `Store` sin heredar."""

    def __init__(self) -> None:
        self.saved: list[Entry] = []

    def save(self, entry: Entry) -> None:
        self.saved.append(entry)

    def recall(self, query: str, limit: int) -> list[Entry]:
        return [entry for entry in self.saved if query in entry.content][:limit]

    def preamble(self) -> str:
        return "preamble de prueba"


def test_fake_store_satisfies_store_protocol() -> None:
    store: Store = FakeStore()
    assert isinstance(store, Store)

    entry = Entry(kind="fact", content="dato de prueba")
    store.save(entry)

    assert store.recall("prueba", limit=10) == [entry]
    assert store.preamble() == "preamble de prueba"
