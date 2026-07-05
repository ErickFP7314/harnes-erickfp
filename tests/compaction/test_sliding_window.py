"""tests/compaction/test_sliding_window.py -- `SlidingWindow` (Lote 6
harness-v0-2, tareas 6.3-6.4, design.md Decision 5, specs/compaction/spec.md
Scenario 'Historial excede el umbral configurado').

`SlidingWindow(max_messages)` descarta turnos antiguos cuando el historial
supera `max_messages`, conservando la cola mas reciente -- SIEMPRE a traves
de `safe_split_point` (nunca corta a ciegas), para no partir jamas un par
`tool_use`/`tool_result` (Riesgo transversal (c), cubierto formalmente en
`test_safe_split_point.py`).
"""

from __future__ import annotations

from erickfp.api.types import Block, Message
from erickfp.compaction.sliding_window import SlidingWindow


def _text(role: str, text: str) -> Message:
    return Message(role=role, content=[Block(type="text", text=text)])  # type: ignore[arg-type]


def test_history_exceeding_threshold_shrinks_keeping_recent_turns() -> None:
    """Scenario 'Historial excede el umbral configurado': GIVEN un
    historial de 10 mensajes con `max_messages=4`, WHEN se aplica
    `SlidingWindow`, THEN el resultado es mas corto que el original y
    conserva exactamente los 4 turnos mas recientes, en el mismo orden."""
    messages = [_text("user" if i % 2 == 0 else "assistant", f"turno {i}") for i in range(10)]

    strategy = SlidingWindow(max_messages=4)
    result = strategy.compact(messages)

    assert len(result) < len(messages)
    assert result == messages[-4:]


def test_history_under_threshold_is_returned_unchanged() -> None:
    """Triangulacion: si el historial NO supera `max_messages`, el
    resultado es identico (no se activa ningun recorte)."""
    messages = [_text("user", "hola"), _text("assistant", "hola, en que ayudo?")]

    strategy = SlidingWindow(max_messages=10)
    result = strategy.compact(messages)

    assert result is messages


def test_sliding_window_never_splits_a_pending_tool_pair() -> None:
    """Integracion con `SafeSplitPoint` (Riesgo transversal (c)): si el
    umbral cae justo dentro de un par `tool_use`/`tool_result`, el corte se
    ajusta hacia atras para conservar el par completo -- el resultado puede
    ser MAS largo que `max_messages`, nunca deja un `tool_result` huerfano."""
    messages = [
        _text("user", "raiz"),
        Message(
            role="assistant",
            content=[
                Block(type="tool_use", tool_use_id="call-1", tool_name="bash", tool_input="{}")
            ],
        ),
        Message(
            role="user",
            content=[Block(type="tool_result", tool_use_id="call-1", tool_result="ok")],
        ),
        _text("assistant", "listo"),
    ]

    # max_messages=2 apunta el corte deseado exactamente al mensaje "user
    # tool_result" (indice 2), dejando su "assistant tool_use" (indice 1)
    # fuera -- SafeSplitPoint debe ajustar hacia atras para mantener el par.
    strategy = SlidingWindow(max_messages=2)
    result = strategy.compact(messages)

    tool_use_ids = {
        block.tool_use_id
        for message in result
        for block in message.content
        if block.type == "tool_use"
    }
    tool_result_ids = {
        block.tool_use_id
        for message in result
        for block in message.content
        if block.type == "tool_result"
    }
    assert tool_use_ids == tool_result_ids  # ningun huerfano en ninguna direccion
    assert "call-1" in tool_use_ids
