"""compaction/base.py -- `Protocol CompactionStrategy` + `NoCompaction`
(Lote 6 harness-v0-2, tareas 6.1-6.2, design.md Decision 5: "Interfaz
Protocol CompactionStrategy.compact(messages) -> messages (capa
compaction)").

Ubicado entre `erickfp.agent` y `erickfp.hooks|tools|provider|memory|ui` en
el contrato de capas (`pyproject.toml`): esta capa depende solo de `api`
(Decision 1), nunca de `agent` ni `provider` -- `SlidingWindow` cablea con
`safe_split.py` (misma capa) y `Summarize` (`summarize.py`) es la unica
implementacion que necesita `provider.base.Provider`, importado ahi mismo,
no aqui.

`NoCompaction` es el default bit-a-bit (mismo axioma que `AlwaysAsk`/
`max_attempts=2`): un turno sin `compaction` inyectado en `run_turn` (o con
`NoCompaction()` explicito) se comporta identico al ciclo 1 -- nunca trunca
ni copia el historial.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from erickfp.api.types import Message


@runtime_checkable
class CompactionStrategy(Protocol):
    """Estructura minima que toda estrategia de compactacion debe satisfacer
    (Decision 5: duck typing puro, sin herencia)."""

    def compact(self, messages: list[Message]) -> list[Message]: ...


class NoCompaction:
    """Identidad pura -- default bit-a-bit (spec compaction, comportamiento
    implicito de 'sin compactacion configurada')."""

    def compact(self, messages: list[Message]) -> list[Message]:
        return messages
