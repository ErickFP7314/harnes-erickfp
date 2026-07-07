"""WebPage/scripts/gen_portada_web.py -- build-time: convierte el arte de
portada del harness (`src/erickfp/ui/_portada_asset.py`, ROWS 25x149) en un
fragmento HTML + CSS para la web estatica de WebPage/.

Spec: web-portada-asset (Generacion build-time desde el asset, Fidelidad del
arte, Regenerabilidad). Design: landing-webpage D3.

Reglas:
- Solo lectura del asset del harness (`src/erickfp/ui/_portada_asset.py`).
  Este script NUNCA escribe bajo `src/`.
- Los segmentos de `ROWS` ya vienen fusionados por color (ver
  `scripts/gen_portada.py` del harness) -- este script solo mapea
  segmento -> <span class="cN"> usando un mapa de color -> clase.
- Segmentos de whitespace puro con fg blanco (`#FFFFFF`) se emiten como
  texto plano (sin <span>): no aportan color visible y reducen el HTML.
- El fondo (#222222) se fija una sola vez en el <pre>, nunca por span.
- Inyeccion idempotente en index.html entre los marcadores
  `<!-- PORTADA:BEGIN -->` / `<!-- PORTADA:END -->` (reemplaza el bloque
  completo en cada ejecucion; re-ejecutable sin acumular contenido).
- Self-check integrado: valida que el asset importado tiene 25 filas y que
  cada fila expande a 149 columnas (sin pytest -- gate de calidad es el
  checklist D7 del design, documentado como excepcion consciente al TDD
  estricto del proyecto).

Uso:
    .venv/bin/python WebPage/scripts/gen_portada_web.py
    (o python3 WebPage/scripts/gen_portada_web.py -- no requiere instalar
    nada, es stdlib puro)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

EXPECTED_ROWS = 25
EXPECTED_COLS = 149

BEGIN_MARKER = "<!-- PORTADA:BEGIN -->"
END_MARKER = "<!-- PORTADA:END -->"

Segment = tuple[str, str, str]  # (texto, fg_hex, bg_hex)


def _repo_root() -> Path:
    # WebPage/scripts/gen_portada_web.py -> WebPage/scripts -> WebPage -> repo root
    return Path(__file__).resolve().parent.parent.parent


def load_rows(asset_path: Path) -> list[list[Segment]]:
    """Importa `ROWS` desde `_portada_asset.py` via importlib, sin tocar
    `sys.path` de forma permanente ni modificar el archivo (solo lectura)."""
    spec = importlib.util.spec_from_file_location("_portada_asset_readonly", asset_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar el asset en {asset_path}")
    module: ModuleType = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows: list[list[Segment]] = module.ROWS
    return rows


def self_check(rows: list[list[Segment]]) -> None:
    """Self-check bloqueante (design D3 / D7.7): 25 filas x 149 columnas
    expandidas. Sin pytest -- es el unico gate 'tipo test' de este cambio."""
    assert len(rows) == EXPECTED_ROWS, (
        f"Se esperaban {EXPECTED_ROWS} filas, se encontraron {len(rows)}"
    )
    for i, row in enumerate(rows):
        width = sum(len(text) for text, _fg, _bg in row)
        assert width == EXPECTED_COLS, (
            f"Fila {i} expande a {width} columnas, se esperaban {EXPECTED_COLS}"
        )


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_color_classes(rows: list[list[Segment]]) -> dict[str, str]:
    """Asigna una clase `c0..cN` a cada color fg distinto usado en el arte
    (excluyendo blanco puro, que se renderiza como texto plano sin span)."""
    colors: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for _text, fg, _bg in row:
            if fg == "#FFFFFF":
                continue
            if fg not in seen:
                seen.add(fg)
                colors.append(fg)
    return {color: f"c{i}" for i, color in enumerate(colors)}


def render_pre_html(rows: list[list[Segment]], color_classes: dict[str, str]) -> str:
    """Emite `<pre class="portada" aria-hidden="true">` con un <span> por
    segmento de color (fusionado), y texto plano para segmentos blancos
    (whitespace decorativo)."""
    lines: list[str] = []
    lines.append(BEGIN_MARKER)
    lines.append('<pre class="portada" aria-hidden="true">')
    for row in rows:
        row_html_parts: list[str] = []
        for text, fg, _bg in row:
            escaped = _escape_html(text)
            if fg == "#FFFFFF":
                row_html_parts.append(escaped)
            else:
                cls = color_classes[fg]
                row_html_parts.append(f'<span class="{cls}">{escaped}</span>')
        lines.append("".join(row_html_parts))
    lines.append("</pre>")
    lines.append(END_MARKER)
    return "\n".join(lines)


def render_portada_css(color_classes: dict[str, str]) -> str:
    """Genera `assets/css/portada.css`: mapa color -> clase + estilos base
    del contenedor `<pre class="portada">` (clamp responsive, design D2/D5,
    spec web-portada-asset Requirement 'Comportamiento responsive del arte')."""
    lines = [
        "/*",
        " * portada.css -- GENERADO por scripts/gen_portada_web.py.",
        " * NO EDITAR A MANO. Regenerar con:",
        " *     .venv/bin/python WebPage/scripts/gen_portada_web.py",
        " *",
        " * Clases de color c0..cN mapeadas 1:1 a los hex fg presentes en",
        " * src/erickfp/ui/_portada_asset.py (ROWS). El fondo #222222 se fija",
        " * una sola vez en .portada, nunca por span (design D3).",
        " */",
        "",
        ".portada {",
        "  background-color: #222222;",
        "  color: #ffffff;",
        "  margin: 0;",
        "  padding: var(--space-3, 1rem) 0;",
        "  white-space: pre;",
        "  overflow: hidden;",
        "  /* Responsive: escala fluida sin scroll horizontal (design D2,",
        "     spec web-portada-asset Requirement 'Comportamiento responsive"
        " del arte'). 149 columnas monospace ~0.6ch por unidad de font-size. */",
        "  font-size: clamp(3px, 1.1vw, 11px);",
        "  line-height: 1.05;",
        "  letter-spacing: 0;",
        "  text-align: center;",
        "}",
        "",
    ]
    for color, cls in color_classes.items():
        lines.append(f".portada .{cls} {{ color: {color}; }}")
    lines.append("")
    return "\n".join(lines)


def inject_into_html(html_path: Path, pre_html: str) -> None:
    """Inyecta `pre_html` (ya envuelto con BEGIN/END) en `html_path` de forma
    idempotente: si los marcadores existen, reemplaza el bloque; si no
    existen, no hace nada destructivo -- falla con un mensaje claro (index.html
    debe crear los marcadores primero, tarea A1/B1)."""
    html = html_path.read_text(encoding="utf-8")
    if BEGIN_MARKER not in html or END_MARKER not in html:
        raise RuntimeError(
            f"{html_path} no contiene los marcadores {BEGIN_MARKER}/{END_MARKER}. "
            "Crea el hueco en index.html antes de ejecutar este script."
        )
    start = html.index(BEGIN_MARKER)
    end = html.index(END_MARKER) + len(END_MARKER)
    new_html = html[:start] + pre_html + html[end:]
    html_path.write_text(new_html, encoding="utf-8")


def generate(repo_root: Path) -> None:
    asset_path = repo_root / "src" / "erickfp" / "ui" / "_portada_asset.py"
    index_path = repo_root / "WebPage" / "index.html"
    css_path = repo_root / "WebPage" / "assets" / "css" / "portada.css"

    rows = load_rows(asset_path)
    self_check(rows)

    color_classes = build_color_classes(rows)
    pre_html = render_pre_html(rows, color_classes)
    css = render_portada_css(color_classes)

    inject_into_html(index_path, pre_html)
    css_path.write_text(css, encoding="utf-8")

    print(f"OK: {EXPECTED_ROWS}x{EXPECTED_COLS} verificado.")
    print(f"Inyectado en {index_path}")
    print(f"Escrito {css_path} ({len(color_classes)} colores)")


def main() -> None:
    generate(_repo_root())


if __name__ == "__main__":
    sys.exit(main() or 0)
