"""tools/read_file.py -- Tool que lee un archivo de texto (spec tool-registry)."""

from __future__ import annotations

import json
from pathlib import Path

from erickfp.api.types import ToolDef


class ReadFileTool:
    """Lee el contenido de un archivo de texto y lo retorna como (contenido, is_error)."""

    def definition(self) -> ToolDef:
        return ToolDef(
            name="read_file",
            description="Lee el contenido de un archivo de texto dada su ruta.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta del archivo a leer."}
                },
            },
            required=["path"],
        )

    def execute(self, input: str) -> tuple[str, bool]:
        try:
            args = json.loads(input) if input else {}
        except json.JSONDecodeError:
            return ("input invalido: se esperaba JSON con la clave 'path'", True)

        path = args.get("path", "") if isinstance(args, dict) else ""
        if not path:
            return ("ruta vacia", True)

        try:
            content = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            return (f"no se pudo leer {path}: {exc}", True)

        return (content, False)
