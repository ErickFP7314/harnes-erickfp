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

Integracion de hooks (Fase 8, EXTIENDE esta funcion sin reescribirla, tal
como anticipaba el docstring de la Fase 6): `hook_manager`/`ctx` son
parametros OPCIONALES (default `None`) para no romper retrocompatibilidad
con el llamador de la Fase 7 (`cli.py::run_chat_session`) ni con las pruebas
de la Fase 6. Cuando se inyectan, cada `tool_use` dispara `PreToolUse` ANTES
de llegar al gate -- un `deny` (p.ej. `core_guard` protegiendo `core/*`)
bloquea la tool sin que el gate sea siquiera consultado (Requirement
'Proteccion incondicional de core/*': el bloqueo no depende de la decision
del humano). Si el hook aprueba, la tool sigue su camino normal hacia el
gate; despues de resolverse (con o sin gate) se dispara `PostToolUse`.

Permission policy (Lote 4 harness-v0-2, Decision 2 del design; spec
permission-policy): `policy` es OPCIONAL (default `None`, mismo patron que
`hook_manager`/`ctx`/`tracker`) y se threadea SOLO cuando se inyecta
explicitamente -- si `policy is None` la llamada a `run_tool_with_gate`
conserva su firma de 2 argumentos identica a los Lotes 1-3 (retrocompatibi-
lidad bit-a-bit con toda prueba que monkeypatchea esa funcion). El orden es
inamovible: `PreToolUse`/`core_guard` SIEMPRE se evalua antes de siquiera
llegar al gate -- ninguna `PermissionPolicy` (incluidas `AllowList`/
`AskOnce`) puede aprobar automaticamente lo que el core_guard ya denego
(Requirement 'core_guard prevalece sobre cualquier policy').
"""

from __future__ import annotations

from erickfp.agent.gate import run_tool_with_gate
from erickfp.agent.policy import PermissionPolicy
from erickfp.agent.tokens import TokenTracker
from erickfp.api.types import Block, Message, ToolDef
from erickfp.hooks.manager import HookManager, PhaseContext
from erickfp.provider.base import Provider
from erickfp.tools.registry import ToolRegistry


def run_turn(
    provider: Provider,
    tools: ToolRegistry,
    messages: list[Message],
    tool_defs: list[ToolDef],
    hook_manager: HookManager | None = None,
    ctx: PhaseContext | None = None,
    tracker: TokenTracker | None = None,
    policy: PermissionPolicy | None = None,
) -> list[Message]:
    """Ejecuta un turno completo hasta `stop_reason != "tool_use"`.

    Retorna la lista de mensajes actualizada (incluye el/los turnos del
    asistente y, si hubo `tool_use`, los `tool_result` correspondientes).
    No muta la lista `messages` recibida -- siempre retorna una nueva.

    `tracker` (Lote 3 harness-v0-2, tarea 3.15, design.md Decision 6) es
    OPCIONAL (default `None`, igual patron que `hook_manager`/`ctx`): si se
    inyecta, cada respuesta real del Provider dentro del turno reporta su
    `usage` -- incluye llamadas intermedias con `tool_use`, no solo la final.
    """
    current_messages = list(messages)

    while True:
        response = provider.send(current_messages, tool_defs)
        if tracker is not None:
            tracker.add(response.usage)
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

            if hook_manager is not None and ctx is not None:
                ctx.tool_name = block.tool_name
                ctx.tool_input = block.tool_input
                pre_result = hook_manager.run("PreToolUse", ctx)
                if pre_result.decision == "deny":
                    result_blocks.append(
                        Block(
                            type="tool_result",
                            tool_use_id=block.tool_use_id,
                            tool_result=pre_result.reason,
                            is_error=True,
                        )
                    )
                    continue

            if policy is not None:
                result_blocks.append(run_tool_with_gate(tool, block, policy))
            else:
                result_blocks.append(run_tool_with_gate(tool, block))

            if hook_manager is not None and ctx is not None:
                hook_manager.run("PostToolUse", ctx)

        current_messages = [*current_messages, Message(role="user", content=result_blocks)]
