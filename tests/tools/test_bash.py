"""tests/tools/test_bash.py -- BashTool.execute() retorna (stdout, is_error)."""

import json

from erickfp.tools.bash import BashTool


def test_execute_returns_output_and_is_error_false_on_success() -> None:
    tool = BashTool()
    output, is_error = tool.execute(json.dumps({"command": "echo hola"}))

    assert "hola" in output
    assert is_error is False


def test_execute_returns_is_error_true_on_nonzero_exit_code() -> None:
    tool = BashTool()
    output, is_error = tool.execute(json.dumps({"command": "exit 1"}))

    assert is_error is True


def test_execute_returns_is_error_true_on_invalid_json_input() -> None:
    tool = BashTool()
    output, is_error = tool.execute("no es json")

    assert is_error is True
    assert "invalido" in output.lower() or "json" in output.lower()


def test_execute_returns_is_error_true_on_empty_command() -> None:
    tool = BashTool()
    output, is_error = tool.execute(json.dumps({"command": ""}))

    assert is_error is True


def test_definition_declares_command_as_required() -> None:
    tool = BashTool()
    definition = tool.definition()

    assert definition.name == "bash"
    assert "command" in definition.required
