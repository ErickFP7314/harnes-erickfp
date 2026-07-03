"""memory/store.py -- Protocol Store (Decision 5 y 6 del design; spec
memory-store, Requirement 'Interfaz Store con impl SQLite').

`@runtime_checkable` para permitir validacion estructural con `isinstance()`
donde haga falta, igual que `Provider`/`Tool`/`Hook` (Decision 5).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from erickfp.api.types import Entry


@runtime_checkable
class Store(Protocol):
    def save(self, entry: Entry) -> None: ...

    def recall(self, query: str, limit: int) -> list[Entry]: ...

    def preamble(self) -> str: ...
