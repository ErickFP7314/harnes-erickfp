# Design: landing-webpage — Web de presentación de ErickFP

## Technical Approach

Sitio estático vanilla multi-página en `WebPage/` (aislado del harness Python), fiel al proposal: 2 páginas HTML planas + un sistema de tema CSS con tokens de la paleta de `theme.py`, JS mínimo sin dependencias, y un único paso de build opcional en Python (arte ASCII) que sigue el patrón existente `scripts/gen_portada.py` → asset precomputado. Todo el output generado se **commitea**: el sitio abre con doble click (file://) sin toolchain, cumpliendo el success criterion.

## Architecture Decisions

### D1 — Estructura de archivos
```
WebPage/
├── index.html                  # landing (arte inyectado entre marcadores)
├── guia.html                   # guía con sidebar (plana, no guia/index.html)
├── assets/
│   ├── css/theme.css           # tokens: paleta theme.py, tipografía, componentes base
│   ├── css/landing.css         # secciones de index
│   ├── css/guia.css            # layout sidebar
│   ├── css/portada.css         # GENERADO: clases de color c0..cN del arte
│   ├── js/main.js              # nav, scrollspy, tabs, copy-button, reveal
│   ├── js/terminal-demo.js     # demo animada del gate y/n
│   └── img/                    # favicon, og-image
└── scripts/gen_portada_web.py  # build-time: _portada_asset.py → HTML+CSS
```
**Rechazado:** `guia/index.html` (URLs limpias en hosting) — rompe la simplicidad de rutas relativas y el test de doble click; 2 páginas no lo ameritan. **Rationale:** flat = deploy directo a GitHub Pages/Netlify y file:// sin fricción.

### D2 — Arte ASCII responsive (149 columnas)
| Aspecto | Decisión |
|---|---|
| Mecanismo | `<pre>` con font-size fluido: `font-size: clamp(3px, 1.1vw, 11px)` (≈100vw/90: 149 chars × ~0.6ch/em); `line-height: 1.05`; sin letter-spacing. Calibrar el factor en apply contra el font stack real |
| Mobile | Escala siempre hacia abajo, **sin scroll horizontal ni versión recortada**: el arte es composición abstracta decorativa (`aria-hidden="true"`), no texto legible — a 360px queda como textura, aceptable |
| Commit | El HTML/CSS generado **se commitea** (cierra la pregunta abierta del proposal); se regenera solo si cambia `_portada_asset.py` |

**Rechazado:** contenedor con scroll (rompe la inmersión del hero); versión recortada mobile (segundo asset que mantener, YAGNI). **Rationale:** el riesgo "ilegible en mobile" no aplica a arte abstracto; cero JS, cero assets extra.

### D3 — Script build-time `gen_portada_web.py`
- Python stdlib puro; carga `ROWS` importando `src/erickfp/ui/_portada_asset.py` vía `importlib` (path relativo al repo root) — **solo lectura**, jamás toca código del harness.
- Emite: (a) fragmento `<pre class="portada">` con `<span class="cK">run</span>` por segmento — los segmentos ya vienen fusionados por color en el asset (~500 spans, ~15-20KB vs 319KB de portada.html); segmentos whitespace con fg blanco se emiten como texto plano sin span; bg uniforme `#222222` se fija una vez en el `<pre>`, nunca por span. (b) `assets/css/portada.css` con el mapa color→clase (16 colores).
- Inyección **idempotente** en `index.html` entre marcadores `<!-- PORTADA:BEGIN --> … <!-- PORTADA:END -->` (reemplaza el bloque, re-ejecutable).
- Self-check integrado: asserts de 25 filas × 149 columnas expandidas (sin pytest; el gate de calidad es D7).

**Rechazado:** grid de spans 1-por-carácter (el 319KB original); fetch() del fragmento en runtime (CORS bloquea file://).

### D4 — Demo terminal animada (gate y/n)
- Guion declarativo: array de pasos `{type: 'cmd'|'out'|'gate'|'pause', text, delay}` en `terminal-demo.js`. Contenido: `$ erickfp chat` → prompt usuario → `⏺ bash(pytest -q)` → `¿aprobar? [y/n] › y` (acento verde) → `✓ ejecutando… 126 passed` → segunda tool con gate esperando (cursor parpadeante).
- Motor: `async/await` + sleep promisificado, append a `textContent` char a char; cursor `█` con blink CSS `steps(2)`. `IntersectionObserver` arranca al entrar en viewport; botón "▶ replay".
- `prefers-reduced-motion` → render estático del estado final (sin animar).

**Rechazado:** requestAnimationFrame (overkill: la cadencia es de decenas de ms, no per-frame); CSS-only typing con `steps()` (no soporta multilínea con colores por token); GIF/video (pesado, no encaja con estética).

### D5 — Navegación (MVP vs descartado)
| Entra en MVP | Descartado (YAGNI) |
|---|---|
| Nav sticky: anclas Features / Cómo funciona / Comparativa / Guía + CTA GitHub | Command-palette-lite |
| Scroll suave (`scroll-behavior: smooth`, CSS puro) | Scroll-driven animations complejas |
| Scrollspy con IntersectionObserver: link activo con prefijo prompt `> ` (estilo terminal) | FAQ acordeón |
| Reveal-on-scroll simple (clase `.visible` vía IntersectionObserver) | Carousel de testimonios |
| Sidebar de `guia.html`: anclas estáticas hardcoded + mismo scrollspy | Sidebar generado desde markdown |

### D6 — Pipeline de diseño en apply (Stitch → Magic → ui-ux-pro-max)
| Etapa | Pide | Produce | Fallback si falla |
|---|---|---|---|
| 0. Manual (siempre) | — | Esqueleto HTML semántico + `theme.css` con tokens (paleta/tipografía/spacing) | ES el fallback: ya cumple criterios |
| 1. Stitch MCP | Diseño base por sección con paleta exacta + anatomía de la exploración | Mockup/HTML de referencia visual | Saltar → etapa 0 manda |
| 2. Magic MCP | Mejora componente a componente (tabs, cards, tabla, tweet-cards) | Snippets que se **normalizan** a los tokens de theme.css | Saltar componente |
| 3. Skill ui-ux-pro-max | Pasada final: jerarquía, spacing, contraste, microinteracciones | Ajustes sobre CSS existente | Checklist D7 manual |

**Regla de integración:** el output de MCPs es INSUMO, nunca se pega crudo — todo se reescribe contra los tokens de `theme.css` (una sola fuente de verdad visual).

### D7 — Gate de calidad (sin pytest)
Checklist bloqueante para verify:
1. HTML válido: W3C validator (o `tidy -e -q` local) — 0 errores en ambas páginas.
2. Link/asset check: todo `href`/`src` resuelve (one-liner Python o revisión manual).
3. file:// test: doble click abre index y guia con todo funcional (sin fetch, rutas relativas).
4. Responsive 360/768/1440: sin overflow horizontal (excepto tabla comparativa, scroll intencional).
5. Contraste: texto base `#D0D0D0` sobre `#222222` (≥4.5:1); neón solo acentos/headings.
6. `prefers-reduced-motion` respetado; arte `aria-hidden`.
7. Self-check de `gen_portada_web.py` pasa (25×149).
Lighthouse manual: opcional, no bloqueante.

### D8 — Testimonios y comparativa
- Testimonios: `<figure class="tweet-card">` (blockquote + figcaption con avatar emoji/ASCII, nombre, @handle) en CSS grid 3→1 columnas; disclaimer visible "testimonios ficticios". Datos hardcoded en HTML — sin JSON+JS (mejor para file:// y SEO).
- Comparativa: `<table>` semántica (`<th scope>`) ErickFP vs Claude Code vs aider vs harness genérico, celdas ✓/— con color de acento, wrapper `overflow-x: auto` en mobile. Estilo bun.sh.

## Data Flow (build + runtime)

```
_portada_asset.py (ROWS 25×149, solo lectura)
        │  WebPage/scripts/gen_portada_web.py (manual, idempotente)
        ▼
index.html [PORTADA:BEGIN/END] + assets/css/portada.css   ← commiteados
        ▼
Browser (file:// o hosting estático)
   ├── theme.css → landing.css / guia.css / portada.css
   └── main.js (nav/scrollspy/tabs/copy) + terminal-demo.js (IntersectionObserver)
```

## File Changes

Todo nuevo, según árbol de D1 (10 archivos + img). Cero modificaciones fuera de `WebPage/`.

## Testing Strategy

Sin pytest (frontend estático): gate D7 como checklist de verify + self-check embebido en el script de build. Strict TDD no aplica a este cambio (no hay runner para HTML/CSS); documentado como excepción consciente.

## Migration / Rollout

No aplica. `WebPage/` aislada; rollback = revertir commits o borrar carpeta (proposal).

## Open Questions

- [ ] Factor exacto del clamp del arte (depende del font stack final; calibrar en apply).
- [ ] Font stack: system monospace vs webfont (JetBrains Mono self-hosted añade ~100KB; decidir en apply con Stitch).
- [ ] Ruta de deploy (GitHub Pages workflow vs /docs) — fuera de scope, decidir post-archive.
