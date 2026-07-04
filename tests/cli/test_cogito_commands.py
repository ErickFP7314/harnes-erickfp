"""tests/cli/test_cogito_commands.py -- comandos `duda`/`divide`/`ordena`/
`enumera` (Fase 10, tarea 10.7).

Igual que `chat()` (Fase 7), el Provider real (LiteLLM/Gemini) no se ejercita
aqui -- eso queda para el smoke E2E manual (Fase 11.3). Se inyecta un
`MockProvider` via monkeypatch sobre `erickfp.cli.LiteLLMGeminiProvider` para
probar el cableado real del orquestador sin red.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import erickfp.cli as cli_module
from erickfp.api.types import Block, Response
from erickfp.cli import _load_role_prompt, _slugify, app
from tests.support import MockProvider

runner = CliRunner()


def test_slugify_normalizes_accents_spaces_and_case() -> None:
    assert _slugify("Añadir Auth de Usuario") == "anadir-auth-de-usuario"


def test_slugify_falls_back_to_default_on_empty_result() -> None:
    assert _slugify("!!!") == "objetivo"


def test_load_role_prompt_combines_claude_axioms_and_role_file(tmp_path: Path) -> None:
    root = tmp_path / ".ErickFP"
    (root / "core" / "agents").mkdir(parents=True)
    (root / "core" / "Claude").write_text("AXIOMA: legibilidad.")
    (root / "core" / "agents" / "planner.md").write_text("Rol: Planner.")

    prompt = _load_role_prompt(root, "planner")

    assert "AXIOMA: legibilidad." in prompt
    assert "Rol: Planner." in prompt


def _init_root(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])
    return tmp_path / ".ErickFP"


def test_divide_fails_cleanly_without_duda_artifact(tmp_path: Path, monkeypatch) -> None:
    """Scenario 'Fase bloqueante sin artefacto previo': no crashea, informa
    la fase y el artefacto faltante, exit_code != 0."""
    _init_root(tmp_path, monkeypatch)

    result = runner.invoke(app, ["divide", "mi-slug"])

    assert result.exit_code == 1
    assert "duda" in result.output.lower()


def test_duda_command_creates_artifact_with_fake_provider(tmp_path: Path, monkeypatch) -> None:
    root = _init_root(tmp_path, monkeypatch)
    fake_provider = MockProvider(
        responses=[
            Response(
                content=[Block(type="text", text="ACEPTADO: # duda.md\n\nObjetivo validado.")],
                stop_reason="end_turn",
            )
        ]
    )
    monkeypatch.setattr(cli_module, "LiteLLMGeminiProvider", lambda: fake_provider)

    result = runner.invoke(app, ["duda", "Objetivo Claro De Prueba"])

    assert result.exit_code == 0, result.output
    artifact = root / "cogito" / "objetivo-claro-de-prueba" / "duda.md"
    assert artifact.is_file()
    assert "Objetivo validado" in artifact.read_text()


def test_duda_command_reports_clarification_without_writing_artifact(
    tmp_path: Path, monkeypatch
) -> None:
    root = _init_root(tmp_path, monkeypatch)
    fake_provider = MockProvider(
        responses=[
            Response(
                content=[Block(type="text", text="AMBIGUO: falta especificar el backend.")],
                stop_reason="end_turn",
            )
        ]
    )
    monkeypatch.setattr(cli_module, "LiteLLMGeminiProvider", lambda: fake_provider)

    result = runner.invoke(app, ["duda", "Objetivo Ambiguo"])

    assert result.exit_code == 0, result.output
    assert "falta especificar el backend" in result.output.lower()
    assert not (root / "cogito" / "objetivo-ambiguo" / "duda.md").exists()
