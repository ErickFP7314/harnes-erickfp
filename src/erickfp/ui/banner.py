"""erickfp.ui.banner -- banner de portada (Lote 1, ui-polish, design.md D3).

Renderiza el asset precomputado por `scripts/gen_portada.py`
(`erickfp.ui._portada_asset.ROWS`) dentro de un `rich.panel.Panel`. El
runtime NUNCA parsea HTML -- solo importa la constante `ROWS` ya construida
en build-time (spec ui-polish, Requirement 'Banner precomputado en
build-time').
"""

from __future__ import annotations

from typing import Protocol

from rich.panel import Panel
from rich.text import Text

from erickfp.ui._portada_asset import ROWS
from erickfp.ui.theme import BG, CYAN, GREEN

_BANNER_WIDTH = 149


class BannerConsole(Protocol):
    """Forma estructural minima que `render_banner` necesita de un Console
    Rich (o un doble de prueba): ancho detectable + capacidad de imprimir un
    renderable. Duck typing estructural (mismo patron que `PreambleSource`
    en `cli.py`) -- evita acoplar este modulo a `rich.console.Console`."""

    width: int

    def print(self, renderable: object) -> None: ...


def _build_full_banner_text() -> Text:
    """Ensambla el `Text` truecolor de las 25 filas del asset -- cada fila
    ya viene segmentada por color (`scripts/gen_portada.py` fusiona spans
    consecutivos del mismo color)."""
    text = Text()
    last_index = len(ROWS) - 1
    for row_index, row in enumerate(ROWS):
        for chunk, fg_hex, bg_hex in row:
            text.append(chunk, style=f"{fg_hex} on {bg_hex}")
        if row_index != last_index:
            text.append("\n")
    return text


def _build_fallback_text() -> Text:
    """Version mini para terminales <149 columnas: titulo estilizado con la
    misma paleta del banner completo (spec ui-polish, Scenario 'Terminal
    angosta') -- nunca corta el arte 25x149 a la mitad ni lanza error."""
    return Text("ErickFP", style=f"bold {CYAN} on {BG}")


def render_banner(console: BannerConsole) -> None:
    """Renderiza el banner completo (25x149, `console.width >= 149`) o el
    fallback reducido (`console.width < 149`) dentro de un cuadro Rich --
    spec ui-polish, Requirement 'Fallback adaptativo por ancho de
    terminal'."""
    if console.width >= _BANNER_WIDTH:
        console.print(Panel(_build_full_banner_text(), style=f"on {BG}", border_style=CYAN))
    else:
        console.print(Panel(_build_fallback_text(), style=f"on {BG}", border_style=GREEN))
