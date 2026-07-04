"""tests/ui/test_theme.py -- paleta compartida del tema (Lote 1, tareas
1.12-1.13, spec ui-polish, Scenario 'Consistencia de tema entre banner e
input'): banner e input decorado usan LA MISMA paleta (#00FFFF/#00FF00/
#222222), sin colores ad-hoc definidos por separado en cada modulo.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import erickfp.ui.banner as banner_module
import erickfp.ui.input_frame as input_frame_module
from erickfp.ui import theme
from erickfp.ui.banner import render_banner
from erickfp.ui.input_frame import frame


class _FakeConsole:
    def __init__(self, width: int) -> None:
        self.width = width
        self.printed: list[object] = []

    def print(self, renderable: object) -> None:
        self.printed.append(renderable)


def _imports_theme(module: object) -> bool:
    source = Path(inspect.getfile(module)).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "erickfp.ui.theme":
            return True
    return False


def test_theme_exposes_shared_palette_constants() -> None:
    assert theme.CYAN == "#00FFFF"
    assert theme.GREEN == "#00FF00"
    assert theme.BG == "#222222"


def test_banner_and_input_share_same_palette() -> None:
    # Ambos modulos importan la paleta desde `erickfp.ui.theme` -- ninguno
    # redefine sus propias constantes de color (sin colores ad-hoc).
    assert _imports_theme(banner_module)
    assert _imports_theme(input_frame_module)

    console = _FakeConsole(width=149)
    render_banner(console)
    banner_panel = console.printed[0]
    input_panel = frame("tu> ")

    assert theme.BG in str(banner_panel.style)
    assert theme.BG in str(input_panel.style)
    assert banner_panel.border_style == theme.CYAN
    assert input_panel.border_style == theme.CYAN
