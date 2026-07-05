"""tests/hooks/test_core_guard_policy.py -- Riesgo transversal (b) del Lote 4
harness-v0-2 (spec permission-policy, Requirement 'core_guard prevalece sobre
cualquier policy', tarea 4.8): ninguna implementacion de `PermissionPolicy`
(`AllowList`/`AskOnce`) puede aprobar automaticamente una escritura en
`.ErickFP/core/*` -- el `core_guard` (`PreToolUse`) SIEMPRE se evalua antes
del gate/policy, sin excepcion, incluso si la policy ya "confia" en la tool
por una llamada previa fuera de core/*.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from erickfp.agent.loop import run_turn
from erickfp.agent.policy import AllowList, AskOnce
from erickfp.api.types import Block, Message, Response
from erickfp.hooks.core_guard import CoreGuardHook
from erickfp.hooks.manager import HookManager, PhaseContext
from erickfp.tools.registry import ToolRegistry
from tests.support import FakeTool, MockProvider


@pytest.mark.parametrize(
    "policy_factory", [lambda: AllowList({"write_file"}), lambda: AskOnce()]
)
def test_allowlist_and_askonce_never_bypass_core_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, policy_factory
) -> None:
    root = tmp_path / ".ErickFP"
    (root / "core").mkdir(parents=True)
    (root / "workspace").mkdir(parents=True)

    # Si la policy llegara a preguntar (AskOnce), el humano aprueba -- lo cual
    # no debe importar para la escritura en core/*, bloqueada aguas arriba.
    monkeypatch.setattr("erickfp.agent.gate.read_line", lambda prompt: "y")

    tool = FakeTool(name="write_file")
    tools = ToolRegistry()
    tools.register(tool)
    policy = policy_factory()

    hook_manager = HookManager([CoreGuardHook(root)])
    ctx = PhaseContext(phase="chat")

    outside_input = json.dumps({"path": str(root / "workspace" / "nota.md"), "content": "ok"})
    core_input = json.dumps({"path": str(root / "core" / "Claude"), "content": "intento"})

    first_response = Response(
        content=[
            Block(
                type="tool_use",
                tool_use_id="call-1",
                tool_name="write_file",
                tool_input=outside_input,
            )
        ],
        stop_reason="tool_use",
    )
    second_response = Response(
        content=[
            Block(
                type="tool_use",
                tool_use_id="call-2",
                tool_name="write_file",
                tool_input=core_input,
            )
        ],
        stop_reason="tool_use",
    )
    third_response = Response(content=[Block(type="text", text="listo")], stop_reason="end_turn")
    provider = MockProvider(responses=[first_response, second_response, third_response])
    messages = [Message(role="user", content=[Block(type="text", text="hazlo")])]

    result = run_turn(
        provider,
        tools,
        messages,
        tools.definitions(),
        hook_manager=hook_manager,
        ctx=ctx,
        policy=policy,
    )

    first_tool_result = result[2].content[0]
    second_tool_result = result[4].content[0]

    assert first_tool_result.is_error is False  # escritura fuera de core: aprobada
    assert second_tool_result.is_error is True  # escritura en core: bloqueada SIEMPRE
    assert "core" in second_tool_result.tool_result
    # La tool real jamas se ejecuto para el target de core/*, sin importar que
    # la policy ya hubiera "confiado" en write_file por la llamada anterior.
    assert tool.executed_with == [outside_input]
