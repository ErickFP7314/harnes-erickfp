# Tasks: landing-webpage — Web de presentación de ErickFP

Orden de dependencia: **A → B → C → D** (secuencial entre lotes). Dentro de un lote, `(P)` = paralelizable; sin marca = secuencial respecto a la tarea anterior del mismo archivo. Gate de calidad = checklist D7 del design (no pytest, excepción TDD documentada).

## Lote A — Fundaciones

- [x] A1 Crear estructura `WebPage/`: `index.html`, `guia.html`, `assets/{css,js,img}/`, `scripts/` (design D1)
- [x] A2 `assets/css/theme.css`: tokens cyan `#00FFFF`/verde `#00FF00`/bg `#222222` + rampas (cyan `#00E6E6–#B3FFFF`, verde `#00E600–#99FF99`) + stack monospace con fallbacks (spec web-theme-terminal R1, R2)
- [x] A3 `scripts/gen_portada_web.py`: importlib de `ROWS` desde `src/erickfp/ui/_portada_asset.py` (solo lectura), emite `<pre class="portada">` con `<span>` por segmento ya fusionado + `portada.css` (mapa color→clase), inyección idempotente entre `<!-- PORTADA:BEGIN/END -->`, self-check `assert 25×149` (design D3, spec web-portada-asset R1, R2, R4)
- [x] A4 Ejecutar `gen_portada_web.py`; commitear `index.html` con arte inyectado + `portada.css` generado (spec web-portada-asset R1, R4)
- [x] A5 CSS responsive del arte: `font-size: clamp(3px, 1.1vw, 11px)`, `line-height: 1.05`, sin scroll horizontal, `aria-hidden="true"` en el `<pre>` (design D2, spec web-portada-asset R3)

## Lote B — Esqueleto de contenido (etapa 0 = fallback)

- [x] B1 `index.html` hero: arte + one-liner + CTA visible sin scroll en desktop (spec web-landing R1)
- [x] B2 `index.html` la idea + ≥5 diferenciadores: método cartesiano, trazabilidad ADR, gate default-deny + núcleo sagrado, provider-agnostic, free tier (spec web-landing R2)
- [x] B3 `index.html` ciclo Cogito narrativo: 4 fases secuenciales duda→divide→ordena→enumera, comando por fase (spec web-landing R3)
- [x] B4 `index.html` tabs instalación: npm (badge "coming soon" explícito) / pip / uv / git clone, todos copiables un clic (spec web-landing R4)
- [x] B5 `assets/js/terminal-demo.js`: guion declarativo de pasos, motor async/await, cursor blink `steps(2)`, `IntersectionObserver` de arranque, botón replay, fallback estático en `prefers-reduced-motion` (design D4, spec web-landing R5)
- [x] B6 `index.html` features grid: las 14 features del harness (spec web-landing R6)
- [x] B7 `index.html` tabla comparativa: ≥4 dimensiones verificables ErickFP vs Claude Code vs aider vs genérico, wrapper `overflow-x: auto` (spec web-landing R7, design D8)
- [x] B8 `index.html` testimonios ficticios: `<figure class="tweet-card">` + disclaimer de ficción visible (spec web-landing R8, design D8)
- [x] B9 `index.html` nav sticky (Features/Cómo funciona/Comparativa/Guía + CTA GitHub) + footer con créditos/disclaimer, sin enlaces rotos (spec web-landing R9)
- [x] B10 `assets/js/main.js`: scrollspy `IntersectionObserver` con prefijo `> ` en link activo + reveal-on-scroll (design D5)
- [x] B11 (P) `guia.html` contenido desde `docs/guia-de-uso.md`: qué es, requisitos, instalación, 6 comandos (`init/chat/duda/divide/ordena/enumera`), slash commands, troubleshooting (spec web-guia R1)
- [x] B12 `guia.html` sidebar con anclas hardcoded a cada sección, usable a 360px sin scroll horizontal (spec web-guia R2, design D5)
- [x] B13 `guia.html` snippets copiables un clic (spec web-guia R3)
- [x] B14 `guia.html` mismo tema visual + nav de regreso a `index.html`, reutiliza scrollspy de `main.js` (spec web-guia R4)

## Lote C — Pipeline de diseño (TOLERANTE A FALLO — si el MCP/skill no está, documentar y seguir con etapa 0)

- [x] C1 (P, tolerante) Invocar **Stitch MCP**: pedir mockup por sección con paleta exacta cyan/verde/`#222222`; produce diseño base de referencia (no se pega crudo) (design D6 etapa 1) — **(orquestador: mockup de referencia generado, proyecto Stitch 10425094107072139447)**
- [x] C2 (tolerante, depende de C1 si corrió) Invocar **Magic MCP**: mejorar componente a componente (tabs, cards, tabla comparativa, tweet-cards) usando C1 como referencia; normalizar todo el output a los tokens de `theme.css` antes de integrarlo (design D6 etapa 2) — **(no ejecutado: Magic MCP sin API key — fallback etapa 0, documentado)**
- [x] C3 (tolerante, depende de C2) Invocar skill **ui-ux-pro-max**: pasada final de jerarquía visual, spacing y contraste sobre `index.html` y `guia.html`; normalizar a tokens (design D6 etapa 3) — **ejecutado directamente (checklist ui-ux-pro-max aplicado a mano sobre theme.css/landing.css/guia.css/index.html/guia.html): tokens de z-index y glow neon añadidos, botones primario/secundario normalizados a paleta (cyan solido / verde borde) segun pistas Stitch, touch targets ≥44px (nav-links, nav-toggle, btn, copy-btn, tab-btn, sidebar guia), emojis de color reemplazados por glifos ASCII/monospace (avatares → iniciales, ⚠️ → [!]), comparativa con texto oculto sí/no/parcial ademas de glifo, scanlines sutiles (opacity 0.06) en hero, hover con borde+glow en feature-card/tweet-card/cogito-step (jerarquia sin depender solo de color), font-stack sin CDN documentado como decision diferida, footer con prompt `> _` parpadeante**

## Lote D — Gate de calidad (design D7, checklist bloqueante — sin pytest)

- [x] D1 Validar W3C/tidy: 0 errores en `index.html` y `guia.html` (D7.1) — (`scripts/check_html.py` con html5lib strict en el .venv del repo: "OK: 0 errores en index.html y guia.html")
- [x] D2 (P) Link/asset check: sin 404 internos, todas las rutas relativas (D7.2) — (check_html.py verifica href/src internos + anclas; 0 errores. `grep http/https`: solo 5 enlaces externos intencionales — CTA GitHub (spec R9) y aistudio.google.com/apikey (guía) — con target=_blank/rel=noopener; cero @import/CDN/fetch en runtime)
- [x] D3 (P) Test manual `file://` doble-click: ambas páginas funcionales sin servidor ni build (D7.3) — (headless Chrome real vía `file://` + CDP: `--dump-dom` exit 0 ambas páginas, cero errores/excepciones de consola JS capturados con Runtime.exceptionThrown/consoleAPICalled tras cargar y hacer scroll)
- [x] D4 Responsive 360/768/1440 sin overflow horizontal, salvo la tabla comparativa (intencional, con wrapper) (D7.4) — (screenshots headless Chrome vía CDP con device-metrics reales a 360/768/1440 para ambas páginas: sin overflow visible ni texto cortado; auditoría `getBoundingClientRect` confirma hero/nav/tabs/features/cogito/tweet-cards dentro de viewport; único elemento que excede su contenedor es `.comparison-table` dentro de `.table-wrapper` con `overflow-x:auto`, contenido por `body{overflow-x:hidden}` — sin scroll de página)
- [x] D5 (P) Contraste texto base `#D0D0D0` sobre `#222222` ≥4.5:1; verificar que cyan/verde puro solo aparecen como acentos (D7.5) — (script Python propio, fórmula de luminancia relativa WCAG, 15 pares reales del CSS: texto base 10.32:1, texto muted/bg-base 4.92:1, cyan/verde sobre bg-base 12.69:1/11.59:1, botones primario/secundario 11.59–13.71:1. 2 fixes aplicados tras detectar FAIL real: `.table-wrapper` sin bg propio heredaba `.section-alt`(bg-elevated #2A2A2A) → texto muted 4.44:1 bajo el mínimo, se agregó `background:var(--bg-inset)` → 5.38:1; `.terminal-title` con text-muted sobre `#2e2e2e` medía 4.20:1 → cambiado a `var(--text-base)` → 8.80:1. Todos los pares ≥4.5:1 tras el fix)
- [x] D6 (P) Verificar `prefers-reduced-motion` (demo terminal a estado final estático) + `aria-hidden` en el arte (D7.6) — (CDP `Emulation.setEmulatedMedia(prefers-reduced-motion:reduce)` real sobre index.html: `matchMedia` true, botón replay oculto, `#demo-output` muestra el texto final completo sin animar; `<pre class="portada" aria-hidden="true">` confirmado en index.html línea 38)
- [x] D7 Re-ejecutar self-check de `gen_portada_web.py` (25×149) antes de cerrar el cambio (D7.7) — (`.venv/bin/python WebPage/scripts/gen_portada_web.py` → "OK: 25x149 verificado."; checksums sha256 de index.html y portada.css idénticos antes/después de re-ejecutar → idempotente)
