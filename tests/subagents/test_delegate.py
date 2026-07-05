"""tests/subagents/test_delegate.py -- `DelegateTool` (Lote 7 harness-v0-2,
tareas 7.7-7.8, design.md "Ciclo delegate" + Decision 7 / spec subagents).
"""

from __future__ import annotations

import json

from erickfp.agent.loop import run_turn
from erickfp.api.types import Block, Message, Response
from erickfp.provider.base import ProviderError
from erickfp.subagents.delegate import DelegateTool
from erickfp.subagents.research import Research
from erickfp.tools.registry import ToolRegistry
from tests.support import MockProvider


def test_delegate_tool_definition_name_and_schema() -> None:
    tool = DelegateTool(Research(provider=MockProvider()))
    definition = tool.definition()

    assert definition.name == "delegate_research"
    assert definition.required == ["task"]
    assert "task" in definition.input_schema["properties"]


def test_internal_subagent_calls_do_not_reask_approval(monkeypatch) -> None:
    """Scenario 'Tool calls internas del subagente no piden aprobacion
    individual': el humano aprueba UNA sola vez la tool call `delegate_
    research`; el subagente `Research` ejecuta DOS llamadas internas a
    `read_file` -- ninguna de ellas dispara una nueva pregunta y/n
    (`read_line` solo se invoca una vez en total)."""
    read_line_calls: list[str] = []
    monkeypatch.setattr(
        "erickfp.agent.gate.read_line",
        lambda prompt: read_line_calls.append(prompt) or "y",
    )

    first_read = Response(
        content=[
            Block(
                type="tool_use",
                tool_use_id="r1",
                tool_name="read_file",
                tool_input=json.dumps({"path": "a.txt"}),
            )
        ],
        stop_reason="tool_use",
    )
    second_read = Response(
        content=[
            Block(
                type="tool_use",
                tool_use_id="r2",
                tool_name="read_file",
                tool_input=json.dumps({"path": "b.txt"}),
            )
        ],
        stop_reason="tool_use",
    )
    synthesis = Response(
        content=[Block(type="text", text="sintesis final")], stop_reason="end_turn"
    )
    inner_provider = MockProvider(responses=[first_read, second_read, synthesis])

    delegate_tool = DelegateTool(Research(provider=inner_provider))
    tools = ToolRegistry()
    tools.register(delegate_tool)

    delegate_call = Response(
        content=[
            Block(
                type="tool_use",
                tool_use_id="call-1",
                tool_name="delegate_research",
                tool_input=json.dumps({"task": "averigua algo"}),
            )
        ],
        stop_reason="tool_use",
    )
    outer_final = Response(content=[Block(type="text", text="listo")], stop_reason="end_turn")
    outer_provider = MockProvider(responses=[delegate_call, outer_final])
    messages = [Message(role="user", content=[Block(type="text", text="delega esto")])]

    result = run_turn(outer_provider, tools, messages, tools.definitions())

    # UNA sola pregunta y/n en TODA la ejecucion: la de `delegate_research`.
    # Las 2 lecturas internas de Research nunca tocaron read_line.
    assert len(read_line_calls) == 1
    assert "delegate_research" in read_line_calls[0]

    tool_result = result[-2].content[0]
    assert tool_result.type == "tool_result"
    assert tool_result.is_error is False
    assert "sintesis final" in tool_result.tool_result
    assert "↳" in tool_result.tool_result  # salida indentada (design.md D7)


def test_delegate_execute_rejects_invalid_and_empty_input() -> None:
    tool = DelegateTool(Research(provider=MockProvider()))

    invalid_json_result, invalid_is_error = tool.execute("no es json")
    assert invalid_is_error is True

    empty_task_result, empty_is_error = tool.execute(json.dumps({"task": ""}))
    assert empty_is_error is True


def test_delegate_execute_translates_provider_error_to_tool_result() -> None:
    """Un fallo interno del subagente (p.ej. `ProviderError` tras agotar
    reintentos durante la investigacion delegada) SIEMPRE se traduce a un
    `tool_result(is_error=True)` -- nunca se propaga como excepcion nativa."""

    class _FailingProvider:
        def send(self, messages: object, tools: object) -> Response:
            raise ProviderError("el proveedor agoto sus reintentos")

        def model(self) -> str:
            return "mock"

        def set_model(self, name: str) -> None:
            pass

    tool = DelegateTool(Research(provider=_FailingProvider()))

    result_text, is_error = tool.execute(json.dumps({"task": "algo"}))

    assert is_error is True
    assert "agoto sus reintentos" in result_text
