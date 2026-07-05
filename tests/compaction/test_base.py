"""tests/compaction/test_base.py -- CompactionStrategy Protocol + NoCompaction
(Lote 6 harness-v0-2, tareas 6.1-6.2, design.md Decision 5, specs/compaction/
spec.md Requirement 'CompactionStrategy con sliding window y summarize').

`NoCompaction` es el default bit-a-bit (design.md: "Todo comportamiento nuevo
es opt-in con default bit-a-bit equivalente al ciclo 1... NoCompaction"): debe
comportarse como identidad pura, sin siquiera copiar la lista, para que
inyectarlo (o no inyectar nada, `compaction=None` en `run_turn`) sea
indistinguible para el resto del sistema.
"""

from __future__ import annotations

from erickfp.api.types import Block, Message
from erickfp.compaction.base import CompactionStrategy, NoCompaction


def test_no_compaction_is_identity_default() -> None:
    """Scenario implicito de NoCompaction (default bit-a-bit): dado un
    historial cualquiera, `NoCompaction().compact(messages)` retorna
    exactamente el mismo objeto -- ni lo trunca ni lo copia."""
    messages = [
        Message(role="user", content=[Block(type="text", text="hola")]),
        Message(role="assistant", content=[Block(type="text", text="hola, en que ayudo?")]),
    ]

    strategy: CompactionStrategy = NoCompaction()
    result = strategy.compact(messages)

    assert result is messages  # identidad real, no una copia estructuralmente igual
    assert result == messages


def test_no_compaction_satisfies_compaction_strategy_protocol_structurally() -> None:
    """`NoCompaction` no hereda de `CompactionStrategy` -- lo satisface
    estructuralmente (Decision 5: todo Protocol nuevo es duck-typing puro,
    mismo patron que `Provider`/`Tool`/`PermissionPolicy`)."""
    assert isinstance(NoCompaction(), CompactionStrategy)
