"""WebPage/scripts/check_html.py -- gate de calidad D1 (validacion HTML) +
D2 (link/asset check) del cambio landing-webpage.

No requiere `tidy` (no disponible en este entorno): usa `html5lib` en modo
estricto como validador W3C-like, mas un set de chequeos propios que tidy no
cubre de forma directa (ids duplicados, tags sin cerrar via stack de
html.parser, alt en <img>, un solo <h1>, jerarquia de headings sin saltos,
enlaces/assets rotos, URLs absolutas locales, dominio externo no permitido).

Uso:
    .venv/bin/python WebPage/scripts/check_html.py

Exit code 0 si CERO errores en ambas paginas; 1 si hay al menos un error.
Dependencia: html5lib (instalado solo en el venv del repo, nunca en el
Python global -- ver CLAUDE.md).
"""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

try:
    import html5lib
except ImportError:  # pragma: no cover
    print(
        "ERROR: falta html5lib. Instala con: "
        ".venv/bin/python -m pip install html5lib",
        file=sys.stderr,
    )
    sys.exit(2)

WEBPAGE_DIR = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "guia.html"]

VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

ALLOWED_EXTERNAL_DOMAINS = {
    "github.com",
    "aistudio.google.com",
}

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class StructuralChecker(HTMLParser):
    """Recorre el documento una sola vez y colecta: stack de tags para
    detectar tags sin cerrar / mal anidados, ids (para duplicados), <img>
    sin alt, headings en orden de documento, y todos los href/src con su
    posicion (linea) para el link/asset check."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []
        self.unclosed_errors: list[str] = []
        self.ids: list[str] = []
        self.img_missing_alt: list[int] = []
        self.headings: list[tuple[str, int]] = []  # (tag, line)
        self.links: list[tuple[str, str, int]] = []  # (attr, value, line)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_d = dict(attrs)
        line = self.getpos()[0]

        if "id" in attrs_d and attrs_d["id"]:
            self.ids.append(attrs_d["id"])

        if tag in HEADING_TAGS:
            self.headings.append((tag, line))

        if tag == "img" and not attrs_d.get("alt"):
            self.img_missing_alt.append(line)

        for attr_name in ("href", "src"):
            if attr_name in attrs_d and attrs_d[attr_name] is not None:
                self.links.append((attr_name, attrs_d[attr_name], line))

        if tag not in VOID_ELEMENTS:
            self.stack.append((tag, line))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Self-closed explicitamente (<tag ... />): tratar igual que
        # start + no push (no requiere cierre).
        self.handle_starttag(tag, attrs)
        if tag not in VOID_ELEMENTS and self.stack and self.stack[-1][0] == tag:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        line = self.getpos()[0]
        if not self.stack:
            self.unclosed_errors.append(
                f"linea {line}: </{tag}> de cierre sin ninguna etiqueta abierta"
            )
            return
        top_tag, top_line = self.stack[-1]
        if top_tag == tag:
            self.stack.pop()
            return
        # Buscar si el tag existe mas abajo en el stack (mal anidado)
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                unclosed = self.stack[i + 1:]
                for u_tag, u_line in unclosed:
                    self.unclosed_errors.append(
                        f"linea {u_line}: <{u_tag}> nunca se cerro antes de "
                        f"</{tag}> (linea {line})"
                    )
                del self.stack[i:]
                return
        self.unclosed_errors.append(
            f"linea {line}: </{tag}> no coincide con ninguna etiqueta abierta"
        )


def check_html5lib_strict(html_text: str, name: str) -> list[str]:
    """Parsea con html5lib en modo estricto (strict=True) y colecta errores
    de parseo W3C-like. Este es el reemplazo de `tidy` (no instalado)."""
    errors: list[str] = []
    parser = html5lib.HTMLParser(strict=True)
    try:
        parser.parse(html_text)
    except Exception as exc:  # html5lib lanza ParseError en modo strict
        errors.append(f"{name}: html5lib strict parse error: {exc}")
    # Ademas, en modo NO estricto html5lib acumula errorLog utilizable
    # incluso si no lanza excepcion -- lo capturamos tambien para no perder
    # advertencias silenciosas.
    lenient_parser = html5lib.HTMLParser(strict=False)
    lenient_parser.parse(html_text)
    for err in lenient_parser.errors:
        # err es (position, errorcode, datavars)
        position, errorcode, datavars = err
        errors.append(f"{name}: linea {position[0]} col {position[1]}: {errorcode} {datavars}")
    return errors


def check_headings(headings: list[tuple[str, int]], name: str) -> list[str]:
    errors: list[str] = []
    h1_count = sum(1 for tag, _ in headings if tag == "h1")
    if h1_count != 1:
        errors.append(f"{name}: se esperaba exactamente 1 <h1>, se encontraron {h1_count}")

    last_level: int | None = None
    for tag, line in headings:
        level = int(tag[1])
        if last_level is not None and level > last_level + 1:
            errors.append(
                f"{name}: linea {line}: salto de jerarquia de heading "
                f"h{last_level} -> h{level} (no debe saltar niveles)"
            )
        last_level = level
    return errors


def check_duplicate_ids(ids: list[str], name: str) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    dupes: set[str] = set()
    for id_value in ids:
        if id_value in seen:
            dupes.add(id_value)
        seen.add(id_value)
    for dupe in sorted(dupes):
        errors.append(f"{name}: id duplicado '{dupe}'")
    return errors


def check_links(
    links: list[tuple[str, str, int]],
    name: str,
    own_ids: set[str],
    ids_by_page: dict[str, set[str]],
) -> list[str]:
    errors: list[str] = []
    for attr_name, value, line in links:
        if not value:
            errors.append(f"{name}: linea {line}: {attr_name} vacio")
            continue

        if value.startswith("file://"):
            errors.append(f"{name}: linea {line}: URL absoluta local prohibida: {value}")
            continue

        if value.startswith("mailto:") or value.startswith("tel:"):
            continue

        parts = urlsplit(value)

        if parts.scheme in ("http", "https"):
            domain = parts.netloc.replace("www.", "")
            if not any(domain == d or domain.endswith("." + d) for d in ALLOWED_EXTERNAL_DOMAINS):
                errors.append(
                    f"{name}: linea {line}: dominio externo no permitido: {domain} ({value})"
                )
            continue

        # Ancla pura dentro de la misma pagina
        if value.startswith("#"):
            anchor_id = value[1:]
            if anchor_id and anchor_id not in own_ids:
                errors.append(
                    f"{name}: linea {line}: ancla #{anchor_id} sin elemento destino en esta pagina"
                )
            continue

        # Ruta relativa: puede incluir ancla (pagina.html#seccion)
        path_part = parts.path
        anchor_part = parts.fragment

        if path_part:
            target = (WEBPAGE_DIR / path_part).resolve()
            if not target.exists():
                errors.append(
                    f"{name}: linea {line}: asset/pagina relativo no existe en disco: {path_part}"
                )
            elif anchor_part:
                target_ids = ids_by_page.get(path_part, None)
                if target_ids is not None and anchor_part not in target_ids:
                    errors.append(
                        f"{name}: linea {line}: ancla #{anchor_part} sin elemento destino en {path_part}"
                    )
        elif anchor_part:
            # value tipo "#foo" ya cubierto arriba; este caso es defensivo
            if anchor_part not in own_ids:
                errors.append(
                    f"{name}: linea {line}: ancla #{anchor_part} sin elemento destino en esta pagina"
                )
    return errors


def main() -> int:
    all_errors: list[str] = []
    parsed_pages: dict[str, StructuralChecker] = {}
    ids_by_page: dict[str, set[str]] = {}

    for page in PAGES:
        path = WEBPAGE_DIR / page
        html_text = path.read_text(encoding="utf-8")

        checker = StructuralChecker()
        checker.feed(html_text)
        checker.close()
        parsed_pages[page] = checker
        ids_by_page[page] = set(checker.ids)

    for page in PAGES:
        checker = parsed_pages[page]
        html_text = (WEBPAGE_DIR / page).read_text(encoding="utf-8")

        all_errors.extend(check_html5lib_strict(html_text, page))
        all_errors.extend(checker.unclosed_errors)
        all_errors.extend(check_duplicate_ids(checker.ids, page))
        if checker.img_missing_alt:
            for line in checker.img_missing_alt:
                all_errors.append(f"{page}: linea {line}: <img> sin atributo alt")
        all_errors.extend(check_headings(checker.headings, page))
        all_errors.extend(
            check_links(checker.links, page, ids_by_page[page], ids_by_page)
        )

    if all_errors:
        print(f"FALLO: {len(all_errors)} error(es) encontrados:\n")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print("OK: 0 errores en index.html y guia.html (html5lib strict + checks propios D1/D2).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
