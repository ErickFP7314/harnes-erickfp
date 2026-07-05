"""tests/agent/test_agent_class.py -- extraccion de `Agent` (Lote 7
harness-v0-2, tareas 7.1-7.2, design.md Decision 7 / spec subagents,
Requirement 'Agent reutilizable y subagente Research read-only')."""

from __future__ import annotations

import inspect

from erickfp.agent.agent import Agent
from erickfp.agent.loop import run_turn
from erickfp.api.types import Block, Message, Response
from erickfp.tools.registry import ToolRegistry
from tests.support import MockProvider


def test_free_run_turn_wraps_agent_class_same_signature(monkeypatch) -> None:
    """La funcion libre `run_turn` (agent/loop.py) preserva su firma EXACTA
    (mismos parametros, mismo orden, mismos defaults `None`) respecto a los
    Lotes 1-6, pero delega la ejecucion real en `Agent` (agent/agent.py,
    Lote 7): construye una instancia de un solo uso por llamada y corre
    `agent.run_turn(messages)`."""
    signature = inspect.signature(run_turn)
    assert list(signature.parameters) == [
        "provider",
        "tools",
        "messages",
        "tool_defs",
        "hook_manager",
        "ctx",
        "tracker",
        "policy",
        "compaction",
    ]
    for name in ("hook_manager", "ctx", "tracker", "policy", "compaction"):
        assert signature.parameters[name].default is None

    constructed: list[dict[str, object]] = []
    expected_result = [Message(role="assistant", content=[Block(type="text", text="via-agent")])]

    class _SpyAgent:
        def __init__(self, provider: object, tools: object, tool_defs: object, **kwargs: object):
            constructed.append(
                {"provider": provider, "tools": tools, "tool_defs": tool_defs, **kwargs}
            )

        def run_turn(self, messages: list[Message]) -> list[Message]:
            constructed[-1]["messages_seen"] = messages
            return expected_result

    monkeypatch.setattr("erickfp.agent.loop.Agent", _SpyAgent)

    provider = MockProvider()
    tools = ToolRegistry()
    messages = [Message(role="user", content=[Block(type="text", text="hola")])]

    result = run_turn(provider, tools, messages, [])

    assert result is expected_result
    assert len(constructed) == 1
    assert constructed[0]["provider"] is provider
    assert constructed[0]["tools"] is tools
    assert constructed[0]["tool_defs"] == []
    assert constructed[0]["messages_seen"] == messages
    # los kwargs opcionales llegan explicitos (incluso en None) -- ninguno
    # se omite silenciosamente al construir el Agent.
    for name in ("hook_manager", "ctx", "tracker", "policy", "compaction"):
        assert constructed[0][name] is None


def test_agent_class_is_reusable_with_independent_state() -> None:
    """El `Agent` es instanciable multiples veces con estado independiente
    (habilita subagentes, Lote 7): dos instancias no comparten `provider`
    ni historial de mensajes entre si."""
    provider_a = MockProvider(
        responses=[Response(content=[Block(type="text", text="A")], stop_reason="end_turn")]
    )
    provider_b = MockProvider(
        responses=[Response(content=[Block(type="text", text="B")], stop_reason="end_turn")]
    )
    agent_a = Agent(provider_a, ToolRegistry(), [])
    agent_b = Agent(provider_b, ToolRegistry(), [])

    result_a = agent_a.run_turn(
        [Message(role="user", content=[Block(type="text", text="hola")])]
    )
    result_b = agent_b.run_turn(
        [Message(role="user", content=[Block(type="text", text="hola")])]
    )

    assert result_a[-1].content[0].text == "A"
    assert result_b[-1].content[0].text == "B"
    assert len(provider_a.sent_messages) == 1
    assert len(provider_b.sent_messages) == 1
