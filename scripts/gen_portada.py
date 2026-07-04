"""scripts/gen_portada.py -- generador build-time del asset del banner
(harness-v0-2, design.md D3 "ui-polish": "scripts/gen_portada.py (exento de
lint) parsea los spans rgb 25x149 -> genera ui/_portada_asset.py").

Parsea `portada.html` (25 <div> filas, cada una con 149 <span
style="color: rgb(R, G, B); background-color: rgb(R, G, B);">CHAR</span>`,
espacios como `&nbsp;`) y produce un modulo Python con una constante `ROWS`:
lista de filas, cada fila una lista de segmentos `(texto, fg_hex, bg_hex)`
-- spans consecutivos del mismo color se fusionan en un solo segmento para
compactar el asset. El runtime (erickfp.ui.banner) SOLO importa `ROWS`;
jamas vuelve a tocar HTML (spec ui-polish, Requirement 'Banner precomputado
en build-time').

Este script vive fuera de `src/erickfp/` (no es codigo de produccion, es
tooling de build) y esta exento de lint/mypy (`pyproject.toml`
`[tool.ruff] extend-exclude = ["scripts"]`), igual que los demas spikes de
`scripts/`. Se ejercita con tests (`tests/ui/test_gen_portada.py`) para
proteger la logica de parseo.

Uso:
    .venv/bin/python scripts/gen_portada.py
"""

from __future__ import annotations

import re
from pathlib import Path

Segment = tuple[str, str, str]  # (texto, fg_hex, bg_hex)

_DIV_RE = re.compile(r"<div>(.*?)</div>", re.S)
_SPAN_RE = re.compile(
    r'<span style="color: rgb\((\d+), (\d+), (\d+)\); '
    r'background-color: rgb\((\d+), (\d+), (\d+)\);">(.*?)</span>'
)
_NBSP = "&nbsp;"

_HEADER = '''"""ui/_portada_asset.py -- asset PRECOMPUTADO por scripts/gen_portada.py.

NO EDITAR A MANO. Regenerar con:
    .venv/bin/python scripts/gen_portada.py

Fuente: portada.html (25 filas x 149 columnas, paleta cyan/verde/blanco
sobre fondo #222222). El runtime (erickfp.ui.banner) NUNCA parsea HTML
(spec ui-polish, Requirement 'Banner precomputado en build-time').
"""

from __future__ import annotations

ROWS: list[list[tuple[str, str, str]]] = [
'''


def _hex(r: str, g: str, b: str) -> str:
    return f"#{int(r):02X}{int(g):02X}{int(b):02X}"


def _decode_char(raw: str) -> str:
    return " " if raw == _NBSP else raw


def parse_portada_html(html_path: Path) -> list[list[Segment]]:
    """Parsea `html_path` (formato de `portada.html`) en filas de segmentos
    `(texto, fg_hex, bg_hex)`. Spans consecutivos con el mismo par de
    colores se fusionan en un solo segmento -- compacta el asset generado
    sin perder informacion (expandir cada segmento a caracteres reconstruye
    exactamente la fila original)."""
    html = html_path.read_text(encoding="utf-8")
    rows: list[list[Segment]] = []

    for div_match in _DIV_RE.finditer(html):
        row: list[Segment] = []
        for r, g, b, br, bg, bb, raw_char in _SPAN_RE.findall(div_match.group(1)):
            fg_hex = _hex(r, g, b)
            bg_hex = _hex(br, bg, bb)
            char = _decode_char(raw_char)
            if row and row[-1][1] == fg_hex and row[-1][2] == bg_hex:
                prev_text, _, _ = row[-1]
                row[-1] = (prev_text + char, fg_hex, bg_hex)
            else:
                row.append((char, fg_hex, bg_hex))
        rows.append(row)

    return rows


def render_asset_module(rows: list[list[Segment]]) -> str:
    """Genera el codigo fuente de `ui/_portada_asset.py` a partir de `rows`
    ya parseadas -- una constante `ROWS` que el runtime importa directo,
    sin volver a parsear HTML."""
    lines = [_HEADER.rstrip("\n")]
    for row in rows:
        segments = ", ".join(f"({text!r}, {fg!r}, {bg!r})" for text, fg, bg in row)
        lines.append(f"    [{segments}],")
    lines.append("]")
    lines.append("")
    return "\n".join(lines)


def generate(html_path: Path, output_path: Path) -> None:
    """Orquesta parseo + escritura del asset (build step, spec ui-polish
    Scenario 'Regeneracion del asset')."""
    rows = parse_portada_html(html_path)
    output_path.write_text(render_asset_module(rows), encoding="utf-8")


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    generate(
        repo_root / "portada.html",
        repo_root / "src" / "erickfp" / "ui" / "_portada_asset.py",
    )


if __name__ == "__main__":
    main()
