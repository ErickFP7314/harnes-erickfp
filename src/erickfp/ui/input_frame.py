"""erickfp.ui.input_frame -- cuadro decorado para el prompt de entrada
(Lote 1, ui-polish, design.md D3, spec ui-polish Requirement 'Input
decorado en cuadro').

`frame(label)` SOLO construye el renderable (`rich.panel.Panel`) -- NUNCA
lee stdin. El composition root (`cli.py`) compone `decorated_read_line`:
imprime este Panel con el `Console` y DESPUES llama a `agent.gate.
read_line` para el stdin real, preservando el patron de consumer unico de
stdin (spike 2.3, docs/spikes/repl-input.md) -- un segundo `input()` aqui
lo romperia.
"""

from __future__ import annotations

from rich.panel import Panel
from rich.text import Text

from erickfp.ui.theme import BG, CYAN


def frame(label: str) -> Panel:
    """Cuadro Rich que envuelve visualmente `label` (p. ej. `"tu> "`) con la
    paleta del tema -- sin leer stdin (spec ui-polish, Scenario 'Prompt en
    cuadro con tema')."""
    text = Text(label, style=f"bold {CYAN} on {BG}")
    return Panel(text, style=f"on {BG}", border_style=CYAN)
