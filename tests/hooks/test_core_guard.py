"""tests/hooks/test_core_guard.py -- hook core_guard (Fase 8, tareas
8.5-8.8). Riesgo alto de la propuesta (spec phase-hooks, Requirement
'Proteccion incondicional de core/*'): este hook debe bloquear CUALQUIER
escritura en `.ErickFP/core/*`, incluso si el permission gate ya aprobo, sin
excepcion por fase ni en `chat`, y resolviendo paths equivalentes (relativos,
`..`, symlinks) con `Path.resolve()` antes de comparar.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from erickfp.hooks.core_guard import CoreGuardHook
from erickfp.hooks.manager import PhaseContext


def _write_file_input(path: str) -> str:
    return json.dumps({"path": path, "content": "intento de modificacion"})


def test_core_guard_blocks_write_to_core_even_after_gate_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Scenario 'Escritura directa bloqueada': se simula que el humano YA
    respondio 'y' en el permission gate (`agent.gate.confirm`) ANTES de
    consultar el hook -- el resultado del gate es irrelevante: el hook
    bloquea igual porque el path cae dentro de `core/*`."""
    root = tmp_path / ".ErickFP"
    (root / "core").mkdir(parents=True)
    monkeypatch.setattr("builtins.input", lambda *_: "y")

    from erickfp.agent.gate import confirm

    gate_approved = confirm("write_file", "{}")
    assert gate_approved is True  # el gate SI aprobo

    hook = CoreGuardHook(root=root)
    ctx = PhaseContext(
        phase="ordena",
        tool_name="write_file",
        tool_input=_write_file_input(str(root / "core" / "Claude")),
    )

    result = hook.run(ctx)

    assert result.decision == "deny"
    assert "core" in result.reason


@pytest.mark.parametrize(
    "relative_path",
    [
        "core/Claude",
        "core/agents/planner.md",
        "core/../core/Claude",  # equivalente via ".."
    ],
)
def test_core_guard_blocks_equivalent_paths(tmp_path: Path, relative_path: str) -> None:
    root = tmp_path / ".ErickFP"
    (root / "core" / "agents").mkdir(parents=True)

    hook = CoreGuardHook(root=root)
    ctx = PhaseContext(
        phase="chat",
        tool_name="write_file",
        tool_input=_write_file_input(str(root / relative_path)),
    )

    result = hook.run(ctx)

    assert result.decision == "deny"


def test_core_guard_blocks_symlink_pointing_into_core(tmp_path: Path) -> None:
    root = tmp_path / ".ErickFP"
    (root / "core").mkdir(parents=True)
    outside_link = tmp_path / "sneaky_link.md"
    outside_link.symlink_to(root / "core" / "Claude")

    hook = CoreGuardHook(root=root)
    ctx = PhaseContext(
        phase="ordena",
        tool_name="write_file",
        tool_input=_write_file_input(str(outside_link)),
    )

    result = hook.run(ctx)

    assert result.decision == "deny"


def test_core_guard_allows_writes_outside_core(tmp_path: Path) -> None:
    """Scenario 'Escritura fuera de core/* no se bloquea por este hook'."""
    root = tmp_path / ".ErickFP"
    (root / "core").mkdir(parents=True)
    (root / "cogito").mkdir(parents=True)

    hook = CoreGuardHook(root=root)
    ctx = PhaseContext(
        phase="ordena",
        tool_name="write_file",
        tool_input=_write_file_input(str(root / "cogito" / "objetivo" / "ordena.md")),
    )

    result = hook.run(ctx)

    assert result.decision == "allow"


@pytest.mark.parametrize("phase", ["duda", "divide", "ordena", "enumera", "chat"])
def test_core_guard_active_in_every_phase_and_chat(tmp_path: Path, phase: str) -> None:
    """Scenario 'Bloqueo activo en toda fase y en chat': el hook no consulta
    `ctx.phase` para decidir -- bloquea igual sin importar la fase o si es
    una sesion de `chat`."""
    root = tmp_path / ".ErickFP"
    (root / "core").mkdir(parents=True)

    hook = CoreGuardHook(root=root)
    ctx = PhaseContext(
        phase=phase,
        tool_name="write_file",
        tool_input=_write_file_input(str(root / "core" / "Claude")),
    )

    result = hook.run(ctx)

    assert result.decision == "deny"


def test_core_guard_ignores_tool_inputs_without_path_field(tmp_path: Path) -> None:
    """Tools sin campo 'path' (p.ej. `bash`) no son afectadas por este hook."""
    root = tmp_path / ".ErickFP"
    (root / "core").mkdir(parents=True)

    hook = CoreGuardHook(root=root)
    ctx = PhaseContext(phase="ordena", tool_name="bash", tool_input=json.dumps({"command": "ls"}))

    result = hook.run(ctx)

    assert result.decision == "allow"
