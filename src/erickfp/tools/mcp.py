"""tools/mcp.py -- MCPTool + descubrimiento de servidores MCP (Lote 8
harness-v0-2, design.md Decision 8, spec mcp-support).

UNICO modulo del paquete que importa el SDK oficial `mcp` (mismo patron que
`provider/litellm_gemini.py` con `litellm`, Decision 2 del design): el
axioma "prohibido SDK nativo" protege la frontera Provider/LLM (interfaz
`Provider`); MCP es transporte de *tools* (JSON-RPC/stdio), ortogonal al
LLM, por lo que el SDK esta permitido -- pero se aisla igual, por la misma
disciplina de "una sola puerta de entrada" a un SDK externo.

`MCPTool` envuelve cada tool remota descubierta en la interfaz `Tool`
existente (`tools/base.py`) -- no crea una ruta de ejecucion paralela al
permission gate: el agent loop la invoca exactamente igual que a
`bash`/`read_file`/`write_file`/`recall` (spec mcp-support, Requirement
'Mismo gate y policy que las tools locales').

`MCPSession` (Protocol estructural, duck typing, Decision 5 del design,
mismo patron que `RecallSource` de `tools/recall.py`) es la forma minima
que `MCPTool` necesita de una sesion MCP ya conectada: los tests inyectan
un doble local (`_FakeMCPSession`) sin depender de un servidor real ni de
la mecanica asincrona de la SDK. La conexion real (stdio, asincrona) vive
aislada en `discover_tools`/`_StdioSession`, mas abajo en este mismo
modulo -- sigue siendo el UNICO lugar que toca la SDK.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from anyio.from_thread import start_blocking_portal
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from erickfp.api.types import ToolDef

_CONFIG_FILENAME = "mcp.json"
_SUPPORTED_TRANSPORT = "stdio"


class MCPConfigError(Exception):
    """Error claro de configuracion MCP: transporte no soportado, JSON
    malformado o servidor incompleto (Scenario 'Transporte no soportado
    (edge, fuera de alcance)' de la spec). Nunca se intenta autenticacion
    OAuth ni ningun otro transporte remoto -- el llamador (composition
    root `cli.py`) decide como degradar (log + seguir sin esa tool)."""


@dataclass
class MCPServerConfig:
    """Entrada validada de `.ErickFP/mcp.json` (solo stdio soportado)."""

    name: str
    command: str
    args: list[str] = field(default_factory=list)
    transport: str = _SUPPORTED_TRANSPORT


@runtime_checkable
class MCPSession(Protocol):
    """Forma estructural minima que `MCPTool` necesita de una sesion MCP
    conectada: invocar una tool remota de forma SINCRONA desde el punto de
    vista del harness (todo el resto del proceso es sincrono, spike 2.3).
    """

    def call_tool(self, name: str, arguments: dict[str, Any]) -> tuple[str, bool]: ...


class MCPTool:
    """Adapta una tool remota MCP a la interfaz `Tool` local (Decision 8
    del design). Satisface `tools.base.Tool` por forma (definition +
    execute), indistinguible de una tool local para el registry y el agent
    loop."""

    def __init__(self, session: MCPSession, definition: ToolDef) -> None:
        self._session = session
        self._definition = definition

    def definition(self) -> ToolDef:
        return self._definition

    def execute(self, input: str) -> tuple[str, bool]:
        try:
            args = json.loads(input) if input else {}
        except json.JSONDecodeError:
            return ("input invalido: se esperaba JSON", True)
        if not isinstance(args, dict):
            return ("input invalido: se esperaba un objeto JSON", True)

        try:
            return self._session.call_tool(self._definition.name, args)
        except Exception as exc:  # noqa: BLE001 -- contrato: nunca excepcion (Decision 3)
            return (f"error MCP invocando '{self._definition.name}': {exc}", True)


def _parse_server_entry(entry: dict[str, Any]) -> MCPServerConfig:
    name = entry.get("name", "?") if isinstance(entry, dict) else "?"
    transport = entry.get("transport", _SUPPORTED_TRANSPORT) if isinstance(entry, dict) else "?"

    if transport != _SUPPORTED_TRANSPORT:
        raise MCPConfigError(
            f"servidor MCP '{name}': transporte '{transport}' no soportado "
            f"(unico soportado en esta fase: '{_SUPPORTED_TRANSPORT}'); "
            "no se intenta autenticacion OAuth ni ningun otro transporte remoto "
            "(fuera de alcance, spec mcp-support)."
        )

    command = entry.get("command", "") if isinstance(entry, dict) else ""
    if not command:
        raise MCPConfigError(f"servidor MCP '{name}': falta 'command' (transporte stdio)")

    args = entry.get("args", []) if isinstance(entry, dict) else []
    return MCPServerConfig(name=name, command=command, args=list(args), transport=transport)


def load_config(path: Path) -> list[MCPServerConfig]:
    """Lee y valida `.ErickFP/mcp.json`.

    - Archivo ausente -> lista vacia (MCP es opt-in; 'el chat arranca igual
      sin tools MCP', spec mcp-support).
    - JSON malformado o servidor con transporte no soportado -> se levanta
      `MCPConfigError` con un mensaje claro (nunca una excepcion generica
      ni un crash del proceso -- el llamador decide como degradar).
    """
    if not path.exists():
        return []

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MCPConfigError(f"{path}: JSON invalido ({exc})") from exc

    servers = raw.get("servers", []) if isinstance(raw, dict) else []
    if not isinstance(servers, list):
        raise MCPConfigError(f"{path}: 'servers' debe ser una lista")

    return [_parse_server_entry(entry) for entry in servers]


def default_config_path(root: Path) -> Path:
    """`root` es el directorio `.ErickFP/` del proyecto (mismo `root` que
    `SqliteStore`/`CoreGuardHook`) -- la config MCP vive en
    `.ErickFP/mcp.json` (design.md Decision 8, confirmado Lote 8)."""
    return root / _CONFIG_FILENAME


class _StdioSession:
    """Puente sincrono sobre una `ClientSession` MCP conectada por stdio.

    Vive dentro del `BlockingPortal` abierto por `discover_tools`: el
    subprocess permanece activo mientras el harness corre (analogo a
    `defer client.Close()` del capitulo 14 de la guia byo-coding-agent) --
    cada `call_tool` sincrono ejecuta la coroutine real via
    `portal.call(...)`.
    """

    def __init__(self, portal: Any, session: ClientSession) -> None:
        self._portal = portal
        self._session = session

    def call_tool(self, name: str, arguments: dict[str, Any]) -> tuple[str, bool]:
        result = self._portal.call(self._session.call_tool, name, arguments)
        text = "\n".join(
            block.text for block in result.content if getattr(block, "type", "") == "text"
        )
        return (text, bool(result.isError))


def discover_tools(root: Path, warn: Any = None) -> list[MCPTool]:
    """Descubre y envuelve las tools de todos los servidores MCP
    declarados en `.ErickFP/mcp.json` (composition root: `cli.py`).

    Falla limpia en cada nivel, nunca crashea el arranque del chat (spec
    mcp-support): config ausente -> [] en silencio (MCP es opt-in, ni
    siquiera se avisa); config malformada o un servidor individual que no
    arranca (binario ausente, crash al iniciar) -> se omite y se invoca
    `warn(mensaje)` si se inyecto un callback (p.ej. `console.print` desde
    `cli.py`), pero el chat sigue arrancando con las tools locales (mismo
    patron 'skip the server, keep going' del capitulo 14 de la guia
    byo-coding-agent). Retorna SIEMPRE una lista (jamas lanza).
    """

    def _warn(message: str) -> None:
        if warn is not None:
            warn(message)

    try:
        servers = load_config(default_config_path(root))
    except MCPConfigError as exc:
        _warn(f"mcp: config invalida, se omiten tools MCP: {exc}")
        return []

    if not servers:
        return []

    tools: list[MCPTool] = []
    for server in servers:
        server_tools = _discover_server_tools(server, _warn)
        tools.extend(server_tools)
    return tools


def _discover_server_tools(server: MCPServerConfig, warn: Any = None) -> list[MCPTool]:
    try:
        with start_blocking_portal() as portal:
            read, write = portal.wrap_async_context_manager(
                stdio_client(StdioServerParameters(command=server.command, args=server.args))
            ).__enter__()
            session = portal.wrap_async_context_manager(ClientSession(read, write)).__enter__()
            portal.call(session.initialize)
            listed = portal.call(session.list_tools)

            bridge = _StdioSession(portal, session)
            return [
                MCPTool(
                    bridge,
                    ToolDef(
                        name=remote_tool.name,
                        description=remote_tool.description or "",
                        input_schema=remote_tool.inputSchema
                        or {"type": "object", "properties": {}},
                        required=list((remote_tool.inputSchema or {}).get("required", [])),
                    ),
                )
                for remote_tool in listed.tools
            ]
    except Exception as exc:  # noqa: BLE001 -- 'skip the server, keep going' (cap.14)
        # un servidor que no arranca (binario ausente, crash temprano) no
        # debe tumbar el resto del descubrimiento ni el arranque del chat.
        if warn is not None:
            warn(f"mcp: servidor '{server.name}' no disponible, se omite ({exc})")
        return []
