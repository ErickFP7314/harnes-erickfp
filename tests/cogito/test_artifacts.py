"""tests/cogito/test_artifacts.py -- validacion y persistencia de artefactos
markdown del Ciclo Cogito (Fase 10, tarea 10.1; spec ciclo-cogito,
Requirement 'Fases secuenciales bloqueantes').

`require()` NUNCA debe crashear con una excepcion generica ni permitir que
una fase arranque con un artefacto previo ausente o vacio (Scenario 'Fase
bloqueante sin artefacto previo').
"""

from __future__ import annotations

from pathlib import Path

import pytest

from erickfp.cogito.artifacts import ArtifactMissingError, artifact_path, require, write


def test_require_raises_cleanly_when_artifact_missing(tmp_path: Path) -> None:
    missing = tmp_path / "duda.md"

    with pytest.raises(ArtifactMissingError) as exc_info:
        require(missing, phase="divide")

    assert exc_info.value.phase == "divide"
    assert exc_info.value.path == missing


def test_require_raises_cleanly_when_artifact_is_empty(tmp_path: Path) -> None:
    empty = tmp_path / "duda.md"
    empty.write_text("   \n")

    with pytest.raises(ArtifactMissingError):
        require(empty, phase="divide")


def test_require_returns_content_when_present(tmp_path: Path) -> None:
    present = tmp_path / "duda.md"
    present.write_text("# duda.md\n\nObjetivo validado.")

    content = require(present, phase="divide")

    assert content == "# duda.md\n\nObjetivo validado."


def test_write_creates_parent_dirs_and_content(tmp_path: Path) -> None:
    target = tmp_path / "cogito" / "mi-slug" / "divide.md"

    write(target, "contenido")

    assert target.is_file()
    assert target.read_text() == "contenido"


def test_artifact_path_matches_convention(tmp_path: Path) -> None:
    root = tmp_path / ".ErickFP"

    path = artifact_path(root, "mi-slug", "ordena")

    assert path == root / "cogito" / "mi-slug" / "ordena.md"
