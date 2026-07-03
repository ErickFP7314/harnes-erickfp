"""tests/tools/test_write_file.py -- escritura real sobre tmp_path."""

import json
from pathlib import Path

from erickfp.tools.write_file import WriteFileTool


def test_execute_writes_content_to_new_file(tmp_path: Path) -> None:
    target = tmp_path / "salida.txt"

    tool = WriteFileTool()
    output, is_error = tool.execute(
        json.dumps({"path": str(target), "content": "hola mundo"})
    )

    assert is_error is False
    assert target.read_text(encoding="utf-8") == "hola mundo"
    assert str(target) in output


def test_execute_overwrites_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "existente.txt"
    target.write_text("viejo", encoding="utf-8")

    tool = WriteFileTool()
    tool.execute(json.dumps({"path": str(target), "content": "nuevo"}))

    assert target.read_text(encoding="utf-8") == "nuevo"


def test_execute_returns_is_error_true_on_invalid_json_input() -> None:
    tool = WriteFileTool()
    output, is_error = tool.execute("no es json")

    assert is_error is True


def test_execute_returns_is_error_true_on_empty_path() -> None:
    tool = WriteFileTool()
    output, is_error = tool.execute(json.dumps({"path": "", "content": "x"}))

    assert is_error is True


def test_execute_returns_is_error_true_on_unwritable_directory(tmp_path: Path) -> None:
    missing_dir_target = tmp_path / "no-existe" / "salida.txt"

    tool = WriteFileTool()
    output, is_error = tool.execute(
        json.dumps({"path": str(missing_dir_target), "content": "x"})
    )

    assert is_error is True


def test_definition_declares_path_and_content_as_required() -> None:
    tool = WriteFileTool()
    definition = tool.definition()

    assert definition.name == "write_file"
    assert set(definition.required) == {"path", "content"}
