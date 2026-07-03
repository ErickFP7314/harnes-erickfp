"""tests/cli/test_init.py -- comando `erickfp init` (spec cli-init). Fase 7,
tareas 7.1-7.2.

Usa `CliRunner` (Typer/Click) sobre `tmp_path` para no tocar el filesystem
real del usuario -- `monkeypatch.chdir` fija el cwd del proceso de prueba.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from erickfp.cli import app

runner = CliRunner()


def test_first_init_creates_full_tree(tmp_path: Path, monkeypatch) -> None:
    """Scenario 'Primera inicializacion': arbol completo, plantillas no vacias."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0, result.output
    root = tmp_path / ".ErickFP"

    claude_path = root / "core" / "Claude"
    assert claude_path.is_file()
    assert claude_path.read_text().strip() != ""

    agents_dir = root / "core" / "agents"
    assert agents_dir.is_dir()
    for role_file in ("planner.md", "coder.md", "reviewer.md"):
        role_path = agents_dir / role_file
        assert role_path.is_file()
        assert role_path.read_text().strip() != ""

    adr_dir = root / "adr"
    assert adr_dir.is_dir()
    assert any(p.is_file() and p.read_text().strip() for p in adr_dir.iterdir())

    assert (root / "memory").is_dir()
    assert (root / "hooks").is_dir()


def test_reinit_does_not_overwrite_core_without_confirmation(
    tmp_path: Path, monkeypatch
) -> None:
    """Scenario 'Re-inicializacion sobre estructura existente': `core/Claude`
    y `core/agents` no se sobrescriben sin confirmacion explicita, y el
    sistema informa que rutas ya existian."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    claude_path = tmp_path / ".ErickFP" / "core" / "Claude"
    claude_path.write_text("axioma modificado por el humano")

    # El humano responde "n" (no sobrescribir) a cada prompt de confirmacion.
    result = runner.invoke(app, ["init"], input="n\nn\nn\nn\n")

    assert result.exit_code == 0, result.output
    assert claude_path.read_text() == "axioma modificado por el humano"
    assert "existente" in result.output.lower() or "ya exist" in result.output.lower()
