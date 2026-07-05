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
de la Fase 6.

Permission policy (Lote 4 harness-v0-2, Decision 2 del design; spec
permission-policy): `policy` es OPCIONAL (default `None`, mismo patron que
`hook_manager`/`ctx`/`tracker`).

Compaction (Lote 6 harness-v0-2, tarea 6.9, design.md Decision 5; spec
compaction): `compaction` es OPCIONAL (default `None`, mismo patron que
`tracker`/`policy`).

Extraccion de `Agent` (Lote 7 harness-v0-2, tareas 7.1-7.2, design.md
Decision 7 / spec subagents): TODA la logica del bucle (antes escrita
directamente en esta funcion) ahora vive en `agent/agent.py::Agent` --
`Agent` es instanciable multiples veces con estado independiente, lo que
habilita subagentes (`subagents/research.py`). Esta funcion PRESERVA su
firma exacta de los Lotes 1-6 (mismos parametros, mismo orden, mismos
defaults) y queda como un wrapper delgado: construye un `Agent` de un solo
uso por llamada, inyectando exactamente los mismos argumentos que antes se
usaban sueltos, y retorna `agent.run_turn(messages)`. Ninguna prueba
existente que invoca la funcion libre se rompe (retrocompatibilidad
bit-a-bit) -- ver `tests/agent/test_agent_class.py::
test_free_run_turn_wraps_agent_class_same_signature`.
"""

from __future__ import annotations

from erickfp.agent.agent import Agent
from erickfp.agent.policy import PermissionPolicy
from erickfp.agent.tokens import TokenTracker
from erickfp.api.types import Message, ToolDef
from erickfp.compaction.base import CompactionStrategy
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
    compaction: CompactionStrategy | None = None,
) -> list[Message]:
    """Ejecuta un turno completo hasta `stop_reason != "tool_use"`.

    Wrapper delgado (Lote 7) sobre `agent.agent.Agent`: construye una
    instancia de un solo uso con exactamente los parametros recibidos y
    delega en `Agent.run_turn(messages)`. Ver el docstring de `Agent` para
    el detalle de cada parametro opcional.
    """
    agent = Agent(
        provider,
        tools,
        tool_defs,
        hook_manager=hook_manager,
        ctx=ctx,
        tracker=tracker,
        policy=policy,
        compaction=compaction,
    )
    return agent.run_turn(messages)
