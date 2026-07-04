"""hooks/adr_graph.py -- parseo de frontmatter YAML de ADRs y validacion de
trazabilidad por DFS (Decision 7 del design).

**Desviacion documentada respecto al design**: el design (Decision 7 /
Cambios de archivos) ubica este algoritmo en `src/erickfp/cogito/adr.py`.
Se implementa aqui, dentro de `hooks/`, en su lugar, porque el contrato de
dependencia YA establecido en `pyproject.toml` (`[tool.importlinter]`,
Decision 1: `hooks -> api`; `cogito -> api,provider,tools,hooks,memory`)
prohibe que `hooks/adr_traceability.py` importe algo de `erickfp.cogito`
-- `cogito` esta POR ENCIMA de `hooks` en la jerarquia de capas, nunca al
reves. Mover el algoritmo a `cogito/adr.py` habria forzado esa importacion
prohibida. Mantenerlo como modulo hermano dentro de `hooks/` preserva la
regla de dependencia ya vigente sin needing ningun cambio en el contrato; si
una fase futura (Fase 10) necesita esta misma logica fuera de un hook, puede
importarla desde aqui (`hooks -> api` sigue siendo la unica dependencia).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from erickfp.api.types import HookResult


def parse_frontmatter(text: str) -> dict[str, Any] | None:
    """Extrae el bloque YAML entre las dos primeras lineas `---` de `text`.

    Retorna `None` si `text` no trae un frontmatter valido (p.ej. `README.md`
    del directorio `adr/`, que no declara `id`).
    """
    stripped = text.lstrip()
    if not stripped.startswith("---"):
        return None

    parts = stripped.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None

    return data if isinstance(data, dict) else None


def load_adr_graph(adr_dir: Path) -> dict[int, dict[str, Any]]:
    """Parsea todos los `*.md` de `adr_dir` y arma `{id: frontmatter}`.

    Archivos sin frontmatter valido, sin campo `id`, o con un `id` que no es
    convertible a `int` (Lote 2, tarea 2.12: `int("no-es-un-numero")`
    lanzaba `ValueError` sin capturar) se ignoran en silencio -- igual que
    la plantilla `README.md`, que documenta el formato pero no es un ADR
    real.
    """
    graph: dict[int, dict[str, Any]] = {}
    if not adr_dir.is_dir():
        return graph

    for path in sorted(adr_dir.glob("*.md")):
        frontmatter = parse_frontmatter(path.read_text())
        if frontmatter is None or "id" not in frontmatter:
            continue
        try:
            adr_id = int(frontmatter["id"])
        except (ValueError, TypeError):
            continue
        graph[adr_id] = frontmatter

    return graph


def validate_traceability(adr_ref: int, graph: dict[int, dict[str, Any]]) -> HookResult:
    """DFS por `parents` desde `adr_ref` hasta un nodo raiz (`parents: []`).

    Algoritmo de Decision 7:
    1. Id inexistente en el grafo -> `deny`.
    2. Ciclo detectado (id ya presente en la pila de la rama actual) -> `deny`.
    3. Todo camino termina en un nodo con `parents: []` -> `allow`.
    """
    return _dfs(adr_ref, graph, stack=[])


def _dfs(node_id: int, graph: dict[int, dict[str, Any]], stack: list[int]) -> HookResult:
    if node_id in stack:
        chain = " -> ".join(str(i) for i in [*stack, node_id])
        return HookResult(decision="deny", reason=f"ciclo detectado en el grafo ADR: {chain}")

    if node_id not in graph:
        return HookResult(decision="deny", reason=f"el ADR referenciado (id={node_id}) no existe")

    parents = graph[node_id].get("parents") or []
    if not parents:
        return HookResult(decision="allow")

    branch = [*stack, node_id]
    for parent_id in parents:
        result = _dfs(int(parent_id), graph, branch)
        if result.decision == "deny":
            return result

    return HookResult(decision="allow")
