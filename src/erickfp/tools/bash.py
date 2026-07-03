"""tools/bash.py -- Tool que ejecuta un comando shell (spec tool-registry).

`execute()` jamas lanza una excepcion: cualquier fallo se traduce a
`(salida, is_error=True)` -- el mismo contrato de "nunca excepcion" que
gobierna el permission gate y los hooks (Decision 3 del design).
"""

from __future__ import annotations

import json
import subprocess

from erickfp.api.types import ToolDef

_TIMEOUT_SECONDS = 30


class BashTool:
    """Ejecuta un comando de shell y retorna (salida combinada, is_error)."""

    def definition(self) -> ToolDef:
        return ToolDef(
            name="bash",
            description=(
                "Ejecuta un comando de shell y retorna su salida combinada (stdout+stderr)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Comando a ejecutar."}
                },
            },
            required=["command"],
        )

    def execute(self, input: str) -> tuple[str, bool]:
        try:
            args = json.loads(input) if input else {}
        except json.JSONDecodeError:
            return ("input invalido: se esperaba JSON con la clave 'command'", True)

        command = args.get("command", "") if isinstance(args, dict) else ""
        if not command:
            return ("comando vacio", True)

        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=_TIMEOUT_SECONDS
            )
        except subprocess.TimeoutExpired:
            return (f"comando excedio el timeout de {_TIMEOUT_SECONDS}s", True)

        output = result.stdout + result.stderr
        return (output, result.returncode != 0)
