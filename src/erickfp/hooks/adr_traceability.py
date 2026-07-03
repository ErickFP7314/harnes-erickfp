"""hooks/adr_traceability.py -- valida trazabilidad ADR antes de sintesis
(Decision 3 y 7 del design; spec phase-hooks, Requirement 'Trazabilidad ADR
antes de sintesis').

`PhaseStart` de la fase `ordena`: el artefacto de entrada (`divide.md`) debe
referenciar, via `adr_ref` en su frontmatter, un ADR que alcance -- por DFS a
traves de `parents` -- un nodo raiz del grafo (`hooks/adr_graph.py`). Fuera
de `ordena` este hook no valida nada (otras fases no producen un artefacto
con `adr_ref`).
"""

from __future__ import annotations

from pathlib import Path

from erickfp.api.types import HookResult
from erickfp.hooks.adr_graph import load_adr_graph, parse_frontmatter, validate_traceability
from erickfp.hooks.manager import PhaseContext

_ORDENA_PHASE = "ordena"
_MISSING_REF_REASON = (
    "el artefacto de 'divide' no referencia un ADR padre (falta 'adr_ref' "
    "en su frontmatter) -- 'ordena' no puede sintetizar sin trazabilidad."
)


class AdrTraceabilityHook:
    event = "PhaseStart"

    def __init__(self, root: Path) -> None:
        self._adr_dir = root / "adr"

    def run(self, ctx: PhaseContext) -> HookResult:
        if ctx.phase != _ORDENA_PHASE:
            return HookResult(decision="allow")

        adr_ref = _extract_adr_ref(ctx.artifact_content)
        if adr_ref is None:
            return HookResult(decision="deny", reason=_MISSING_REF_REASON)

        graph = load_adr_graph(self._adr_dir)
        return validate_traceability(adr_ref, graph)


def _extract_adr_ref(artifact_content: str) -> int | None:
    frontmatter = parse_frontmatter(artifact_content)
    if frontmatter is None or "adr_ref" not in frontmatter:
        return None
    try:
        return int(frontmatter["adr_ref"])
    except (TypeError, ValueError):
        return None
