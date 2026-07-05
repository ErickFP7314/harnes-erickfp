"""tests/agent/test_loop.py -- agent loop (spec agent-loop). Fase 6, tareas 6.5-6.6.

Usa `MockProvider` (tests/support) para simular turnos sin red. Monkeypatchea
`erickfp.agent.loop.run_tool_with_gate` para verificar que TODO `tool_use`
pasa por el gate -- nunca hay una ruta que invoque `tool.execute()`
directamente (Requirement 'Permission gate sin fuga', Scenario 'Ninguna tool
se ejecuta sin pasar por el gate').
"""

from __future__ import annotations

from erickfp.agent.loop import run_turn
from erickfp.agent.tokens import TokenTracker
from erickfp.api.types import Block, Message, Response, Usage
from erickfp.tools.registry import ToolRegistry
from tests.support import FakeTool, MockProvider


def test_no_tool_use_skips_gate(monkeypatch) -> None:
    """Scenario 'Turno sin tool use': texto puro no invoca el gate."""
    gate_calls: list[str] = []
    monkeypatch.setattr(
        "erickfp.agent.loop.run_tool_with_gate",
        lambda tool, tool_use: gate_calls.append(tool_use.tool_use_id) or Block(
            type="tool_result"
        ),
    )
    provider = MockProvider(
        responses=[Response(content=[Block(type="text", text="hola")], stop_reason="end_turn")]
    )
    messages = [Message(role="user", content=[Block(type="text", text="hola")])]

    result = run_turn(provider, ToolRegistry(), messages, [])

    assert gate_calls == []
    assert result[-1].role == "assistant"
    assert result[-1].content[0].text == "hola"


def test_every_tool_use_passes_through_gate_no_direct_path(monkeypatch) -> None:
    """Scenario 'Turno con una o mas tool calls': cada tool_use pasa por el
    gate, nunca por una ruta directa a `execute()`."""
    tool = FakeTool(name="alpha")
    tools = ToolRegistry()
    tools.register(tool)

    gate_calls: list[str] = []

    def fake_gate(tool_: object, tool_use: Block) -> Block:
        gate_calls.append(tool_use.tool_use_id)
        return Block(
            type="tool_result", tool_use_id=tool_use.tool_use_id, tool_result="ok", is_error=False
        )

    monkeypatch.setattr("erickfp.agent.loop.run_tool_with_gate", fake_gate)

    first_response = Response(
        content=[
            Block(type="tool_use", tool_use_id="call-1", tool_name="alpha", tool_input="{}"),
            Block(type="tool_use", tool_use_id="call-2", tool_name="alpha", tool_input="{}"),
        ],
        stop_reason="tool_use",
    )
    second_response = Response(content=[Block(type="text", text="listo")], stop_reason="end_turn")
    provider = MockProvider(responses=[first_response, second_response])
    messages = [Message(role="user", content=[Block(type="text", text="hazlo")])]

    result = run_turn(provider, tools, messages, tools.definitions())

    assert gate_calls == ["call-1", "call-2"]
    assert tool.executed_with == []  # jamas se llamo execute() por fuera del gate
    assert result[-1].content[0].text == "listo"
    assert len(provider.sent_messages) == 2  # 2 turnos: tool_use -> tool_result -> end_turn


def test_unknown_tool_returns_is_error_result_without_raising(monkeypatch) -> None:
    """Lote 2, tarea 2.7 (SUGGESTION-1/3 del verify-report de ciclo 1): un
    `tool_use` cuyo nombre NO esta en el `ToolRegistry` no lanza una
    excepcion nativa -- produce un `tool_result` con `is_error=True` y un
    mensaje claro que nombra la tool desconocida, y el loop continua hasta
    el siguiente `stop_reason != "tool_use"` (nunca por una ruta que invoque
    `run_tool_with_gate`/`execute()` para esa tool)."""
    gate_calls: list[str] = []
    monkeypatch.setattr(
        "erickfp.agent.loop.run_tool_with_gate",
        lambda tool, tool_use: gate_calls.append(tool_use.tool_use_id) or Block(
            type="tool_result"
        ),
    )

    first_response = Response(
        content=[
            Block(
                type="tool_use",
                tool_use_id="call-1",
                tool_name="tool_que_no_existe",
                tool_input="{}",
            )
        ],
        stop_reason="tool_use",
    )
    second_response = Response(content=[Block(type="text", text="listo")], stop_reason="end_turn")
    provider = MockProvider(responses=[first_response, second_response])
    messages = [Message(role="user", content=[Block(type="text", text="hazlo")])]

    result = run_turn(provider, ToolRegistry(), messages, [])

    assert gate_calls == []  # jamas llego al gate: no existe en el registry
    tool_result = result[-2].content[0]
    assert tool_result.type == "tool_result"
    assert tool_result.tool_use_id == "call-1"
    assert tool_result.is_error is True
    assert "tool_que_no_existe" in tool_result.tool_result
    assert result[-1].content[0].text == "listo"  # el loop continua sin crashear


def test_run_turn_reports_usage_to_tracker_each_turn(monkeypatch) -> None:
    """Lote 3, tarea 3.15 (design.md Decision 6): cada respuesta del
    Provider dentro del turno reporta su `usage` al `TokenTracker` inyectado
    -- un turno con una tool call intermedia reporta 2 veces (una por cada
    llamada real a `provider.send`), acumulando ambas."""
    monkeypatch.setattr(
        "erickfp.agent.loop.run_tool_with_gate",
        lambda tool, tool_use: Block(
            type="tool_result", tool_use_id=tool_use.tool_use_id, tool_result="ok"
        ),
    )
    tracker = TokenTracker()
    first_response = Response(
        content=[
            Block(type="tool_use", tool_use_id="call-1", tool_name="alpha", tool_input="{}")
        ],
        stop_reason="tool_use",
        usage=Usage(prompt=10, completion=2, total=12),
    )
    second_response = Response(
        content=[Block(type="text", text="listo")],
        stop_reason="end_turn",
        usage=Usage(prompt=15, completion=3, total=18),
    )
    tool = FakeTool(name="alpha")
    tools = ToolRegistry()
    tools.register(tool)
    provider = MockProvider(responses=[first_response, second_response])
    messages = [Message(role="user", content=[Block(type="text", text="hazlo")])]

    run_turn(provider, tools, messages, tools.definitions(), tracker=tracker)

    assert tracker.prompt_tokens == 25
    assert tracker.completion_tokens == 5
    assert tracker.total_tokens == 30


def test_run_turn_without_tracker_keeps_previous_behavior() -> None:
    """Retrocompatibilidad: `tracker=None` (default) no cambia el
    comportamiento previo -- ninguna prueba existente deberia romperse."""
    provider = MockProvider(
        responses=[Response(content=[Block(type="text", text="hola")], stop_reason="end_turn")]
    )
    messages = [Message(role="user", content=[Block(type="text", text="hola")])]

    result = run_turn(provider, ToolRegistry(), messages, [])

    assert result[-1].content[0].text == "hola"
