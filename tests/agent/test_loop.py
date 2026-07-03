"""tests/agent/test_loop.py -- agent loop (spec agent-loop). Fase 6, tareas 6.5-6.6.

Usa `MockProvider` (tests/support) para simular turnos sin red. Monkeypatchea
`erickfp.agent.loop.run_tool_with_gate` para verificar que TODO `tool_use`
pasa por el gate -- nunca hay una ruta que invoque `tool.execute()`
directamente (Requirement 'Permission gate sin fuga', Scenario 'Ninguna tool
se ejecuta sin pasar por el gate').
"""

from __future__ import annotations

from erickfp.agent.loop import run_turn
from erickfp.api.types import Block, Message, Response
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
