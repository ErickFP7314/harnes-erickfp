"""api/types.py -- tipos propios sin dependencias externas (Decision 1 y 5 del design).

Este modulo es la base cartesiana de todo el paquete: NO debe importar nada
fuera de la stdlib. `Provider`, `Tool`, `Store` y `Hook` (Decision 5) dependen
de estos tipos, nunca al reves (regla de dependencia de Decision 1: api ->
nada).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["user", "assistant"]
BlockType = Literal["text", "tool_use", "tool_result"]


@dataclass
class Block:
    """Unidad minima de contenido de un turno.

    `provider_metadata` es un dict opaco (Decision 2): el adapter LiteLLM lo
    llena y lo relee para preservar thought signatures de Gemini 3 entre
    turnos; el agent loop y el resto del harness nunca lo inspeccionan.
    """

    type: BlockType
    text: str = ""
    tool_use_id: str = ""
    tool_name: str = ""
    tool_input: str = ""
    tool_result: str = ""
    is_error: bool = False
    provider_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Message:
    role: Role
    content: list[Block]


@dataclass
class ToolDef:
    name: str
    description: str
    input_schema: dict[str, Any]
    required: list[str] = field(default_factory=list)


@dataclass
class Response:
    content: list[Block]
    stop_reason: str


@dataclass
class HookResult:
    """Resultado de un Hook (Decision 3): nunca excepcion, siempre allow/deny + razon."""

    decision: Literal["allow", "deny"]
    reason: str = ""


@dataclass
class Entry:
    """Registro del Memory Store (Decision 6). `id` es None hasta persistirse."""

    kind: Literal["fact", "decision", "session-summary", "preference"]
    content: str
    ts: str = ""
    tags: list[str] = field(default_factory=list)
    id: int | None = None
