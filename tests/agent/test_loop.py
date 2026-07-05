"""tests/agent/test_loop.py -- agent loop (spec agent-loop). Fase 6, tareas 6.5-6.6.

Usa `MockProvider` (tests/support) para simular turnos sin red. Monkeypatchea
`erickfp.agent.agent.run_tool_with_gate` para verificar que TODO `tool_use`
pasa por el gate -- nunca hay una ruta que invoque `tool.execute()`
directamente (Requirement 'Permission gate sin fuga', Scenario 'Ninguna tool
se ejecuta sin pasar por el gate').
"""

from __future__ import annotations

import pytest

from erickfp.agent.loop import run_turn
from erickfp.agent.policy import AllowList, AlwaysAsk, AskOnce
from erickfp.agent.tokens import TokenTracker
from erickfp.api.types import Block, Entry, Message, Response, ToolDef, Usage
from erickfp.compaction.base import CompactionStrategy
from erickfp.tools.mcp import MCPTool
from erickfp.tools.recall import RecallTool
from erickfp.tools.registry import ToolRegistry
from tests.support import FakeTool, MockProvider


def test_no_tool_use_skips_gate(monkeypatch) -> None:
    """Scenario 'Turno sin tool use': texto puro no invoca el gate."""
    gate_calls: list[str] = []
    monkeypatch.setattr(
        "erickfp.agent.agent.run_tool_with_gate",
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

    monkeypatch.setattr("erickfp.agent.agent.run_tool_with_gate", fake_gate)

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
        "erickfp.agent.agent.run_tool_with_gate",
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
        "erickfp.agent.agent.run_tool_with_gate",
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


@pytest.mark.parametrize(
    "policy_factory",
    [lambda: AlwaysAsk(), lambda: AllowList({"alpha"}), lambda: AskOnce()],
)
def test_no_tool_executes_without_gate_and_policy_regardless_of_policy_impl(
    monkeypatch, policy_factory
) -> None:
    """Riesgo transversal (a) del Lote 4 (spec permission-policy): sin
    importar la implementacion de `PermissionPolicy` inyectada, NO existe
    ruta directa a `tool.execute()` -- `run_tool_with_gate` (la funcion real,
    sin monkeypatchear) SIEMPRE consulta `policy.decide()` antes de resolver
    la tool call."""
    monkeypatch.setattr("erickfp.agent.gate.read_line", lambda prompt: "y")

    tool = FakeTool(name="alpha")
    tools = ToolRegistry()
    tools.register(tool)
    policy = policy_factory()

    decide_calls: list[tuple[str, str]] = []
    original_decide = policy.decide

    def spy_decide(tool_name: str, tool_input: str) -> str:
        decide_calls.append((tool_name, tool_input))
        return original_decide(tool_name, tool_input)

    monkeypatch.setattr(policy, "decide", spy_decide)

    first_response = Response(
        content=[
            Block(type="tool_use", tool_use_id="call-1", tool_name="alpha", tool_input="{}")
        ],
        stop_reason="tool_use",
    )
    second_response = Response(content=[Block(type="text", text="listo")], stop_reason="end_turn")
    provider = MockProvider(responses=[first_response, second_response])
    messages = [Message(role="user", content=[Block(type="text", text="hazlo")])]

    run_turn(provider, tools, messages, tools.definitions(), policy=policy)

    assert decide_calls == [("alpha", "{}")]  # el gate SIEMPRE consulto la policy
    assert tool.executed_with == ["{}"]  # unica ejecucion, siempre via el gate


class _FakeRecallSource:
    """Doble ad-hoc (Lote 5, spec memory-store delta): satisface
    `.recall(query, limit)` sin importar `erickfp.memory` -- mismo patron
    de duck typing usado en `tests/tools/test_recall.py`."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def recall(self, query: str, limit: int) -> list[Entry]:
        self.calls.append((query, limit))
        return [Entry(kind="fact", content="dato recuperado de prueba")]


def test_recall_tool_passes_through_gate_like_other_tools(monkeypatch) -> None:
    """Lote 5 harness-v0-2 (spec memory-store delta, Requirement 'Recall
    bajo demanda' MODIFICADO, Scenario 'Recall como Tool pasa por el
    gate'): una `RecallTool` real (sin monkeypatchear `run_tool_with_gate`)
    consulta la policy activa y solo ejecuta `store.recall(...)` a traves
    del gate -- exactamente el mismo camino que cualquier otra tool local
    (`bash`/`read_file`/`write_file`), sin ruta alterna."""
    monkeypatch.setattr("erickfp.agent.gate.read_line", lambda prompt: "y")

    recall_source = _FakeRecallSource()
    tool = RecallTool(recall_source)
    tools = ToolRegistry()
    tools.register(tool)
    policy = AllowList({"recall"})

    decide_calls: list[tuple[str, str]] = []
    original_decide = policy.decide

    def spy_decide(tool_name: str, tool_input: str) -> str:
        decide_calls.append((tool_name, tool_input))
        return original_decide(tool_name, tool_input)

    monkeypatch.setattr(policy, "decide", spy_decide)

    tool_input = '{"query": "prueba", "limit": 5}'
    first_response = Response(
        content=[
            Block(
                type="tool_use",
                tool_use_id="call-1",
                tool_name="recall",
                tool_input=tool_input,
            )
        ],
        stop_reason="tool_use",
    )
    second_response = Response(content=[Block(type="text", text="listo")], stop_reason="end_turn")
    provider = MockProvider(responses=[first_response, second_response])
    messages = [Message(role="user", content=[Block(type="text", text="recuerda algo")])]

    result = run_turn(provider, tools, messages, tools.definitions(), policy=policy)

    assert decide_calls == [("recall", tool_input)]  # el gate consulto la policy
    assert recall_source.calls == [("prueba", 5)]  # unica ejecucion, siempre via el gate
    tool_result = result[-2].content[0]
    assert tool_result.type == "tool_result"
    assert tool_result.is_error is False
    assert "dato recuperado de prueba" in tool_result.tool_result


class _FakeMCPSession:
    """Doble ad-hoc (Lote 8, spec mcp-support): satisface
    `.call_tool(name, arguments)` sin depender del SDK real `mcp` ni de un
    servidor MCP real -- mismo patron de duck typing que `_FakeRecallSource`
    de este mismo archivo."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def call_tool(self, name: str, arguments: dict) -> tuple[str, bool]:
        self.calls.append((name, arguments))
        return ("cambios: 2 archivos", False)


def test_mcp_tool_passes_through_same_gate_and_policy(monkeypatch) -> None:
    """Lote 8 harness-v0-2 (spec mcp-support, Requirement 'Mismo gate y
    policy que las tools locales', Scenario 'Tool MCP pasa por el gate'):
    una `MCPTool` real (sin monkeypatchear `run_tool_with_gate`) consulta
    la policy activa y solo invoca `session.call_tool(...)` a traves del
    gate -- exactamente el mismo camino que `bash`/`read_file`/
    `write_file`/`recall`, sin ruta de ejecucion alternativa."""
    monkeypatch.setattr("erickfp.agent.gate.read_line", lambda prompt: "y")

    session = _FakeMCPSession()
    tool = MCPTool(
        session,
        ToolDef(
            name="git_status",
            description="tool remota MCP de prueba",
            input_schema={"type": "object", "properties": {}},
            required=[],
        ),
    )
    tools = ToolRegistry()
    tools.register(tool)
    policy = AllowList({"git_status"})

    decide_calls: list[tuple[str, str]] = []
    original_decide = policy.decide

    def spy_decide(tool_name: str, tool_input: str) -> str:
        decide_calls.append((tool_name, tool_input))
        return original_decide(tool_name, tool_input)

    monkeypatch.setattr(policy, "decide", spy_decide)

    tool_input = '{"path": "."}'
    first_response = Response(
        content=[
            Block(
                type="tool_use",
                tool_use_id="call-1",
                tool_name="git_status",
                tool_input=tool_input,
            )
        ],
        stop_reason="tool_use",
    )
    second_response = Response(content=[Block(type="text", text="listo")], stop_reason="end_turn")
    provider = MockProvider(responses=[first_response, second_response])
    messages = [Message(role="user", content=[Block(type="text", text="que cambio?")])]

    result = run_turn(provider, tools, messages, tools.definitions(), policy=policy)

    assert decide_calls == [("git_status", tool_input)]  # el gate consulto la policy
    assert session.calls == [("git_status", {"path": "."})]  # unica ejecucion, via el gate
    tool_result = result[-2].content[0]
    assert tool_result.type == "tool_result"
    assert tool_result.is_error is False
    assert "cambios: 2 archivos" in tool_result.tool_result


class _SpyCompactionStrategy:
    """Doble de `CompactionStrategy` (Lote 6, design.md Decision 5): registra
    los `messages` recibidos y retorna una lista mas corta reconocible, para
    poder verificar tanto QUE se invoco como CUANDO (antes del primer
    `provider.send`)."""

    def __init__(self) -> None:
        self.calls: list[list[Message]] = []

    def compact(self, messages: list[Message]) -> list[Message]:
        self.calls.append(messages)
        return messages[-1:]  # recorte reconocible: solo el ultimo mensaje


def test_run_turn_invokes_compaction_before_first_provider_send() -> None:
    """Lote 6 harness-v0-2, tarea 6.9 (design.md Decision 5: 'Invocacion:
    inicio de run_turn, antes del primer provider.send'): el `messages`
    efectivamente enviado al Provider es el YA COMPACTADO -- no el original
    -- y `compact()` se invoca exactamente una vez por turno (no una vez por
    cada llamada intermedia a `provider.send` dentro del mismo turno)."""
    compaction: CompactionStrategy = _SpyCompactionStrategy()
    provider = MockProvider(
        responses=[Response(content=[Block(type="text", text="listo")], stop_reason="end_turn")]
    )
    messages = [
        Message(role="user", content=[Block(type="text", text="turno viejo")]),
        Message(role="user", content=[Block(type="text", text="turno reciente")]),
    ]

    run_turn(provider, ToolRegistry(), messages, [], compaction=compaction)

    assert len(compaction.calls) == 1  # una sola vez, al inicio del turno
    assert compaction.calls[0] == messages  # recibio el historial ORIGINAL
    assert len(provider.sent_messages) == 1
    assert provider.sent_messages[0] == messages[-1:]  # el Provider vio el YA compactado


def test_run_turn_without_compaction_keeps_previous_behavior() -> None:
    """Retrocompatibilidad: `compaction=None` (default) preserva el
    comportamiento previo bit-a-bit -- ninguna prueba existente deberia
    romperse (mismo patron que `tracker=None`/`policy=None`)."""
    provider = MockProvider(
        responses=[Response(content=[Block(type="text", text="hola")], stop_reason="end_turn")]
    )
    messages = [Message(role="user", content=[Block(type="text", text="hola")])]

    result = run_turn(provider, ToolRegistry(), messages, [])

    assert provider.sent_messages[0] == messages  # sin compactar
    assert result[-1].content[0].text == "hola"
