"""provider/base.py -- Protocol Provider (Decision 5 del design).

Interfaz estructural (typing.Protocol) para cualquier proveedor de LLM. Este
modulo depende solo de `erickfp.api.types` (Decision 1: provider -> api).
Ningun SDK nativo se importa aqui -- eso solo ocurre en el adapter concreto
(`litellm_gemini.py`, Decision 2).
"""

from __future__ import annotations

from typing import Protocol

from erickfp.api.types import Message, Response, ToolDef


class ProviderError(Exception):
    """Fallo definitivo del proveedor de LLM (hotfix 2026-07-04).

    Los adapters traducen cualquier excepcion nativa (litellm, httpx, etc.)
    a este tipo de dominio cuando agotan sus reintentos, para que las capas
    superiores (CLI, orquestador) puedan fallar limpio -- sin traceback y
    sin conocer los tipos de error de ningun SDK. El mensaje conserva el
    texto del error original para diagnostico.
    """


class Provider(Protocol):
    def send(self, messages: list[Message], tools: list[ToolDef]) -> Response: ...

    def model(self) -> str: ...

    def set_model(self, name: str) -> None: ...
