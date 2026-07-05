"""tests/tools/test_registry.py -- mecanica del registry (spec tool-registry).

Estas primeras pruebas usan `FakeTool` (doble generico) porque, en este punto
del plan cartesiano (Fase 5.3), `bash.py`/`read_file.py`/`write_file.py`
todavia no existen -- la mecanica del registry (orden estable, tool nueva al
final) se valida independientemente de las 3 tools concretas del MVP. La
tarea 5.8 (mas abajo en este archivo) agrega la prueba de integracion con las
3 tools reales una vez existen.
"""

from erickfp.api.types import ToolDef
from erickfp.tools.mcp import MCPTool
from erickfp.tools.registry import ToolRegistry
from tests.support import FakeTool


def test_register_and_get_tool_by_name() -> None:
    registry = ToolRegistry()
    tool = FakeTool(name="alpha")
    registry.register(tool)

    assert registry.get("alpha") is tool


def test_get_missing_tool_returns_none() -> None:
    registry = ToolRegistry()
    assert registry.get("no-existe") is None


def test_definitions_order_is_stable_across_repeated_calls() -> None:
    registry = ToolRegistry()
    registry.register(FakeTool(name="alpha"))
    registry.register(FakeTool(name="beta"))
    registry.register(FakeTool(name="gamma"))

    first_call = [d.name for d in registry.definitions()]
    second_call = [d.name for d in registry.definitions()]

    assert first_call == ["alpha", "beta", "gamma"]
    assert first_call == second_call


def test_new_tool_is_appended_at_the_end_without_reordering() -> None:
    registry = ToolRegistry()
    registry.register(FakeTool(name="alpha"))
    registry.register(FakeTool(name="beta"))

    registry.register(FakeTool(name="delta"))

    assert [d.name for d in registry.definitions()] == ["alpha", "beta", "delta"]


def test_all_tools_returns_registered_tool_instances() -> None:
    registry = ToolRegistry()
    tool_a = FakeTool(name="alpha")
    tool_b = FakeTool(name="beta")
    registry.register(tool_a)
    registry.register(tool_b)

    assert registry.all_tools() == [tool_a, tool_b]


def test_module_level_registry_singleton_has_the_three_mvp_tools_registered() -> None:
    """Scenario 'Registro de las 3 tools del MVP' (specs/tool-registry/spec.md).

    Actualizado en Lote 5 harness-v0-2 (spec tool-registry delta, MODIFIED
    'Orden estable de definiciones'): el registry del PROCESO (singleton
    compartido) puede crecer mas alla de las 3 tools del MVP en tiempo de
    ejecucion -- `recall` se registra en el composition root (`cli.py::chat`,
    tarea 5.7) y tools MCP se sumaran igual en el Lote 8. La garantia que
    esta prueba sostiene ahora es mas precisa que una igualdad exacta: las 3
    tools locales del MVP SIEMPRE estan presentes y en su orden relativo
    original, sin importar que registros posteriores del proceso hayan
    agregado otras tools (nunca las reordenan)."""
    from erickfp.tools.registry import registry as module_registry

    names = [d.name for d in module_registry.definitions()]
    mvp_names_in_order = [name for name in names if name in {"bash", "read_file", "write_file"}]
    assert mvp_names_in_order == ["bash", "read_file", "write_file"]


def test_mcp_tool_appended_at_end_without_reordering_locals() -> None:
    """Lote 8 harness-v0-2 (spec mcp-support, Requirement 'Tool MCP
    satisface la interfaz Tool existente', Scenario 'Tool MCP descubierta
    se registra como cualquier tool local'): una `MCPTool` (Decision 8) se
    registra en el MISMO registry que las tools locales, al final, SIN
    reordenar ninguna de las ya registradas -- indistinguible en forma de
    `bash`/`read_file`/`write_file` para el registry."""
    class _FakeMCPSession:
        def call_tool(self, name: str, arguments: dict) -> tuple[str, bool]:
            return ("ok", False)

    registry = ToolRegistry()
    registry.register(FakeTool(name="bash"))
    registry.register(FakeTool(name="read_file"))
    registry.register(FakeTool(name="write_file"))

    mcp_tool = MCPTool(
        _FakeMCPSession(),
        ToolDef(
            name="git_status",
            description="tool remota MCP",
            input_schema={"type": "object", "properties": {}},
            required=[],
        ),
    )
    registry.register(mcp_tool)

    assert [d.name for d in registry.definitions()] == [
        "bash",
        "read_file",
        "write_file",
        "git_status",
    ]
    assert registry.get("git_status") is mcp_tool
