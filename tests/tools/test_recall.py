"""tests/tools/test_recall.py -- RecallTool (Lote 5 harness-v0-2, spec
memory-store delta, Requirement 'Recall bajo demanda' MODIFICADO: `recall`
ahora se expone como una Tool registrada en el tool-registry).

`_FakeRecallSource` es un doble ad-hoc (duck typing estructural, Decision 5
del design): satisface `.recall(query, limit)` SIN depender de
`erickfp.memory` -- exactamente lo que exige design.md D9 ('RecallTool
envuelve objeto con .recall(query,limit) INYECTADO desde cli, no importa
memory.Store -> respeta capas').
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

from erickfp.api.types import Entry
from erickfp.tools import recall as recall_module
from erickfp.tools.recall import RecallTool


class _FakeRecallSource:
    """NO hereda de nada ni importa `erickfp.memory` -- solo satisface la
    forma estructural `.recall(query, limit) -> list[Entry]`."""

    def __init__(self, entries: list[Entry]) -> None:
        self._entries = entries
        self.calls: list[tuple[str, int]] = []

    def recall(self, query: str, limit: int) -> list[Entry]:
        self.calls.append((query, limit))
        return self._entries[:limit]


def test_recall_tool_uses_injected_duck_typed_store() -> None:
    """`RecallTool` delega en el objeto inyectado (no en un `Store`
    concreto importado): llama `.recall(query, limit)` con los argumentos
    del `tool_input` JSON y formatea los `Entry` retornados."""
    entries = [
        Entry(kind="decision", content="usar LiteLLM como adapter"),
        Entry(kind="fact", content="el usuario prefiere Python"),
    ]
    source = _FakeRecallSource(entries)
    tool = RecallTool(source)

    result_text, is_error = tool.execute(json.dumps({"query": "LiteLLM", "limit": 2}))

    assert source.calls == [("LiteLLM", 2)]
    assert is_error is False
    assert "usar LiteLLM como adapter" in result_text
    assert "el usuario prefiere Python" in result_text


def test_recall_tool_applies_default_limit_when_absent() -> None:
    """Triangulacion: sin `limit` explicito en el input, usa el limite por
    defecto configurado en el constructor -- prueba que el valor NO esta
    hardcodeado a lo que paso el primer test."""
    entries = [Entry(kind="fact", content=f"dato {i}") for i in range(10)]
    source = _FakeRecallSource(entries)
    tool = RecallTool(source, default_limit=3)

    tool.execute(json.dumps({"query": "dato"}))

    assert source.calls == [("dato", 3)]


def test_recall_tool_reports_no_results_without_error() -> None:
    """Sin coincidencias, `RecallTool` informa 'sin resultados' -- no es un
    error (Scenario 'Recall exitoso' de la spec no distingue vacio de
    fallo; solo `is_error` marca fallos reales de input)."""
    source = _FakeRecallSource([])
    tool = RecallTool(source)

    result_text, is_error = tool.execute(json.dumps({"query": "nada"}))

    assert is_error is False
    assert "sin resultados" in result_text


def test_recall_tool_rejects_missing_query_as_error() -> None:
    """Input sin `query` (o vacio) es un error de input -- nunca invoca
    `.recall()` con un criterio vacio."""
    source = _FakeRecallSource([Entry(kind="fact", content="irrelevante")])
    tool = RecallTool(source)

    result_text, is_error = tool.execute(json.dumps({}))

    assert is_error is True
    assert source.calls == []


def test_recall_tool_definition_declares_query_as_required() -> None:
    """La `ToolDef` expone el nombre `recall` y exige `query` -- el
    registry/agent loop puede describirla al Provider igual que las
    demas tools locales."""
    tool = RecallTool(_FakeRecallSource([]))

    definition = tool.definition()

    assert definition.name == "recall"
    assert "query" in definition.required


def test_recall_module_never_imports_memory_layer() -> None:
    """Introspeccion (design.md D9: 'no importa memory.Store -> respeta
    capas'): `tools/recall.py` NUNCA debe importar `erickfp.memory` -- el
    objeto Store concreto se inyecta desde `cli.py` (composition root), no
    se importa aqui (mismo patron que `test_runtime_never_parses_html` de
    `tests/ui/test_banner.py`: analiza los imports reales via AST, no un
    grep textual que un docstring explicativo podria falsear)."""
    source_path = Path(inspect.getfile(recall_module))
    tree = ast.parse(source_path.read_text(encoding="utf-8"))

    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)

    assert not any(name.startswith("erickfp.memory") for name in imported_names)
