"""tests/test_architecture_import_rules.py -- valida el contrato completo de
capas de Decision 1 del design (Fase 11, tarea 11.1): `api -> nada`;
`provider|tools|memory -> api`; `hooks -> api`; `cogito ->
api,provider,tools,hooks,memory` (mas `agent`, dependencia real no listada
en el arbol de Decision 1 pero necesaria para ejecutar el agent loop por
fase -- ver 'Secuencia' del design y la desviacion ya documentada para
`agent` en la Fase 8/Lote 4); `cli -> todo`.

El contrato en si vive en `[tool.importlinter]` de `pyproject.toml`; este
test ejecuta `lint-imports` (import-linter) como subproceso sobre el `.venv`
del proyecto y confirma que el codigo real lo respeta -- antes de la Fase 10
esto fallaba con "Missing layer 'erickfp.cogito'" porque el paquete aun no
existia.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import tomllib

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Contrato extendido (Lote 1, tarea 1.1): design.md "Contrato de capas
# extendido (Decision 1)" agrega `ui`, `compaction`, `subagents` sobre el
# contrato base de la Fase 11 (`cli -> cogito -> agent -> hooks|tools|
# provider|memory -> api`). El ciclo delegate (D7: DelegateTool/Research)
# obliga a ubicar `subagents` POR ENCIMA de `agent` -- ver design.md,
# seccion "Ciclo delegate" -- y `ui` entra a la MISMA altura que
# hooks/tools/provider/memory (no depende de nada nuevo, solo de `api`).
_EXPECTED_LAYERS = [
    "erickfp.cli",
    "erickfp.cogito",
    "erickfp.subagents",
    "erickfp.agent",
    "erickfp.compaction",
    "erickfp.hooks | erickfp.tools | erickfp.provider | erickfp.memory | erickfp.ui",
    "erickfp.api",
]


def test_extended_layer_contract_ui_compaction_subagents() -> None:
    """El contrato declarado en `pyproject.toml [[tool.importlinter.contracts]]`
    debe incluir las capas nuevas `ui`, `compaction`, `subagents` en el orden
    exacto de design.md -- ANTES de que exista codigo real en esas capas
    (tarea 1.1 precede a 1.2, que crea los paquetes placeholder)."""
    pyproject = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text())
    contracts = pyproject["tool"]["importlinter"]["contracts"]
    layers_contract = next(c for c in contracts if c["type"] == "layers")
    assert layers_contract["layers"] == _EXPECTED_LAYERS


def test_lint_imports_contract_passes() -> None:
    # El console-script `lint-imports` vive junto al interprete del venv
    # activo (`sys.executable`) -- invocarlo asi, en vez de `python -m
    # importlinter` (el paquete no expone un `__main__` ejecutable), evita
    # depender de que el binario este en el PATH del proceso de pytest.
    lint_imports_bin = Path(sys.executable).parent / "lint-imports"
    result = subprocess.run(
        [str(lint_imports_bin)],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "kept, 0 broken" in result.stdout
