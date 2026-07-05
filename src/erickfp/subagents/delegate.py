"""subagents/delegate.py -- `DelegateTool` (Lote 7 harness-v0-2, tarea 7.8,
design.md "Ciclo delegate" + Decision 7 / spec subagents).

Vive en la capa `subagents` (por ENCIMA de `agent`) para resolver el ciclo
de import descrito en design.md: si `DelegateTool` viviera en `tools/`,
`tools -> agent` cerraria el ciclo `tool -> subagent -> agent -> tool`
(`DelegateTool` necesita construir/usar un `Agent`, capa `agent`, y un
registry de tools, capa `tools`). Su *definicion* esta aqui; su *registro*
ocurre en el composition root (`cli.py`), que arma un registry EXTENDIDO
anadiendo esta tool a las tools base -- `tools/` nunca importa
`agent`/`subagents` (mismo patron que `MCPTool`/`RecallTool`: definidas
abajo, inyectadas arriba).

Aprobacion (Requirement 'Aprobacion del delegate cubre las tool calls del
subagente'): esta tool es UNA tool_use mas del agente principal, por lo
tanto pasa por el permission gate normal (una sola aprobacion humana para
`delegate_research`). Las tool calls que el `Research` interno ejecuta
DENTRO de `execute()` nunca vuelven a pasar por ese gate -- usan la policy
`AllowList` auto-aprobada de `Research` (`subagents/research.py`) -- de
modo que la aprobacion externa cubre todo el trabajo interno sin preguntas
adicionales.

Errores internos (Requirement de robustez, incluye `ProviderError` si el
Provider agota sus reintentos durante la investigacion delegada) se
traducen SIEMPRE a `tool_result(is_error=True)` -- nunca se propagan como
excepcion nativa (mismo axioma que el resto de las tools del harness)."""

from __future__ import annotations

import json

from erickfp.api.types import ToolDef
from erickfp.provider.base import ProviderError
from erickfp.subagents.research import Research

_INDENT = "  ↳ "  # "  ↳ " -- indentacion visual del capitulo 11 de la guia


class DelegateTool:
    """Envuelve un `Research` (u otro subagente futuro con `.run(task) ->
    str`) como una `Tool` del registry principal."""

    def __init__(self, research: Research) -> None:
        self._research = research

    def definition(self) -> ToolDef:
        return ToolDef(
            name="delegate_research",
            description=(
                "Delega una investigacion de solo lectura (leer archivos, "
                "buscar definiciones, entender codigo existente) a un "
                "subagente especializado, EN VEZ de leer los archivos tu "
                "mismo. Prefiere esto SIEMPRE que la tarea implique varias "
                "lecturas exploratorias -- el subagente devuelve una sola "
                "sintesis en vez de ensuciar esta conversacion con cada "
                "resultado intermedio."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Tarea de investigacion a delegar, en lenguaje natural.",
                    }
                },
            },
            required=["task"],
        )

    def execute(self, input: str) -> tuple[str, bool]:
        try:
            args = json.loads(input) if input else {}
        except json.JSONDecodeError:
            return ("input invalido: se esperaba JSON con la clave 'task'", True)

        task = args.get("task", "") if isinstance(args, dict) else ""
        if not task:
            return ("task vacia", True)

        try:
            answer = self._research.run(task)
        except ProviderError as exc:
            return (f"{_INDENT}delegate_research fallo: {exc}", True)

        return (_indent(answer), False)


def _indent(text: str) -> str:
    """Prefija cada linea de `text` con la indentacion visual del
    subagente (`  ↳ `, spec subagents/design.md D7) -- distingue en la UI
    la sintesis del subagente del resto de la conversacion principal."""
    lines = text.splitlines() or [""]
    return "\n".join(f"{_INDENT}{line}" for line in lines)
