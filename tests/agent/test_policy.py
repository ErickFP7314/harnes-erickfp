"""tests/agent/test_policy.py -- PermissionPolicy (spec permission-policy,
Lote 4 harness-v0-2, tareas 4.1/4.3/4.5/4.7). `AlwaysAsk`/`AllowList`/
`AskOnce` implementan el mismo Protocol `decide(tool_name, tool_input) ->
Literal["allow", "deny", "ask"]` que `run_tool_with_gate` (agent/gate.py)
consulta ANTES de decidir si pregunta al humano.
"""

from __future__ import annotations

import pytest

from erickfp.agent.gate import run_tool_with_gate
from erickfp.agent.policy import AllowList, AlwaysAsk, AskOnce
from erickfp.api.types import Block
from tests.support import FakeTool


def _tool_use(tool_name: str, call_id: str = "call-1") -> Block:
    return Block(type="tool_use", tool_use_id=call_id, tool_name=tool_name, tool_input="{}")


@pytest.mark.parametrize(
    ("raw_input", "expected_error"),
    [("y", False), ("n", True), ("", True), ("yes", True), ("Y", True), ("maybe", True)],
)
def test_always_ask_matches_cycle1_gate_behavior(monkeypatch, raw_input, expected_error) -> None:
    """Scenario 'AlwaysAsk equivalente al gate del ciclo 1': el resultado con
    `AlwaysAsk` explicita es identico al comportamiento default (sin policy,
    ciclo 1) -- se pregunta y/n, solo 'y' aprueba."""
    monkeypatch.setattr("erickfp.agent.gate.read_line", lambda prompt: raw_input)
    tool = FakeTool(name="bash")

    result_default = run_tool_with_gate(tool, _tool_use("bash", "call-1"))
    result_explicit = run_tool_with_gate(tool, _tool_use("bash", "call-2"), AlwaysAsk())

    assert result_default.is_error is expected_error
    assert result_explicit.is_error is expected_error


def test_allowlist_approves_without_asking(monkeypatch) -> None:
    """Scenario 'AllowList aprueba sin preguntar': read_line() NUNCA se
    invoca para una tool preaprobada."""
    read_line_calls: list[str] = []
    monkeypatch.setattr(
        "erickfp.agent.gate.read_line", lambda prompt: read_line_calls.append(prompt) or "n"
    )
    tool = FakeTool(name="read_file")
    policy = AllowList({"read_file"})

    result = run_tool_with_gate(tool, _tool_use("read_file"), policy)

    assert read_line_calls == []
    assert result.is_error is False
    assert tool.executed_with == ["{}"]


def test_askonce_asks_once_then_reuses_decision(monkeypatch) -> None:
    """Scenario 'AskOnce pregunta una sola vez por sesion': la segunda tool
    call de la misma tool reutiliza la decision aprobada sin volver a
    preguntar."""
    read_line_calls: list[str] = []
    monkeypatch.setattr(
        "erickfp.agent.gate.read_line", lambda prompt: read_line_calls.append(prompt) or "y"
    )
    tool = FakeTool(name="bash")
    policy = AskOnce()

    first = run_tool_with_gate(tool, _tool_use("bash", "call-1"), policy)
    second = run_tool_with_gate(tool, _tool_use("bash", "call-2"), policy)

    assert first.is_error is False
    assert second.is_error is False
    assert len(read_line_calls) == 1  # solo pregunto una vez
    assert tool.executed_with == ["{}", "{}"]


def test_askonce_ambiguous_response_is_denial_not_cached(monkeypatch) -> None:
    """Scenario 'Respuesta ambigua bajo AskOnce': la respuesta ambigua se
    trata como negacion y NO se registra como aprobacion futura -- la
    siguiente tool call de la misma tool vuelve a preguntar."""
    read_line_calls: list[str] = []
    monkeypatch.setattr(
        "erickfp.agent.gate.read_line",
        lambda prompt: read_line_calls.append(prompt) or "tal vez",
    )
    tool = FakeTool(name="bash")
    policy = AskOnce()

    first = run_tool_with_gate(tool, _tool_use("bash", "call-1"), policy)
    second = run_tool_with_gate(tool, _tool_use("bash", "call-2"), policy)

    assert first.is_error is True
    assert second.is_error is True
    assert len(read_line_calls) == 2  # NO se cacheo -- pregunta de nuevo
    assert tool.executed_with == []
