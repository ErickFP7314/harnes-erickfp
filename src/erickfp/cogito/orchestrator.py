"""cogito/orchestrator.py -- orquestador del Ciclo Cogito (Decision 3 y 4 del
design; spec ciclo-cogito).

Encadena las 4 fases (`duda -> divide -> ordena -> enumera`), invocando
`HookManager` en `PhaseStart`/`PhaseEnd` de cada una (Decision 3: hooks
inyectados; una sola instancia de `PhaseContext` vive durante toda la cadena
-- nunca se recrea entre fases -- para que `constraints` se acumule,
Requirement 'Restricciones acumulativas por fase' de la spec phase-hooks).
Cada fase valida el artefacto previo (`artifacts.require`, Requirement
'Fases secuenciales bloqueantes') antes de ejecutar el turno.

`save` de `session-summary` es explicito tras cada fase (decision registrada
en tasks.md 10.4: auto-resumen fuera de alcance por YAGNI).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from erickfp.api.types import Entry
from erickfp.cogito import artifacts
from erickfp.cogito.phases import PHASE_SEQUENCE, PREVIOUS_PHASE, ROLE_BY_PHASE, run_phase
from erickfp.hooks.manager import HookManager, PhaseContext
from erickfp.memory.store import Store
from erickfp.provider.base import Provider
from erickfp.tools.registry import ToolRegistry

Mode = Literal["interactivo", "automatico"]


class PhaseBlockedError(Exception):
    """Un hook denego el evento `PhaseStart` (p.ej. `adr_traceability` en
    `ordena` cuando `divide.md` no referencia un ADR trazable)."""

    def __init__(self, phase: str, reason: str) -> None:
        self.phase = phase
        self.reason = reason
        super().__init__(f"fase '{phase}' bloqueada por un hook: {reason}")


@dataclass
class PhaseOutcome:
    phase: str
    status: Literal["artifact", "clarification"]
    content: str
    path: Path | None


class CicloCogitoOrchestrator:
    """Coordina una ejecucion del Ciclo Cogito sobre `root` (`.ErickFP/`)."""

    def __init__(
        self,
        root: Path,
        provider: Provider,
        tools: ToolRegistry,
        hook_manager: HookManager,
        role_prompts: dict[str, str],
        store: Store | None = None,
    ) -> None:
        self._root = root
        self._provider = provider
        self._tools = tools
        self._hook_manager = hook_manager
        self._role_prompts = role_prompts
        self._store = store

    def run_phase(
        self, phase: str, slug: str, ctx: PhaseContext, objetivo: str | None = None
    ) -> PhaseOutcome:
        """Ejecuta una unica fase. `ctx` se comparte entre fases sucesivas de
        la misma cadena para que `constraints` se acumule (Decision 3)."""
        ctx.phase = phase

        previous_phase = PREVIOUS_PHASE[phase]
        if previous_phase is None:
            input_text = objetivo or ""
        else:
            previous_path = artifacts.artifact_path(self._root, slug, previous_phase)
            input_text = artifacts.require(previous_path, phase=phase)
        ctx.artifact_content = input_text

        start_result = self._hook_manager.run("PhaseStart", ctx)
        if start_result.decision == "deny":
            raise PhaseBlockedError(phase, start_result.reason)

        role = ROLE_BY_PHASE[phase]
        result = run_phase(self._provider, self._tools, phase, self._role_prompts[role], input_text)

        outcome_path: Path | None = None
        if result.status == "artifact":
            outcome_path = artifacts.artifact_path(self._root, slug, phase)
            artifacts.write(outcome_path, result.content)

        self._hook_manager.run("PhaseEnd", ctx)

        if self._store is not None:
            self._store.save(
                Entry(
                    kind="session-summary",
                    content=f"Fase '{phase}' completada para el slug '{slug}' "
                    f"(estado: {result.status}).",
                )
            )

        return PhaseOutcome(
            phase=phase, status=result.status, content=result.content, path=outcome_path
        )

    def run_chain(
        self,
        slug: str,
        objetivo: str,
        *,
        mode: Mode,
        confirm: Callable[[str], bool] | None = None,
    ) -> list[PhaseOutcome]:
        """Encadena las 4 fases desde `duda`.

        Modo 'interactivo' (Scenario 'Modo interactivo pausa entre fases'):
        tras cada fase (salvo la ultima) se llama a `confirm(siguiente_fase)`;
        si retorna `False` la cadena se detiene ahi. Modo 'automatico'
        (Scenario 'Modo automatico encadena sin pausa'): `confirm` NUNCA se
        invoca, las fases corren sin pausa mientras produzcan artefacto
        valido.

        Si `duda` responde con `status='clarification'` la cadena se detiene
        de inmediato -- no hay artefacto que alimente `divide`.
        """
        ctx = PhaseContext(phase=PHASE_SEQUENCE[0])
        outcomes: list[PhaseOutcome] = []

        for index, phase in enumerate(PHASE_SEQUENCE):
            phase_objetivo = objetivo if phase == "duda" else None
            outcome = self.run_phase(phase, slug, ctx, objetivo=phase_objetivo)
            outcomes.append(outcome)

            if outcome.status == "clarification":
                break

            is_last_phase = index == len(PHASE_SEQUENCE) - 1
            if is_last_phase:
                continue

            if mode == "interactivo":
                next_phase = PHASE_SEQUENCE[index + 1]
                should_continue = confirm(next_phase) if confirm is not None else False
                if not should_continue:
                    break

        return outcomes
