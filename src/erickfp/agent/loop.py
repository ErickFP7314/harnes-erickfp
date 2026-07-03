"""agent/loop.py -- agent loop (spec agent-loop, Requirement 'Loop REPL con
Provider').

Encadena `Provider.send()` hasta que `stop_reason != "tool_use"`. Cada
`tool_use` de la respuesta pasa OBLIGATORIAMENTE por `run_tool_with_gate`
(el permission gate) antes de ejecutarse -- no existe una ruta alternativa
que invoque `tool.execute()` directamente (Scenario 'Ninguna tool se ejecuta
sin pasar por el gate').

Contrato heredado de la guia byo-coding-agent: el turno del asistente se
anexa a `messages` ANTES de decidir si el loop continua; cada `tool_result`
lleva el `tool_use_id` correcto; los errores de tool (deny o fallo real)
viajan como texto en el propio `tool_result`, nunca como excepcion.

La integracion de hooks (PreToolUse/PostToolUse, Fase 8) se añadira en una
fase posterior extendiendo `run_turn` -- a la fecha de esta fase (6) el loop
solo conoce Provider + gate + tool registry (regla de dependencia de
Decision 1: `agent` -> `api`, `provider`, `tools`; nunca -> `hooks`. Los
hooks se inyectaran en el orquestador del Ciclo Cogito, Fase 10, si el
diseño lo requiere para el chat general).
"""

from __future__ import annotations

from erickfp.agent.gate import run_tool_with_gate
from erickfp.api.types import Block, Message, ToolDef
from erickfp.provider.base import Provider
from erickfp.tools.registry import ToolRegistry


def run_turn(
    provider: Provider,
    tools: ToolRegistry,
    messages: list[Message],
    tool_defs: list[ToolDef],
) -> list[Message]:
    """Ejecuta un turno completo hasta `stop_reason != "tool_use"`.

    Retorna la lista de mensajes actualizada (incluye el/los turnos del
    asistente y, si hubo `tool_use`, los `tool_result` correspondientes).
    No muta la lista `messages` recibida -- siempre retorna una nueva.
    """
    current_messages = list(messages)

    while True:
        response = provider.send(current_messages, tool_defs)
        current_messages = [
            *current_messages,
            Message(role="assistant", content=response.content),
        ]

        if response.stop_reason != "tool_use":
            return current_messages

        result_blocks: list[Block] = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            tool = tools.get(block.tool_name)
            if tool is None:
                result_blocks.append(
                    Block(
                        type="tool_result",
                        tool_use_id=block.tool_use_id,
                        tool_result=f"tool desconocida en el registry: {block.tool_name}",
                        is_error=True,
                    )
                )
                continue
            result_blocks.append(run_tool_with_gate(tool, block))

        current_messages = [*current_messages, Message(role="user", content=result_blocks)]
