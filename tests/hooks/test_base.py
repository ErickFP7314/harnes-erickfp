"""tests/hooks/test_base.py -- Protocol Hook (Fase 8, tarea 8.1).

`FakeHook` satisface el Protocol estructural `Hook` sin heredar de el
(Decision 5 del design). El parametro `ctx` de `run()` se tipa laxo aqui a
proposito: `PhaseContext` vive en `hooks/manager.py` (tarea 8.4, aun no
existe en este punto del ciclo RED->GREEN), y `isinstance()` sobre un
Protocol `@runtime_checkable` solo verifica la presencia de los metodos, no
sus firmas -- no hace falta importar `PhaseContext` para esta prueba.
"""

from __future__ import annotations

from erickfp.api.types import HookResult
from erickfp.hooks.base import Hook


class FakeHook:
    event = "PreToolUse"

    def run(self, ctx: object) -> HookResult:
        return HookResult(decision="allow")


def test_fake_hook_satisfies_hook_protocol() -> None:
    hook: Hook = FakeHook()
    assert isinstance(hook, Hook)
    assert hook.event == "PreToolUse"
    assert hook.run(object()) == HookResult(decision="allow")


def test_hook_result_allow_and_deny_construction() -> None:
    allow = HookResult(decision="allow")
    deny = HookResult(decision="deny", reason="motivo del bloqueo")

    assert allow.decision == "allow"
    assert allow.reason == ""
    assert deny.decision == "deny"
    assert deny.reason == "motivo del bloqueo"
