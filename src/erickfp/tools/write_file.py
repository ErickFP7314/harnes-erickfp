"""tools/write_file.py -- Tool que escribe un archivo de texto (spec tool-registry).

La proteccion de `.ErickFP/core/*` NO vive aqui -- es responsabilidad
independiente del hook `core_guard` (Decision 3 del design, Fase 8). Esta
tool es deliberadamente generica.
"""

from __future__ import annotations

import json
from pathlib import Path

from erickfp.api.types import ToolDef


class WriteFileTool:
    """Escribe (sobrescribiendo) contenido en un archivo de texto dada su ruta."""

    def definition(self) -> ToolDef:
        return ToolDef(
            name="write_file",
            description="Escribe contenido en un archivo de texto dada su ruta (sobrescribe).",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta del archivo a escribir."},
                    "content": {"type": "string", "description": "Contenido a escribir."},
                },
            },
            required=["path", "content"],
        )

    def execute(self, input: str) -> tuple[str, bool]:
        try:
            args = json.loads(input) if input else {}
        except json.JSONDecodeError:
            return ("input invalido: se esperaba JSON con 'path' y 'content'", True)

        path = args.get("path", "") if isinstance(args, dict) else ""
        content = args.get("content", "") if isinstance(args, dict) else ""
        if not path:
            return ("ruta vacia", True)

        try:
            Path(path).write_text(content, encoding="utf-8")
        except OSError as exc:
            return (f"no se pudo escribir {path}: {exc}", True)

        return (f"escrito: {path}", False)
