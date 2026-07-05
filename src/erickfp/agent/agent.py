"""agent/agent.py -- clase `Agent` reutilizable (Lote 7 harness-v0-2, tareas
7.1-7.2, design.md Decision 7 / spec subagents, Requirement 'Agent
reutilizable y subagente Research read-only').

Extrae a una clase instanciable el estado y el bucle que antes vivian
sueltos como argumentos posicionales/keyword de la funcion libre
`agent/loop.py::run_turn`: dos "agentes" (el principal del REPL y un
subagente delegado, Lote 7) necesitan cada uno su propio estado
(`provider`/`tools`/`tool_defs`/`hook_manager`/`ctx`/`tracker`/`policy`/
`compaction`) sin compartir variables de modulo -- mismo refactor que el
capitulo 11 de la guia byo-coding-agent (`internal/agent/agent.go::Agent`,
`Send(ctx, prompt)`).

`agent/loop.py::run_turn` (funcion libre) PRESERVA su firma exacta y ahora
es un wrapper delgado: construye un `Agent` de un solo uso por llamada y
corre `agent.run_turn(messages)` -- ningun test de los Lotes 1-6 que invoca
la funcion libre se rompe (retrocompatibilidad bit-a-bit, tarea 7.1).

`max_turns` (Lote 7, nuevo -- sin equivalente en los Lotes 1-6) es OPCIONAL
(default `None` = sin limite, preserva bit-a-bit el `while True` de antes):
el subagente `Research` (`subagents/research.py`) SI lo fija a un valor
acotado (mismo patron que `MaxTurns=10` del subagente Research en la guia
byo-coding-agent, capitulo 11) -- una tarea delegada nunca debe poder
iterar indefinidamente sin que el agente principal recupere el control.
"""

from __future__ import annotations

from erickfp.agent.gate import run_tool_with_gate
from erickfp.agent.policy import PermissionPolicy
from erickfp.agent.tokens import TokenTracker
from erickfp.api.types import Block, Message, ToolDef
from erickfp.compaction.base import CompactionStrategy
from erickfp.hooks.manager import HookManager, PhaseContext
from erickfp.provider.base import Provider
from erickfp.tools.registry import ToolRegistry


class Agent:
    """Agente reutilizable: un turno completo hasta `stop_reason !=
    "tool_use"` (o hasta agotar `max_turns`, si esta acotado).

    Cada instancia es independiente -- dos `Agent` distintos (p.ej. el
    principal y un `Research` delegado) no comparten historial ni estado
    alguno, solo si se les inyecta explicitamente el mismo objeto (p.ej. el
    mismo `HookManager` para que `core_guard` proteja `core/*` tambien
    dentro de un subagente, Requirement 'core_guard sigue activo dentro del
    subagente').
    """

    def __init__(
        self,
        provider: Provider,
        tools: ToolRegistry,
        tool_defs: list[ToolDef],
        hook_manager: HookManager | None = None,
        ctx: PhaseContext | None = None,
        tracker: TokenTracker | None = None,
        policy: PermissionPolicy | None = None,
        compaction: CompactionStrategy | None = None,
        max_turns: int | None = None,
    ) -> None:
        self.provider = provider
        self.tools = tools
        self.tool_defs = tool_defs
        self.hook_manager = hook_manager
        self.ctx = ctx
        self.tracker = tracker
        self.policy = policy
        self.compaction = compaction
        self.max_turns = max_turns

    def run_turn(self, messages: list[Message]) -> list[Message]:
        """Logica identica, mensaje por mensaje, a la que tenia la funcion
        libre `agent.loop.run_turn` antes del Lote 7 -- movida aqui sin
        cambios de comportamiento salvo el limite opcional de `max_turns`.

        Retorna la lista de mensajes actualizada; no muta la lista
        `messages` recibida -- siempre retorna una nueva.
        """
        current_messages = list(messages)
        if self.compaction is not None:
            current_messages = self.compaction.compact(current_messages)

        turns_run = 0
        while True:
            if self.max_turns is not None and turns_run >= self.max_turns:
                return current_messages
            turns_run += 1

            response = self.provider.send(current_messages, self.tool_defs)
            if self.tracker is not None:
                self.tracker.add(response.usage)
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
                tool = self.tools.get(block.tool_name)
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

                if self.hook_manager is not None and self.ctx is not None:
                    self.ctx.tool_name = block.tool_name
                    self.ctx.tool_input = block.tool_input
                    pre_result = self.hook_manager.run("PreToolUse", self.ctx)
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

                if self.policy is not None:
                    result_blocks.append(run_tool_with_gate(tool, block, self.policy))
                else:
                    result_blocks.append(run_tool_with_gate(tool, block))

                if self.hook_manager is not None and self.ctx is not None:
                    self.hook_manager.run("PostToolUse", self.ctx)

            current_messages = [*current_messages, Message(role="user", content=result_blocks)]
