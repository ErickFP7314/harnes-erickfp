"""agent/tokens.py -- TokenTracker (spec token-viewer, Lote 3 harness-v0-2,
tarea 3.15, design.md Decision 6: "TokenTracker(agent) acumula: run_turn(
tracker=None) -> tracker.add(response.usage)").

Vive en la capa `agent` (por encima de `provider`/`api`, contrato de capas de
`pyproject.toml`): es estado de sesion del agent loop, no del adapter. El
comando `/tokens` de `cli.py` lee su estado -- ninguna otra capa lo muta.
"""

from __future__ import annotations

from dataclasses import dataclass

from erickfp.api.types import Usage


@dataclass
class TokenTracker:
    """Acumulador de tokens de una sesion. Empieza en cero; cada `add()`
    SUMA (nunca reemplaza) al total en curso."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, usage: Usage | None) -> None:
        """Suma `usage` al acumulado. `usage=None` (turno sin conteo, p.ej.
        `raw.usage` ausente en el adapter) no lanza ni altera el estado."""
        if usage is None:
            return
        self.prompt_tokens += usage.prompt
        self.completion_tokens += usage.completion
        self.total_tokens += usage.total
