"""tests/agent/test_loop_hooks.py -- integracion de hooks en el agent loop
(Fase 8: `run_turn` se EXTIENDE, no se reescribe -- ver docstring de
`agent/loop.py` de la Fase 6). Cubre el riesgo alto de la propuesta: un
`deny` de un hook `PreToolUse` (p.ej. `core_guard`) bloquea la tool ANTES de
que el permission gate sea siquiera consultado, y el comportamiento previo
(sin hooks) sigue intacto cuando no se inyecta `hook_manager`/`ctx`
(retrocompatibilidad con las pruebas de la Fase 6).
"""

from __future__ import annotations

from erickfp.agent.loop import run_turn
from erickfp.api.types import Block, HookResult, Message, Response
from erickfp.hooks.manager import HookManager, PhaseContext
from erickfp.tools.registry import ToolRegistry
from tests.support import FakeTool, MockProvider


def test_hook_deny_blocks_tool_before_gate_is_consulted(monkeypatch) -> None:
    """Un hook `PreToolUse` que deniega bloquea la tool SIN pasar por el
    gate: `run_tool_with_gate` (y por lo tanto `input()`) nunca se llama."""
    gate_calls: list[str] = []
    monkeypatch.setattr(
        "erickfp.agent.agent.run_tool_with_gate",
        lambda tool, tool_use: gate_calls.append(tool_use.tool_use_id) or Block(
            type="tool_result", is_error=False
        ),
    )

    tool = FakeTool(name="write_file")
    tools = ToolRegistry()
    tools.register(tool)

    class DenyEverythingHook:
        event = "PreToolUse"

        def run(self, ctx: PhaseContext) -> HookResult:
            return HookResult(decision="deny", reason="core_guard: bloqueado")

    hook_manager = HookManager([DenyEverythingHook()])
    ctx = PhaseContext(phase="ordena")

    first_response = Response(
        content=[
            Block(type="tool_use", tool_use_id="call-1", tool_name="write_file", tool_input="{}")
        ],
        stop_reason="tool_use",
    )
    second_response = Response(content=[Block(type="text", text="listo")], stop_reason="end_turn")
    provider = MockProvider(responses=[first_response, second_response])
    messages = [Message(role="user", content=[Block(type="text", text="hazlo")])]

    result = run_turn(
        provider, tools, messages, tools.definitions(), hook_manager=hook_manager, ctx=ctx
    )

    assert gate_calls == []  # el gate NUNCA se consulto
    assert tool.executed_with == []  # la tool real jamas se ejecuto
    last_user_message = result[-2]  # el turno "user" con el tool_result
    assert last_user_message.content[0].is_error is True
    assert "core_guard" in last_user_message.content[0].tool_result


def test_hook_allow_lets_tool_reach_the_gate(monkeypatch) -> None:
    """Un hook `PreToolUse` que aprueba deja que la tool siga su camino
    normal hacia el gate."""
    gate_calls: list[str] = []
    monkeypatch.setattr(
        "erickfp.agent.agent.run_tool_with_gate",
        lambda tool, tool_use: gate_calls.append(tool_use.tool_use_id) or Block(
            type="tool_result", tool_use_id=tool_use.tool_use_id, tool_result="ok", is_error=False
        ),
    )

    tool = FakeTool(name="read_file")
    tools = ToolRegistry()
    tools.register(tool)

    class AllowEverythingHook:
        event = "PreToolUse"

        def run(self, ctx: PhaseContext) -> HookResult:
            return HookResult(decision="allow")

    hook_manager = HookManager([AllowEverythingHook()])
    ctx = PhaseContext(phase="ordena")

    first_response = Response(
        content=[
            Block(type="tool_use", tool_use_id="call-1", tool_name="read_file", tool_input="{}")
        ],
        stop_reason="tool_use",
    )
    second_response = Response(content=[Block(type="text", text="listo")], stop_reason="end_turn")
    provider = MockProvider(responses=[first_response, second_response])
    messages = [Message(role="user", content=[Block(type="text", text="hazlo")])]

    run_turn(
        provider, tools, messages, tools.definitions(), hook_manager=hook_manager, ctx=ctx
    )

    assert gate_calls == ["call-1"]


def test_run_turn_without_hook_manager_keeps_previous_behavior() -> None:
    """Retrocompatibilidad: sin `hook_manager`/`ctx` (default `None`), el
    comportamiento es identico al de la Fase 6 -- ninguna prueba existente
    de `test_loop.py` deberia romperse por esta extension."""
    provider = MockProvider(
        responses=[Response(content=[Block(type="text", text="hola")], stop_reason="end_turn")]
    )
    messages = [Message(role="user", content=[Block(type="text", text="hola")])]

    result = run_turn(provider, ToolRegistry(), messages, [])

    assert result[-1].content[0].text == "hola"
