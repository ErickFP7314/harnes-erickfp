"""provider/base.py -- Protocol Provider (Decision 5 del design).

Interfaz estructural (typing.Protocol) para cualquier proveedor de LLM. Este
modulo depende solo de `erickfp.api.types` (Decision 1: provider -> api).
Ningun SDK nativo se importa aqui -- eso solo ocurre en el adapter concreto
(`litellm_gemini.py`, Decision 2).
"""

from __future__ import annotations

from typing import Protocol

from erickfp.api.types import Message, Response, ToolDef


class Provider(Protocol):
    def send(self, messages: list[Message], tools: list[ToolDef]) -> Response: ...

    def model(self) -> str: ...

    def set_model(self, name: str) -> None: ...
