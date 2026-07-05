"""tests/subagents/test_research.py -- subagente `Research` (Lote 7
harness-v0-2, tareas 7.3, 7.5, 7.6, design.md Decision 7 / spec subagents).
"""

from __future__ import annotations

import json
from pathlib import Path

from erickfp.api.types import Block, Message, Response
from erickfp.hooks.core_guard import CoreGuardHook
from erickfp.hooks.manager import HookManager
from erickfp.subagents.research import Research
from tests.support import MockProvider


def test_research_registry_contains_only_read_only_tools() -> None:
    """Scenario 'Research solo tiene tools de lectura': el registry local
    del subagente contiene UNICAMENTE `read_file` -- `write_file` (y
    `bash`) no estan registradas."""
    research = Research(provider=MockProvider())

    names = {tool.definition().name for tool in research.registry.all_tools()}

    assert names == {"read_file"}
    assert "write_file" not in names
    assert "bash" not in names
    assert research.registry.get("write_file") is None
    assert research.registry.get("bash") is None


def test_research_cannot_write_unknown_tool_no_execution() -> None:
    """TRANSVERSAL (d), spec subagents Scenario 'Research no puede
    escribir': el modelo dentro del subagente intenta invocar `write_file`;
    como esa tool no existe en su registry, la invocacion falla como tool
    desconocida (sin excepcion) y NINGUNA escritura real ocurre -- no hay
    siquiera una `WriteFileTool` instanciada para ejecutar."""
    write_attempt = Response(
        content=[
            Block(
                type="tool_use",
                tool_use_id="call-1",
                tool_name="write_file",
                tool_input=json.dumps({"path": "hackeado.txt", "content": "malicioso"}),
            )
        ],
        stop_reason="tool_use",
    )
    final = Response(
        content=[Block(type="text", text="no pude escribir eso")], stop_reason="end_turn"
    )
    provider = MockProvider(responses=[write_attempt, final])
    research = Research(provider=provider)

    answer = research.run("intenta escribir un archivo")

    assert answer == "no pude escribir eso"
    # El "turno" que sigue al intento de escritura es el tool_result que
    # prueba que la tool fue tratada como desconocida (nunca ejecutada).
    tool_result_message = provider.sent_messages[1][-1]
    tool_result = tool_result_message.content[0]
    assert tool_result.type == "tool_result"
    assert tool_result.is_error is True
    assert "write_file" in tool_result.tool_result
    assert "desconocida" in tool_result.tool_result


def test_core_guard_active_inside_subagent(tmp_path: Path) -> None:
    """Scenario 'core_guard bloquea escritura en core incluso dentro del
    subagente': aunque `read_file` SI esta en el registry de `Research` y
    su policy (`AllowList`) la auto-aprueba, el `core_guard` (`PreToolUse`)
    inyectado sigue evaluandose y bloquea un intento de leer un archivo
    dentro de `.ErickFP/core/*` -- el bloqueo no depende de que la policy
    del subagente ya la tuviera auto-aprobada."""
    root = tmp_path / ".ErickFP"
    (root / "core").mkdir(parents=True)
    core_file = root / "core" / "Claude"
    core_file.write_text("axiomas del proyecto")

    hook_manager = HookManager([CoreGuardHook(root)])
    read_core_attempt = Response(
        content=[
            Block(
                type="tool_use",
                tool_use_id="call-1",
                tool_name="read_file",
                tool_input=json.dumps({"path": str(core_file)}),
            )
        ],
        stop_reason="tool_use",
    )
    final = Response(
        content=[Block(type="text", text="bloqueado por core_guard")], stop_reason="end_turn"
    )
    provider = MockProvider(responses=[read_core_attempt, final])
    research = Research(provider=provider, hook_manager=hook_manager)

    answer = research.run("lee .ErickFP/core/Claude")

    assert answer == "bloqueado por core_guard"
    tool_result = provider.sent_messages[1][-1].content[0]
    assert tool_result.type == "tool_result"
    assert tool_result.is_error is True
    assert "core" in tool_result.tool_result


def test_research_run_returns_final_text_synthesis() -> None:
    """Camino feliz: `Research.run` retorna el texto final del subagente
    tras leer un archivo real via `read_file` (sin mockear el gate: la
    policy `AllowList` auto-aprueba, no hay `input()` involucrado)."""
    target = Response(
        content=[
            Block(
                type="tool_use",
                tool_use_id="call-1",
                tool_name="read_file",
                tool_input=json.dumps({"path": "cualquier/ruta.txt"}),
            )
        ],
        stop_reason="tool_use",
    )
    final = Response(content=[Block(type="text", text="sintesis final")], stop_reason="end_turn")
    provider = MockProvider(responses=[target, final])
    research = Research(provider=provider)

    answer = research.run("investiga algo")

    assert answer == "sintesis final"


def test_research_bounds_turns_with_max_turns() -> None:
    """El subagente Research nunca itera indefinidamente: `max_turns`
    (mismo patron que `MaxTurns=10` de la guia byo-coding-agent) acota el
    turno incluso si el Provider siguiera pidiendo tools eternamente."""

    class _InfiniteToolUseProvider:
        def __init__(self) -> None:
            self.calls = 0

        def send(self, messages: list[Message], tools: object) -> Response:
            self.calls += 1
            return Response(
                content=[
                    Block(
                        type="tool_use",
                        tool_use_id=f"call-{self.calls}",
                        tool_name="read_file",
                        tool_input=json.dumps({"path": "loop.txt"}),
                    )
                ],
                stop_reason="tool_use",
            )

        def model(self) -> str:
            return "mock"

        def set_model(self, name: str) -> None:
            pass

    provider = _InfiniteToolUseProvider()
    research = Research(provider=provider)

    research.run("investiga algo que nunca termina")

    assert provider.calls == 10  # _MAX_TURNS de subagents/research.py
