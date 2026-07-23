"""WebPage/scripts/gen_og_image.py -- genera assets/img/og-image.png (1200x630)
para las metas OpenGraph/Twitter Card de index.html y guia.html.

Regla de cero-dependencias-de-red del sitio: este script corre en BUILD TIME
(no en el navegador del visitante) y usa Pillow (venv global o del proyecto,
nunca pip del sistema) + una fuente monoespaciada YA INSTALADA LOCALMENTE en
el sistema (DejaVu Sans Mono). El PNG resultante es un asset estatico -- el
sitio publicado no descarga nada para mostrarlo.

Paleta identica a assets/css/theme.css (fuente de verdad: theme.py del
harness): BG #222222, CYAN #00FFFF, GREEN #00FF00.

Uso:
    ~/.venvs/global/bin/python WebPage/scripts/gen_og_image.py
    (o el venv del proyecto si tiene Pillow instalado)
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:  # pragma: no cover
    print(
        "ERROR: falta Pillow. Instala en un venv (NUNCA en el Python del "
        "sistema), p.ej.: ~/.venvs/global/bin/python -m pip install Pillow",
        file=sys.stderr,
    )
    sys.exit(2)

WIDTH, HEIGHT = 1200, 630

BG = "#222222"
BG_INSET = "#1a1a1a"
TITLEBAR_BG = "#2e2e2e"
BORDER = "#3a3a3a"
CYAN = "#00ffff"
GREEN = "#00ff00"
TEXT_BASE = "#d0d0d0"
TEXT_MUTED = "#8f8f8f"
DOT_RED = "#ff5f56"
DOT_YELLOW = "#ffbd2e"
DOT_GREEN = "#27c93f"

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
FONT_REGULAR = FONT_DIR / "DejaVuSansMono.ttf"
FONT_BOLD = FONT_DIR / "DejaVuSansMono-Bold.ttf"


def _font(path: Path, size: int) -> "ImageFont.FreeTypeFont":
    return ImageFont.truetype(str(path), size)


def _text_w(draw: "ImageDraw.ImageDraw", text: str, font: "ImageFont.FreeTypeFont") -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def generate(out_path: Path) -> None:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    # ---------- Titlebar (misma estetica que .terminal-window) ----------
    titlebar_h = 54
    draw.rectangle([0, 0, WIDTH, titlebar_h], fill=TITLEBAR_BG)
    draw.line([0, titlebar_h, WIDTH, titlebar_h], fill=BORDER, width=1)
    dot_y = titlebar_h // 2
    for i, color in enumerate((DOT_RED, DOT_YELLOW, DOT_GREEN)):
        cx = 34 + i * 30
        r = 9
        draw.ellipse([cx - r, dot_y - r, cx + r, dot_y + r], fill=color)
    title_font = _font(FONT_REGULAR, 20)
    draw.text((140, dot_y), "erickfp chat", font=title_font, fill=TEXT_BASE, anchor="lm")

    # ---------- Glow del titulo (blur cyan detras del texto verde) ------
    big_font = _font(FONT_BOLD, 132)
    title_text = "ErickFP"
    title_x, title_y = 76, 210

    glow_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_draw.text((title_x, title_y), title_text, font=big_font, fill=(0, 255, 255, 200))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(14))
    img = Image.alpha_composite(img.convert("RGBA"), glow_layer).convert("RGB")
    draw = ImageDraw.Draw(img)

    draw.text((title_x, title_y), title_text, font=big_font, fill=GREEN)

    # ---------- Subtitulo (tagline, wrap manual a ~2 lineas) ----------
    sub_font = _font(FONT_REGULAR, 33)
    subtitle_lines = [
        "harness agéntico CLI gobernado por",
        "el método cartesiano",
    ]
    sub_y = 372
    for line in subtitle_lines:
        draw.text((title_x, sub_y), line, font=sub_font, fill=TEXT_BASE)
        sub_y += 46

    # ---------- Ciclo cogito (linea de comando, acento cyan) ----------
    cmd_font = _font(FONT_REGULAR, 27)
    cmd_text = "duda → divide → ordena → enumera"
    cmd_y = 480
    draw.text((title_x, cmd_y), cmd_text, font=cmd_font, fill=CYAN)

    # ---------- Footer: repo + cursor parpadeante (estatico) ----------
    footer_font = _font(FONT_REGULAR, 24)
    footer_text = "github.com/ErickFP7314/harnes-erickfp"
    footer_y = HEIGHT - 56
    draw.text((title_x, footer_y), footer_text, font=footer_font, fill=TEXT_MUTED, anchor="lm")
    footer_w = _text_w(draw, footer_text, footer_font)
    draw.text(
        (title_x + footer_w + 14, footer_y),
        "_",
        font=footer_font,
        fill=CYAN,
        anchor="lm",
    )

    assert img.size == (WIDTH, HEIGHT), f"Tamano inesperado: {img.size}"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")
    print(f"OK: {out_path} generado ({img.size[0]}x{img.size[1]})")


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    out_path = repo_root / "assets" / "img" / "og-image.png"
    generate(out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
