"""tests/tools/test_read_file.py -- lectura real sobre tmp_path."""

import json
from pathlib import Path

from erickfp.tools.read_file import ReadFileTool


def test_execute_reads_existing_file_content(tmp_path: Path) -> None:
    target = tmp_path / "hola.txt"
    target.write_text("contenido real", encoding="utf-8")

    tool = ReadFileTool()
    output, is_error = tool.execute(json.dumps({"path": str(target)}))

    assert output == "contenido real"
    assert is_error is False


def test_execute_returns_is_error_true_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "no-existe.txt"

    tool = ReadFileTool()
    output, is_error = tool.execute(json.dumps({"path": str(missing)}))

    assert is_error is True


def test_execute_returns_is_error_true_on_invalid_json_input() -> None:
    tool = ReadFileTool()
    output, is_error = tool.execute("no es json")

    assert is_error is True


def test_execute_returns_is_error_true_on_empty_path() -> None:
    tool = ReadFileTool()
    output, is_error = tool.execute(json.dumps({"path": ""}))

    assert is_error is True


def test_definition_declares_path_as_required() -> None:
    tool = ReadFileTool()
    definition = tool.definition()

    assert definition.name == "read_file"
    assert "path" in definition.required
