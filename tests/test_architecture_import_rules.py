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

_REPO_ROOT = Path(__file__).resolve().parents[1]


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
