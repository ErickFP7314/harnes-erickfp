"""tools/registry.py -- registro de tools (Decision 3 del design: contraste con hooks).

Las tools son stateless y aditivas: un registry a nivel de modulo alcanza
para "soltar un archivo y que aparezca" (spec tool-registry), a diferencia de
los hooks (Decision 3), que llevan estado acumulativo y se inyectan por
instancia. `dict` preserva el orden de insercion (Python 3.7+), lo que
garantiza el orden estable exigido por la spec.
"""

from __future__ import annotations

from erickfp.api.types import ToolDef
from erickfp.tools.base import Tool


class ToolRegistry:
    """Registro ordenado de tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.definition().name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def definitions(self) -> list[ToolDef]:
        return [tool.definition() for tool in self._tools.values()]


# Instancia unica del proceso -- las tools concretas del MVP se registran
# abajo (tarea 5.8) para que "importar erickfp.tools.registry" ya deje el
# registry listo para el agent loop (spec tool-registry: registro de las 3
# tools del MVP al arrancar el sistema).
registry = ToolRegistry()

# Import diferido (despues de crear `registry`) para no introducir un ciclo:
# bash/read_file/write_file no dependen de este modulo, solo de api.types.
from erickfp.tools.bash import BashTool  # noqa: E402
from erickfp.tools.read_file import ReadFileTool  # noqa: E402
from erickfp.tools.write_file import WriteFileTool  # noqa: E402

registry.register(BashTool())
registry.register(ReadFileTool())
registry.register(WriteFileTool())
