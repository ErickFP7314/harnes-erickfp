"""tests/ui/test_gen_portada.py -- generador build-time del asset de banner
(Lote 1, tarea 1.3): parsea `portada.html` (25 <div> filas x 149 <span> con
estilos rgb inline) y produce una estructura de filas de segmentos (texto,
fg_hex, bg_hex) consumible por Rich -- el runtime NUNCA parsea HTML (spec
ui-polish, Requirement 'Banner precomputado en build-time').

`scripts/gen_portada.py` esta exento de lint (mismo criterio que los demas
scripts de build/spike, `pyproject.toml` `[tool.ruff] extend-exclude`), pero
SI se ejercita con tests -- es el unico punto que sabe leer HTML.
"""

from __future__ import annotations

from pathlib import Path

from scripts.gen_portada import parse_portada_html, render_asset_module


def _span(fg: str, bg: str, char: str) -> str:
    return f'<span style="color: rgb({fg}); background-color: rgb({bg});">{char}</span>'


_BG = "34, 34, 34"
_FIXTURE_HTML = (
    "<!DOCTYPE html><html><body>"
    "<div>"
    + _span("255, 255, 255", _BG, "&nbsp;")
    + _span("0, 255, 255", _BG, "&nbsp;")
    + _span("0, 255, 255", _BG, "A")
    + "</div>"
    "<div>" + _span("0, 255, 0", _BG, "B") + "</div>"
    "</body></html>"
)


def test_parses_portada_html_into_rich_text_asset(tmp_path: Path) -> None:
    html_path = tmp_path / "portada.html"
    html_path.write_text(_FIXTURE_HTML, encoding="utf-8")

    rows = parse_portada_html(html_path)

    assert len(rows) == 2  # 2 <div> == 2 filas
    # fila 0: el 1er span (blanco) queda solo; el 2do y 3er span comparten
    # color cyan y se fusionan en un solo segmento (compactacion); &nbsp;
    # se decodifica a espacio real.
    assert rows[0] == [(" ", "#FFFFFF", "#222222"), (" A", "#00FFFF", "#222222")]
    assert rows[1] == [("B", "#00FF00", "#222222")]


def test_parses_real_portada_html_25x149() -> None:
    """El asset real debe cubrir las 25 filas x 149 columnas logicas -- una
    vez expandidos los segmentos fusionados de vuelta a caracteres, cada
    fila suma exactamente 149."""
    repo_root = Path(__file__).resolve().parents[2]
    rows = parse_portada_html(repo_root / "portada.html")

    assert len(rows) == 25
    for row in rows:
        total_chars = sum(len(text) for text, _, _ in row)
        assert total_chars == 149


def test_render_asset_module_produces_valid_python_with_rows_constant(tmp_path: Path) -> None:
    html_path = tmp_path / "portada.html"
    html_path.write_text(_FIXTURE_HTML, encoding="utf-8")
    rows = parse_portada_html(html_path)

    source = render_asset_module(rows)
    namespace: dict[str, object] = {}
    exec(compile(source, "<portada_asset>", "exec"), namespace)

    assert namespace["ROWS"] == rows
