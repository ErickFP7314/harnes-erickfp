"""tests/hooks/test_adr_graph.py -- parseo de frontmatter y carga del grafo
ADR (Lote 2, tarea 2.11, SUGGESTION-1 del verify-report de ciclo 1).

`hooks/adr_traceability.py` cubre el DFS de trazabilidad (tests/hooks/
test_adr_traceability.py); este archivo cubre las ramas de parseo de
`adr_graph.py` que quedaron sin test dedicado en el ciclo 1: frontmatter con
YAML invalido (debe ignorarse en silencio, ya lo hacia `parse_frontmatter`)
y un campo `id` que NO es convertible a `int` (bug real: `load_adr_graph`
llamaba `int(frontmatter["id"])` sin capturar `ValueError`/`TypeError`,
lo que propagaba una excepcion nativa en vez de ignorar el archivo).
"""

from __future__ import annotations

from pathlib import Path

from erickfp.hooks.adr_graph import load_adr_graph, parse_frontmatter

_INVALID_YAML = """---
titulo: "sin cerrar
parents: [1
---
Contenido irrelevante.
"""

_NON_INT_ID = """---
id: no-es-un-numero
titulo: "id invalido"
parents: []
estado: aceptada
trade_off: "ninguno"
---
Contenido irrelevante.
"""

_VALID_ROOT_ADR = """---
id: 1
titulo: "Axioma raiz"
parents: []
estado: aceptada
trade_off: "ninguno"
---
Contenido del ADR raiz.
"""


def test_invalid_yaml_and_non_int_id_handled_cleanly(tmp_path: Path) -> None:
    """Frontmatter con YAML invalido y con `id` no convertible a `int` se
    ignoran en silencio -- ninguno de los dos hace que `load_adr_graph`
    propague una excepcion nativa (`yaml.YAMLError`/`ValueError`)."""
    adr_dir = tmp_path / "adr"
    adr_dir.mkdir()
    (adr_dir / "001-invalid-yaml.md").write_text(_INVALID_YAML)
    (adr_dir / "002-non-int-id.md").write_text(_NON_INT_ID)
    (adr_dir / "003-valid.md").write_text(_VALID_ROOT_ADR)

    graph = load_adr_graph(adr_dir)

    # Solo el ADR valido (id=1) entra al grafo; los otros dos se ignoran.
    assert graph == {
        1: {
            "id": 1,
            "titulo": "Axioma raiz",
            "parents": [],
            "estado": "aceptada",
            "trade_off": "ninguno",
        }
    }


def test_parse_frontmatter_returns_none_on_invalid_yaml() -> None:
    """`parse_frontmatter` en aislamiento: YAML invalido -> `None`, sin
    lanzar `yaml.YAMLError`."""
    assert parse_frontmatter(_INVALID_YAML) is None


def test_load_adr_graph_on_empty_or_missing_dir_returns_empty_graph(tmp_path: Path) -> None:
    """Guard existente: directorio ADR ausente no lanza, retorna grafo vacio."""
    assert load_adr_graph(tmp_path / "no-existe") == {}
