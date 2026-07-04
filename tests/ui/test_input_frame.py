"""tests/ui/test_input_frame.py -- cuadro decorado del prompt (Lote 1,
tareas 1.10-1.11, spec ui-polish, Requirement 'Input decorado en cuadro').

`frame(label)` SOLO construye el renderable (`rich.panel.Panel`) -- no lee
stdin. El composition root (`cli.py`) sigue usando `gate.read_line` como
unico consumer de stdin (spike 2.3): imprime el Panel de `frame()` y
DESPUES llama a `gate.read_line`, preservando el patron de consumer unico.
"""

from __future__ import annotations

from rich.panel import Panel
from rich.text import Text

from erickfp.ui.input_frame import frame

_CYAN = "#00FFFF"
_GREEN = "#00FF00"
_BG = "#222222"


def test_decorated_prompt_uses_theme_panel() -> None:
    panel = frame("tu> ")

    assert isinstance(panel, Panel)
    assert panel.border_style in (_CYAN, _GREEN)
    renderable = panel.renderable
    assert isinstance(renderable, Text)
    assert "tu> " in renderable.plain
    # El fondo del cuadro respeta el tema (#222222), sin colores ad-hoc.
    assert _BG in str(panel.style)
