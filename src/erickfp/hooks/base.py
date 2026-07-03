"""hooks/base.py -- Protocol Hook (Decision 3 y 5 del design).

Cada Hook declara el evento al que reacciona (`PreToolUse` | `PostToolUse` |
`PhaseStart` | `PhaseEnd`) y retorna SIEMPRE un `HookResult` (allow/deny +
razon) -- jamas una excepcion, el mismo contrato de "nunca excepcion" que
gobierna el permission gate (Decision 3, `agent/gate.py`).
`@runtime_checkable` porque `HookManager` (hooks/manager.py) puede validar
con `isinstance()` los hooks que recibe.

El parametro `ctx` de `run()` es `PhaseContext`, definido en
`hooks/manager.py` y no aqui, para evitar un import circular real:
`manager.py` importa `Hook` desde este modulo en tiempo de ejecucion, asi que
este modulo solo referencia `PhaseContext` bajo `TYPE_CHECKING` (nunca en
runtime).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from erickfp.api.types import HookResult

if TYPE_CHECKING:
    from erickfp.hooks.manager import PhaseContext


@runtime_checkable
class Hook(Protocol):
    event: str

    def run(self, ctx: PhaseContext) -> HookResult: ...
