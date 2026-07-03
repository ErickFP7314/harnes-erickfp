"""tests/hooks/test_manager.py -- HookManager + PhaseContext (Fase 8,
tareas 8.3-8.4). Spec phase-hooks, Requirement 'Restricciones acumulativas
por fase'.
"""

from __future__ import annotations

from erickfp.api.types import HookResult
from erickfp.hooks.manager import HookManager, PhaseContext


class _AddConstraintHook:
    """Hook de prueba: cada `PhaseStart` anexa su nombre a `ctx.constraints`."""

    event = "PhaseStart"

    def __init__(self, name: str) -> None:
        self._name = name

    def run(self, ctx: PhaseContext) -> HookResult:
        ctx.constraints.append(self._name)
        return HookResult(decision="allow")


def test_constraints_accumulate_across_phase_starts() -> None:
    """Scenario 'Acumulacion entre divide y ordena': el manager reutiliza el
    mismo `PhaseContext` entre fases -- ninguna llamada a `run()` limpia
    `ctx.constraints`, por lo que las restricciones de una fase anterior
    siguen presentes cuando se suma una nueva en la fase siguiente."""
    ctx = PhaseContext(phase="divide")
    manager = HookManager([_AddConstraintHook("core_guard")])

    manager.run("PhaseStart", ctx)
    assert ctx.constraints == ["core_guard"]

    ctx.phase = "ordena"
    manager.register(_AddConstraintHook("adr_traceability"))
    manager.run("PhaseStart", ctx)

    assert ctx.constraints == ["core_guard", "core_guard", "adr_traceability"]
    assert "core_guard" in ctx.constraints  # sigue activo, nadie lo limpio


def test_first_deny_short_circuits_remaining_hooks() -> None:
    """Un solo `deny` basta para bloquear el evento -- los hooks restantes
    del mismo evento no se ejecutan (Requirement 'Proteccion incondicional
    de core/*': ningun hook posterior puede relajar el bloqueo)."""
    calls: list[str] = []

    class AllowHook:
        event = "PreToolUse"

        def run(self, ctx: PhaseContext) -> HookResult:
            calls.append("allow-hook")
            return HookResult(decision="allow")

    class DenyHook:
        event = "PreToolUse"

        def run(self, ctx: PhaseContext) -> HookResult:
            calls.append("deny-hook")
            return HookResult(decision="deny", reason="bloqueado")

    class NeverCalledHook:
        event = "PreToolUse"

        def run(self, ctx: PhaseContext) -> HookResult:
            calls.append("never")
            return HookResult(decision="allow")

    manager = HookManager([AllowHook(), DenyHook(), NeverCalledHook()])
    result = manager.run("PreToolUse", PhaseContext(phase="ordena"))

    assert result.decision == "deny"
    assert result.reason == "bloqueado"
    assert calls == ["allow-hook", "deny-hook"]


def test_hooks_for_other_events_are_not_invoked() -> None:
    """Un hook `PhaseStart` no se ejecuta cuando el manager corre un evento
    `PreToolUse`, y viceversa."""
    calls: list[str] = []

    class PhaseStartHook:
        event = "PhaseStart"

        def run(self, ctx: PhaseContext) -> HookResult:
            calls.append("phase-start")
            return HookResult(decision="allow")

    manager = HookManager([PhaseStartHook()])
    manager.run("PreToolUse", PhaseContext(phase="ordena"))

    assert calls == []
