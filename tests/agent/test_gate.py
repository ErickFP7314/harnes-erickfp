"""tests/agent/test_gate.py -- permission gate (spec agent-loop, Requirement
'Permission gate sin fuga'). Fase 6, tareas 6.1-6.3.

El gate NUNCA lanza una excepcion: toda decision se traduce a un valor de
retorno explicito (bool en `confirm()`, `Block` tool_result en
`run_tool_with_gate()`), igual que el contrato de HookResult (Decision 3).
"""

from __future__ import annotations

import pytest

from erickfp.agent.gate import confirm, run_tool_with_gate
from erickfp.api.types import Block
from tests.support import FakeTool


@pytest.mark.parametrize("raw_input", ["", "n", "yes", "Y", "maybe", "  ", "\n"])
def test_gate_denies_by_default_on_empty_or_invalid_input(monkeypatch, raw_input) -> None:
    """Enter vacio o cualquier texto distinto de 'y' exacto -> deny (default)."""
    monkeypatch.setattr("erickfp.agent.gate.read_line", lambda prompt: raw_input)

    assert confirm("bash", '{"command": "ls"}') is False


def test_gate_approves_only_on_explicit_y(monkeypatch) -> None:
    """Solo 'y' (tras strip) aprueba -- ninguna otra variante lo hace."""
    monkeypatch.setattr("erickfp.agent.gate.read_line", lambda prompt: "y")

    assert confirm("bash", '{"command": "ls"}') is True


def test_gate_denial_produces_tool_result_is_error_true_no_exception(monkeypatch) -> None:
    """'n' produce tool_result(is_error=True) sin lanzar excepcion ni ejecutar
    la tool real (Scenario 'Negacion explicita')."""
    monkeypatch.setattr("erickfp.agent.gate.read_line", lambda prompt: "n")
    tool = FakeTool(name="bash")
    tool_use = Block(
        type="tool_use",
        tool_use_id="call-1",
        tool_name="bash",
        tool_input='{"command": "rm -rf /"}',
    )

    result = run_tool_with_gate(tool, tool_use)

    assert result.type == "tool_result"
    assert result.tool_use_id == "call-1"
    assert result.is_error is True
    assert tool.executed_with == []  # la tool real jamas se invoco


def test_gate_approval_executes_the_real_tool(monkeypatch) -> None:
    """'y' ejecuta la tool real y su resultado real viaja en el tool_result
    (Scenario 'Aprobacion explicita')."""
    monkeypatch.setattr("erickfp.agent.gate.read_line", lambda prompt: "y")
    tool = FakeTool(name="bash")
    tool_use = Block(
        type="tool_use", tool_use_id="call-2", tool_name="bash", tool_input='{"command": "ls"}'
    )

    result = run_tool_with_gate(tool, tool_use)

    assert result.type == "tool_result"
    assert result.tool_use_id == "call-2"
    assert result.is_error is False
    assert tool.executed_with == ['{"command": "ls"}']
    assert result.tool_result == 'executed:{"command": "ls"}'
