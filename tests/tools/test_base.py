"""tests/tools/test_base.py -- FakeTool satisface el Protocol Tool (runtime_checkable).

Decision 5 del design: `Tool` es `@runtime_checkable` porque el registry
necesita `isinstance()` para validar un objeto antes de aceptarlo.
"""

from erickfp.tools.base import Tool
from tests.support import FakeTool


def test_fake_tool_satisfies_tool_protocol_via_isinstance() -> None:
    tool = FakeTool()
    assert isinstance(tool, Tool)


def test_fake_tool_definition_returns_tooldef_with_name() -> None:
    tool = FakeTool(name="my_tool")
    definition = tool.definition()
    assert definition.name == "my_tool"


def test_fake_tool_execute_returns_result_and_is_error_tuple() -> None:
    tool = FakeTool()
    result, is_error = tool.execute("payload")
    assert result == "executed:payload"
    assert is_error is False


def test_object_missing_execute_does_not_satisfy_tool_protocol() -> None:
    class NotATool:
        def definition(self) -> None:  # pragma: no cover - solo forma
            return None

    assert not isinstance(NotATool(), Tool)
