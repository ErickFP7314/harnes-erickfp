"""tests/tools/test_mcp.py -- MCPTool + config MCP (Lote 8 harness-v0-2,
design.md Decision 8, spec mcp-support).

`_FakeMCPSession` es un doble ad-hoc (duck typing estructural, Decision 5
del design, mismo patron que `_FakeRecallSource` de `tests/tools/
test_recall.py`): satisface la forma minima que `MCPTool` necesita
(`.call_tool(name, arguments)`) SIN depender del SDK real `mcp` ni de un
servidor MCP real (Project Standards: "Los tests de MCP usan un servidor
fake local/in-process (mock del cliente), no servicios remotos reales").
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import pytest

from erickfp.api.types import ToolDef
from erickfp.tools import mcp as mcp_module
from erickfp.tools.base import Tool
from erickfp.tools.mcp import MCPConfigError, MCPTool, load_config

SRC_ROOT = Path(inspect.getfile(mcp_module)).resolve().parent.parent


def _imported_top_level_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def test_only_mcp_module_imports_mcp_sdk() -> None:
    """Introspeccion de imports (Decision 8 del design, mismo patron que
    `tests/test_no_native_sdk_leak.py` con `litellm`): NINGUN archivo del
    paquete `erickfp` distinto de `tools/mcp.py` puede importar el SDK
    `mcp` -- el axioma "prohibido SDK nativo" protege la frontera
    Provider/LLM, pero MCP se aisla igual que litellm por disciplina de
    capas (una sola puerta de entrada al SDK externo)."""
    allowed = "tools/mcp.py"
    offenders: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        relative = str(path.relative_to(SRC_ROOT).as_posix())
        modules = _imported_top_level_modules(path)
        imports_mcp = any(m == "mcp" or m.startswith("mcp.") for m in modules)
        if imports_mcp and relative != allowed:
            offenders.append(relative)

    assert offenders == [], f"SDK mcp importado fuera de {allowed}: {offenders}"


def test_mcp_module_actually_imports_mcp_sdk() -> None:
    adapter_path = SRC_ROOT / "tools" / "mcp.py"
    modules = _imported_top_level_modules(adapter_path)
    assert any(m == "mcp" or m.startswith("mcp.") for m in modules)


class _FakeMCPSession:
    """NO importa el SDK `mcp` -- solo satisface `.call_tool(name, args)`."""

    def __init__(self, result: tuple[str, bool] = ("ok", False)) -> None:
        self._result = result
        self.calls: list[tuple[str, dict]] = []

    def call_tool(self, name: str, arguments: dict) -> tuple[str, bool]:
        self.calls.append((name, arguments))
        return self._result


def _make_definition(name: str = "git_status") -> ToolDef:
    return ToolDef(
        name=name,
        description="tool remota MCP de prueba",
        input_schema={"type": "object", "properties": {}},
        required=[],
    )


def test_mcp_tool_satisfies_tool_protocol_via_isinstance() -> None:
    """Scenario 'Tool MCP descubierta se registra como cualquier tool
    local': `MCPTool` es indistinguible en forma de una tool local -- pasa
    el mismo chequeo `isinstance(tool, Tool)` que usa el registry."""
    tool = MCPTool(_FakeMCPSession(), _make_definition())

    assert isinstance(tool, Tool)


def test_mcp_tool_definition_returns_injected_tooldef() -> None:
    definition = _make_definition("git_diff")
    tool = MCPTool(_FakeMCPSession(), definition)

    assert tool.definition() is definition


def test_mcp_tool_execute_delegates_to_injected_session() -> None:
    """`MCPTool.execute` parsea el `tool_input` JSON y delega en la sesion
    inyectada -- ninguna llamada de red real, solo el doble local."""
    session = _FakeMCPSession(result=("cambios: 3 archivos", False))
    tool = MCPTool(session, _make_definition("git_status"))

    result_text, is_error = tool.execute(json.dumps({"path": "."}))

    assert session.calls == [("git_status", {"path": "."})]
    assert is_error is False
    assert result_text == "cambios: 3 archivos"


def test_mcp_tool_execute_accepts_empty_input() -> None:
    session = _FakeMCPSession(result=("ok", False))
    tool = MCPTool(session, _make_definition())

    result_text, is_error = tool.execute("")

    assert session.calls == [("git_status", {})]
    assert is_error is False
    assert result_text == "ok"


def test_mcp_tool_execute_rejects_invalid_json_as_error() -> None:
    session = _FakeMCPSession()
    tool = MCPTool(session, _make_definition())

    result_text, is_error = tool.execute("{invalido")

    assert is_error is True
    assert session.calls == []


def test_mcp_tool_execute_translates_session_error_to_is_error_never_raises() -> None:
    """Contrato heredado de `bash`/`read_file`/`write_file`/`recall`: un
    fallo del servidor MCP (timeout, desconexion, tool inexistente) NUNCA
    se propaga como excepcion -- se traduce a `tool_result(is_error=True)`."""

    class _FailingSession:
        def call_tool(self, name: str, arguments: dict) -> tuple[str, bool]:
            raise RuntimeError("el servidor MCP se desconecto")

    tool = MCPTool(_FailingSession(), _make_definition())

    result_text, is_error = tool.execute("{}")

    assert is_error is True
    assert "se desconecto" in result_text


def test_non_stdio_transport_rejected_with_clear_error(tmp_path: Path) -> None:
    """Scenario 'Transporte no soportado (edge, fuera de alcance)': una
    configuracion que declara un transporte remoto (p.ej. HTTP con OAuth)
    se rechaza con un error claro, sin intentar autenticacion OAuth."""
    config_path = tmp_path / "mcp.json"
    config_path.write_text(
        json.dumps(
            {
                "servers": [
                    {
                        "name": "github",
                        "transport": "http",
                        "url": "https://api.githubcopilot.com/mcp/",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(MCPConfigError, match="http"):
        load_config(config_path)


def test_stdio_transport_config_parses_command_and_args(tmp_path: Path) -> None:
    config_path = tmp_path / "mcp.json"
    config_path.write_text(
        json.dumps(
            {
                "servers": [
                    {
                        "name": "git",
                        "transport": "stdio",
                        "command": "uvx",
                        "args": ["mcp-server-git"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    servers = load_config(config_path)

    assert len(servers) == 1
    assert servers[0].name == "git"
    assert servers[0].command == "uvx"
    assert servers[0].args == ["mcp-server-git"]


def test_transport_defaults_to_stdio_when_absent(tmp_path: Path) -> None:
    """Si `transport` no se declara, se asume `stdio` (unico soportado hoy)
    -- no se rechaza una config que simplemente omite el campo."""
    config_path = tmp_path / "mcp.json"
    config_path.write_text(
        json.dumps({"servers": [{"name": "git", "command": "uvx", "args": ["mcp-server-git"]}]}),
        encoding="utf-8",
    )

    servers = load_config(config_path)

    assert servers[0].transport == "stdio"


def test_missing_config_file_returns_empty_list_without_crashing(tmp_path: Path) -> None:
    """'Config ausente = el chat arranca igual sin tools MCP (falla limpia
    con aviso, nunca crash)': un `mcp.json` inexistente NO es un error,
    MCP es opt-in."""
    config_path = tmp_path / "no-existe" / "mcp.json"

    assert load_config(config_path) == []


def test_malformed_json_raises_clear_config_error(tmp_path: Path) -> None:
    config_path = tmp_path / "mcp.json"
    config_path.write_text("{esto no es json", encoding="utf-8")

    with pytest.raises(MCPConfigError):
        load_config(config_path)


def test_discover_tools_missing_config_returns_empty_without_warning(tmp_path: Path) -> None:
    """'Config ausente o malformada = el chat arranca igual sin tools MCP
    (falla limpia con aviso, nunca crash)': sin `.ErickFP/mcp.json`,
    `discover_tools` NUNCA lanza -- retorna [] en silencio (MCP opt-in)."""
    warnings: list[str] = []

    result = mcp_module.discover_tools(tmp_path, warn=warnings.append)

    assert result == []
    assert warnings == []


def test_discover_tools_malformed_config_warns_and_returns_empty_no_crash(tmp_path: Path) -> None:
    """Config malformada (transporte no-stdio, JSON invalido, etc.) nunca
    crashea el arranque del chat -- se avisa via el callback inyectado y
    se continua sin tools MCP."""
    config_path = tmp_path / "mcp.json"
    config_path.write_text(
        json.dumps({"servers": [{"name": "github", "transport": "http", "url": "https://x"}]}),
        encoding="utf-8",
    )
    warnings: list[str] = []

    result = mcp_module.discover_tools(tmp_path, warn=warnings.append)

    assert result == []
    assert len(warnings) == 1
    assert "http" in warnings[0]
