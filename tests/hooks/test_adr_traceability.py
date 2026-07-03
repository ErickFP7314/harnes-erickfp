"""tests/hooks/test_adr_traceability.py -- hook adr_traceability (Fase 8,
tareas 8.9-8.10). Spec phase-hooks, Requirement 'Trazabilidad ADR antes de
sintesis': el artefacto de entrada de `ordena` (`divide.md`) debe referenciar
(via `adr_ref` en su frontmatter) un nodo del grafo ADR que alcance, por DFS,
un nodo raiz (`parents: []`).
"""

from __future__ import annotations

from pathlib import Path

from erickfp.hooks.adr_traceability import AdrTraceabilityHook
from erickfp.hooks.manager import PhaseContext

_ROOT_ADR = """---
id: 1
titulo: "Axioma raiz"
parents: []
estado: aceptada
trade_off: "ninguno"
---
Contenido del ADR raiz.
"""

_CHILD_ADR = """---
id: 2
titulo: "Decision derivada"
parents: [1]
estado: aceptada
trade_off: "overhead menor"
---
Contenido del ADR hijo.
"""


def _divide_artifact(adr_ref: int | None) -> str:
    if adr_ref is None:
        return "---\ntitulo: divide\n---\nSin referencia a ningun ADR.\n"
    return f"---\ntitulo: divide\nadr_ref: {adr_ref}\n---\nContenido de divide.\n"


def _make_root_with_adrs(tmp_path: Path, *adr_contents: str) -> Path:
    root = tmp_path / ".ErickFP"
    adr_dir = root / "adr"
    adr_dir.mkdir(parents=True)
    for index, content in enumerate(adr_contents, start=1):
        (adr_dir / f"{index:03d}-adr.md").write_text(content)
    return root


def test_blocks_when_divide_artifact_has_no_adr_reference(tmp_path: Path) -> None:
    """Scenario 'Artefacto sin referencia ADR'."""
    root = _make_root_with_adrs(tmp_path, _ROOT_ADR)
    hook = AdrTraceabilityHook(root=root)
    ctx = PhaseContext(phase="ordena", artifact_content=_divide_artifact(None))

    result = hook.run(ctx)

    assert result.decision == "deny"
    assert "adr_ref" in result.reason


def test_blocks_when_referenced_adr_id_does_not_exist(tmp_path: Path) -> None:
    root = _make_root_with_adrs(tmp_path, _ROOT_ADR)
    hook = AdrTraceabilityHook(root=root)
    ctx = PhaseContext(phase="ordena", artifact_content=_divide_artifact(99))

    result = hook.run(ctx)

    assert result.decision == "deny"
    assert "99" in result.reason


def test_blocks_when_cycle_detected(tmp_path: Path) -> None:
    cyclic_a = "---\nid: 1\ntitulo: a\nparents: [2]\nestado: aceptada\ntrade_off: x\n---\n"
    cyclic_b = "---\nid: 2\ntitulo: b\nparents: [1]\nestado: aceptada\ntrade_off: x\n---\n"
    root = _make_root_with_adrs(tmp_path, cyclic_a, cyclic_b)
    hook = AdrTraceabilityHook(root=root)
    ctx = PhaseContext(phase="ordena", artifact_content=_divide_artifact(1))

    result = hook.run(ctx)

    assert result.decision == "deny"
    assert "ciclo" in result.reason.lower()


def test_allows_when_dfs_reaches_root(tmp_path: Path) -> None:
    root = _make_root_with_adrs(tmp_path, _ROOT_ADR, _CHILD_ADR)
    hook = AdrTraceabilityHook(root=root)
    ctx = PhaseContext(phase="ordena", artifact_content=_divide_artifact(2))

    result = hook.run(ctx)

    assert result.decision == "allow"


def test_ignored_outside_ordena_phase(tmp_path: Path) -> None:
    """El hook solo valida en `PhaseStart` de `ordena` (spec: '...en la fase
    ordena'). Otras fases no se bloquean por falta de `adr_ref`."""
    root = _make_root_with_adrs(tmp_path, _ROOT_ADR)
    hook = AdrTraceabilityHook(root=root)
    ctx = PhaseContext(phase="divide", artifact_content=_divide_artifact(None))

    result = hook.run(ctx)

    assert result.decision == "allow"
