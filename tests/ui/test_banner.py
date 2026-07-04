"""tests/ui/test_banner.py -- banner de portada (Lote 1, tareas 1.5-1.9,
spec ui-polish). `render_banner(console)` consume el asset precomputado
`erickfp.ui._portada_asset.ROWS` (generado por `scripts/gen_portada.py`);
el runtime NUNCA parsea HTML. Usa un doble minimo de Console (duck typing
estructural: `.width` + `.print(renderable)`) en vez de un `rich.console.
Console` real, para no depender de I/O de terminal en los tests (mismo
patron que `_DummyConsole` en `tests/cli/test_chat.py`).
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from rich.panel import Panel
from rich.text import Text

import erickfp.ui.banner as banner_module
from erickfp.ui.banner import render_banner


class _FakeConsole:
    def __init__(self, width: int) -> None:
        self.width = width
        self.printed: list[object] = []

    def print(self, renderable: object) -> None:
        self.printed.append(renderable)


def test_wide_terminal_renders_full_banner() -> None:
    console = _FakeConsole(width=149)

    render_banner(console)

    assert len(console.printed) == 1
    panel = console.printed[0]
    assert isinstance(panel, Panel)
    text = panel.renderable
    assert isinstance(text, Text)
    # El asset real tiene 25 filas -- 24 saltos de linea entre ellas.
    assert text.plain.count("\n") == 24


def test_narrow_terminal_renders_fallback_panel() -> None:
    """<149 columnas: version reducida legible, sin cortar el arte a la
    mitad ni lanzar excepcion (spec ui-polish, Scenario 'Terminal
    angosta')."""
    console = _FakeConsole(width=80)

    render_banner(console)  # no debe lanzar

    assert len(console.printed) == 1
    panel = console.printed[0]
    assert isinstance(panel, Panel)
    text = panel.renderable
    assert isinstance(text, Text)
    # NO es el banner completo (25 filas / 24 saltos de linea) -- es una
    # version mini con el nombre del proyecto.
    assert text.plain.count("\n") == 0
    assert "ErickFP" in text.plain


def test_runtime_never_parses_html() -> None:
    """`erickfp.ui.banner` (runtime) NUNCA debe parsear HTML: no importa el
    generador `scripts.gen_portada` ni modulos de parseo HTML, y su codigo
    fuente no referencia `portada.html` -- solo consume el asset ya
    precomputado `erickfp.ui._portada_asset.ROWS` (spec ui-polish,
    Requirement 'Banner precomputado en build-time')."""
    source_path = Path(inspect.getfile(banner_module))
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_names.add(node.module)

    forbidden = {"scripts", "scripts.gen_portada", "html", "html.parser"}
    assert imported_names.isdisjoint(forbidden)
    assert "portada.html" not in source
