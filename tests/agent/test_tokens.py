"""tests/agent/test_tokens.py -- TokenTracker (spec token-viewer, Lote 3
harness-v0-2, tarea 3.14, design.md Decision 6).

`TokenTracker` acumula tokens de entrada/salida/total a traves de turnos
sucesivos de una misma sesion -- el comando `/tokens` (cli.py) lee su estado
en cualquier momento sin depender del Provider concreto.
"""

from __future__ import annotations

from erickfp.agent.tokens import TokenTracker
from erickfp.api.types import Usage


def test_tracker_starts_at_zero() -> None:
    tracker = TokenTracker()

    assert tracker.prompt_tokens == 0
    assert tracker.completion_tokens == 0
    assert tracker.total_tokens == 0


def test_tracker_accumulates_usage_across_turns() -> None:
    """Lote 3, tarea 3.14: dos llamadas a `add()` con `Usage` distintos
    suman -- no reemplazan -- el estado acumulado de la sesion."""
    tracker = TokenTracker()

    tracker.add(Usage(prompt=10, completion=5, total=15))
    tracker.add(Usage(prompt=20, completion=8, total=28))

    assert tracker.prompt_tokens == 30
    assert tracker.completion_tokens == 13
    assert tracker.total_tokens == 43


def test_tracker_add_ignores_none_usage_without_error() -> None:
    """Un turno de solo texto (sin `tool_use`) puede no traer `usage` desde
    el adapter (ver test_response_usage_is_none_when_raw_has_no_usage) --
    `add(None)` no debe lanzar ni alterar el acumulado."""
    tracker = TokenTracker()
    tracker.add(Usage(prompt=1, completion=1, total=2))

    tracker.add(None)

    assert tracker.prompt_tokens == 1
    assert tracker.completion_tokens == 1
    assert tracker.total_tokens == 2
