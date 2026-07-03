"""hooks/core_guard.py -- protege `.ErickFP/core/*` de escritura (Decision 3
del design; axioma 3 de `core/Claude`; spec phase-hooks, Requirement
'Proteccion incondicional de core/*').

`PreToolUse`, SIEMPRE activo -- ninguna fase del Ciclo Cogito ni `chat` lo
desactivan (Scenario 'Bloqueo activo en toda fase y en chat': este hook ni
siquiera consulta `ctx.phase`). Deny si el `tool_input` de la tool call
apunta -- por ruta absoluta, relativa, con `..` o via symlink -- dentro de
`root/core/`. El permission gate (`agent/gate.py`) puede haber aprobado la
accion ("y" del humano); este hook corre independiente de esa decision y la
anula si detecta escritura en `core/*`: la unica via legitima para modificar
`core/*` es que el humano lo edite directamente, fuera del agente, o registre
un ADR de tipo `amendment`.
"""

from __future__ import annotations

import json
from pathlib import Path

from erickfp.api.types import HookResult
from erickfp.hooks.manager import PhaseContext

_DENY_REASON = (
    "'{path}' esta dentro de core/* -- protegido por el axioma 3 de "
    "core/Claude. Solo un humano puede modificarlo directamente o mediante "
    "un ADR de tipo amendment; ningun agente puede escribir ahi, ni siquiera "
    "con el permission gate aprobado."
)


class CoreGuardHook:
    event = "PreToolUse"

    def __init__(self, root: Path) -> None:
        self._core_dir = (root / "core").resolve()

    def run(self, ctx: PhaseContext) -> HookResult:
        path_str = _extract_path(ctx.tool_input)
        if not path_str:
            return HookResult(decision="allow")

        candidate = Path(path_str)
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate

        if _is_inside_core(candidate, self._core_dir):
            return HookResult(decision="deny", reason=_DENY_REASON.format(path=path_str))
        return HookResult(decision="allow")


def _is_inside_core(candidate: Path, core_dir: Path) -> bool:
    """Resuelve `candidate` (siga o no un symlink, exista o no todavia el
    archivo final) y compara contra `core_dir`, ya resuelto -- neutraliza
    paths equivalentes via relativos, `..` o symlinks (riesgo de fuga
    documentado en la propuesta)."""
    try:
        resolved = candidate.resolve()
    except OSError:
        return False
    return resolved == core_dir or core_dir in resolved.parents


def _extract_path(tool_input: str) -> str:
    try:
        args = json.loads(tool_input) if tool_input else {}
    except json.JSONDecodeError:
        return ""
    return args.get("path", "") if isinstance(args, dict) else ""
