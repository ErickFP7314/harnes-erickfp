"""tools/recall.py -- RecallTool (Lote 5 harness-v0-2, spec memory-store
delta, Requirement 'Recall bajo demanda' MODIFICADO: `recall` ahora es una
`Tool` registrada en el tool-registry, por lo que TODA invocacion del
modelo pasa por el permission gate igual que `bash`/`read_file`/
`write_file`, design.md D9).

`RecallSource` se define AQUI, no se importa `erickfp.memory.store.Store`:
mismo patron de duck typing estructural que el resto de Protocols del
proyecto (Decision 5). `tools/` y `memory/` son capas HERMANAS en el
contrato de `pyproject.toml` (ambas dependen solo de `api`) -- este modulo
JAMAS debe importar `erickfp.memory`; el objeto Store concreto (hoy
`SqliteStore`) se instancia e inyecta desde `cli.py` (composition root).
"""

from __future__ import annotations

import json
from typing import Protocol, runtime_checkable

from erickfp.api.types import Entry, ToolDef

_DEFAULT_LIMIT = 5


@runtime_checkable
class RecallSource(Protocol):
    """Forma estructural minima que `RecallTool` necesita: cualquier objeto
    con `.recall(query, limit) -> list[Entry]` la satisface (hoy
    `SqliteStore`, en tests dobles ad-hoc sin depender de `erickfp.memory`).
    """

    def recall(self, query: str, limit: int) -> list[Entry]: ...


class RecallTool:
    """Envuelve un `RecallSource` inyectado como una `Tool` del registry."""

    def __init__(self, store: RecallSource, default_limit: int = _DEFAULT_LIMIT) -> None:
        self._store = store
        self._default_limit = default_limit

    def definition(self) -> ToolDef:
        return ToolDef(
            name="recall",
            description=(
                "Busca registros previos guardados en el Memory Store "
                "(hechos, decisiones, preferencias, resumenes de sesion) "
                "por un criterio de texto."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Texto a buscar en contenido o tags.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximo de resultados a retornar.",
                    },
                },
            },
            required=["query"],
        )

    def execute(self, input: str) -> tuple[str, bool]:
        try:
            args = json.loads(input) if input else {}
        except json.JSONDecodeError:
            return ("input invalido: se esperaba JSON con la clave 'query'", True)

        query = args.get("query", "") if isinstance(args, dict) else ""
        if not query:
            return ("query vacia", True)

        limit = args.get("limit", self._default_limit) if isinstance(args, dict) else (
            self._default_limit
        )

        entries = self._store.recall(query, limit)
        if not entries:
            return ("sin resultados", False)

        lines = [f"- ({entry.kind}) {entry.content}" for entry in entries]
        return ("\n".join(lines), False)
