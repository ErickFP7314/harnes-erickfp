"""tools/base.py -- Protocol Tool (Decision 5 del design).

`@runtime_checkable` porque el registry (`tools/registry.py`) usa
`isinstance()` para validar un objeto antes de aceptarlo.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from erickfp.api.types import ToolDef


@runtime_checkable
class Tool(Protocol):
    def definition(self) -> ToolDef: ...

    def execute(self, input: str) -> tuple[str, bool]: ...
