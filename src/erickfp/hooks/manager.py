"""hooks/manager.py -- HookManager inyectado + PhaseContext (Decision 3 del
design).

NO es un registry global a nivel de modulo, a diferencia deliberada de
`tools/registry.py` (contraste documentado en Decision 3): el orquestador
del Ciclo Cogito construye una instancia por ejecucion e inyecta los hooks
activos. Esto da aislamiento total en tests (cada test arranca con un
manager fresco) y refleja que los hooks portan estado ACUMULATIVO por fase,
a diferencia de las tools (stateless).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from erickfp.api.types import HookResult
from erickfp.hooks.base import Hook


@dataclass
class PhaseContext:
    """Estado mutable compartido durante una ejecucion del Ciclo Cogito.

    El orquestador crea UNA instancia por ciclo completo (no una por fase) y
    la reutiliza en cada `PhaseStart` sucesivo -- por eso `constraints` se
    ACUMULA (Requirement 'Restricciones acumulativas por fase', spec
    phase-hooks): ni los hooks ni el manager limpian esta lista entre fases.

    `tool_name`/`tool_input` se completan antes de invocar el evento
    `PreToolUse` (ver `agent/loop.py`); `artifact_content` lleva el texto del
    artefacto de la fase previa para validaciones en `PhaseStart` (p.ej.
    `adr_traceability` sobre `divide.md` al iniciar `ordena`).
    """

    phase: str
    tool_name: str = ""
    tool_input: str = ""
    artifact_content: str = ""
    constraints: list[str] = field(default_factory=list)


class HookManager:
    """Ejecuta, para un evento dado, todos los hooks registrados que
    escuchan ese evento, en orden de registro. El primer `deny` corta la
    cadena (un solo hook que bloquee basta para impedir la accion); si
    ninguno deniega, el evento se resuelve como `allow`.
    """

    def __init__(self, hooks: list[Hook] | None = None) -> None:
        self._hooks: list[Hook] = list(hooks or [])

    def register(self, hook: Hook) -> None:
        self._hooks.append(hook)

    def run(self, event: str, ctx: PhaseContext) -> HookResult:
        for hook in self._hooks:
            if hook.event != event:
                continue
            result = hook.run(ctx)
            if result.decision == "deny":
                return result
        return HookResult(decision="allow")
