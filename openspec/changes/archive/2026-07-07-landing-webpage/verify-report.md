# Verify Report: landing-webpage

**Cambio**: landing-webpage
**Fecha**: 2026-07-07
**Modo**: Standard (excepción TDD documentada en design — gate = checklist D7, no pytest)
**Veredicto**: **PASS** (0 CRITICAL, 2 WARNING, 2 SUGGESTION)

Verificación independiente por sdd-verify: lectura completa de las 4 specs, design D1-D8, tasks.md y de todos los archivos de `WebPage/`, más re-ejecución real de los checks reproducibles del gate D7.

---

## Completeness (tasks.md)

| Métrica | Valor |
|---|---|
| Tareas totales | 29 (Lote A 5 + B 14 + C 3 + D 7) |
| Completas `[x]` | 29 |
| Incompletas | 0 |

Las marcas coinciden con el estado real del código; cada tarea D1-D7 trae evidencia concreta y reproducible. C2 (Magic MCP) marcada como fallback tolerado (API key inválida) según design D6 — no es hallazgo.

## Checks re-ejecutados (evidencia real, no reportada)

| Check (D7) | Comando | Resultado |
|---|---|---|
| D1/D2 HTML válido + links/anclas/assets | `.venv/bin/python WebPage/scripts/check_html.py` | ✅ exit 0 — "OK: 0 errores en index.html y guia.html" (html5lib strict + ids duplicados, headings, un solo h1, alt, anclas cruzadas) |
| D7 self-check portada | `.venv/bin/python WebPage/scripts/gen_portada_web.py` | ✅ "OK: 25x149 verificado." (15 colores) |
| D7 idempotencia | sha256sum de `index.html` + `portada.css` antes/después de re-ejecutar | ✅ checksums idénticos |
| Fidelidad del arte (spec web-portada-asset R2) | script propio: strip de spans del bloque PORTADA vs `ROWS` del asset | ✅ 25 filas, todas de 149 cols, **char-exact** vs ROWS; los 15 fg no-blancos presentes en portada.css; bg único `#222222` fijado una vez en el `<pre>` |
| Cero dependencias externas de runtime | grep `@import`/CDN/fonts/`fetch(` en HTML/CSS/JS | ✅ 0 (único match: comentario en theme.css). 6 hipervínculos externos de navegación (github.com ×5, aistudio.google.com ×1), todos `target="_blank" rel="noopener noreferrer"` — excepción intencional spec R9/design, el sitio funciona 100% offline |
| D3 file:// funcional | `google-chrome --headless=new --dump-dom file://…` ambas páginas | ✅ exit 0 ambas; títulos correctos; 14 `feature-card` presentes en el DOM renderizado |
| D5 contraste WCAG | script Python (luminancia relativa) sobre 13 pares en uso | ✅ todos ≥4.5:1 — text-base/bg-base 10.32:1, muted/bg-base 4.92:1, muted/bg-inset 5.38:1 (fix .table-wrapper), text-base/#2E2E2E 8.80:1 (fix .terminal-title), cyan 12.69:1, verde 11.59:1, btn-primary 12.69:1. El único FAIL calculado (muted/bg-elevated 4.44:1) es el par PRE-fix, ya sin uso en el CSS actual |
| `src/` intocado tras re-generar | `git status --porcelain src/` | ✅ vacío (solo lectura confirmada) |
| D6 reduced-motion + aria-hidden | inspección de código + evidencia CDP del apply | ✅ `terminal-demo.js` no toca el `<pre>` estático si `prefers-reduced-motion`, oculta replay; theme.css anula animaciones/reveal; `aria-hidden="true"` en el arte (emitido por el generador) |
| D4 responsive | inspección CSS + evidencia CDP del apply (360/768/1440) | ✅ `body{overflow-x:hidden}`, arte `clamp(3px,1.1vw,11px)` + `overflow:hidden`, única excepción `.comparison-table` (min-width 640px) dentro de `.table-wrapper{overflow-x:auto}` — exactamente lo que D7.4 permite; sidebar guía se apila a ≤860px |

## Spec Compliance (22 requirements, 30 escenarios — muestreados todos)

### web-landing (9/9 ✅)
| Req | Evidencia | Estado |
|---|---|---|
| R1 Hero arte+one-liner+CTA | index.html:35-78 (portada, one-liner cartesiano, 2 CTA) | ✅ |
| R2 Idea + ≥5 diferenciadores | index.html:81-118 — exactamente los 5 exigidos como `<li>` distintos | ✅ |
| R3 Ciclo Cogito 4 fases + comando | index.html:120-152, orden duda→divide→ordena→enumera con snippet cada una | ✅ |
| R4 Tabs instalación, npm honesto, copy 1-clic | index.html:155-204 — npm con badge "coming soon" en tab y panel, sin comando npm; pip/uv/git reales con `copy-btn data-copy` exacto | ✅ |
| R5 Demo terminal gate y/n + legible sin JS | `#demo-output` trae el guion completo estático en el HTML; terminal-demo.js anima solo si puede (nunca borra antes de confirmar) | ✅ |
| R6 14 features | 14 `<article class="feature-card">` confirmadas también en DOM renderizado | ✅ |
| R7 Comparativa ≥4 dimensiones, honesta | 5 dimensiones; concede ✓/△ a terceros donde corresponde (aider provider-agnostic ✓, Claude Code gate △), texto oculto sí/no/parcial para lectores de pantalla | ✅ |
| R8 Testimonios ficticios + disclaimer | disclaimer visible en sección + refuerzo en footer; nombres/handles evidentemente inventados | ✅ |
| R9 Nav + footer sin enlaces rotos | nav sticky con secciones/guía/GitHub; check_html verifica anclas y rutas → 0 errores | ✅ |

### web-guia (4/4 ✅)
R1 contenido completo (qué es, requisitos, instalación, 6 comandos `init/chat/duda/divide/ordena/enumera`, slash commands `/help /model /tools /clear /tokens`, troubleshooting; snippets EN, prosa ES) · R2 sidebar con anclas a las 8 secciones, apilada y accesible a 360px · R3 snippets con `copy-btn` y comando exacto · R4 mismo theme.css + retorno a index (logo, nav, "← Volver al inicio", footer).

### web-theme-terminal (5/5 ✅, ver WARNING-2)
R1 tokens de paleta exactos en `:root` (cyan/verde/bg + rampas theme.py) · R2 `--font-mono` con fallbacks aplicado a body/headings/code/buttons · R3 texto base `#D0D0D0`, neón solo acentos · R4 responsive 360→desktop, `--max-width:1200px` · R5 contraste AA verificado, landmarks header/nav/main/footer, un h1 por página (verificado por check_html), `:focus-visible` global, tabs con roving tabindex + flechas, skip-link.

### web-portada-asset (4/4 ✅)
R1 build-time, solo lectura de `src/` (verificado con git status tras re-ejecutar), sitio abre sin build (file:// exit 0) · R2 fidelidad char-exact y color-exact re-verificada independientemente · R3 clamp fluido sin scroll horizontal, `aria-hidden` · R4 regenerable e idempotente (sha256 idénticos).

## Coherence (design D1-D8)

| Decisión | ¿Seguida? |
|---|---|
| D1 estructura flat | ✅ árbol idéntico al diseñado |
| D2 clamp + aria-hidden + commit del generado | ✅ |
| D3 spans fusionados, bg una vez, marcadores idempotentes, self-check | ✅ (15 clases + blanco como texto plano ≈ los "16 colores" del design) |
| D4 demo declarativa async/await + IO + replay + reduced-motion | ⚠️ parcial — ver WARNING-1 |
| D5 nav sticky, scrollspy "> ", reveal, sidebar hardcoded | ✅ |
| D6 pipeline Stitch→Magic→ui-ux-pro-max tolerante a fallo | ✅ C1 ejecutado, C2 fallback documentado (tolerado), C3 aplicado |
| D7 gate de calidad | ✅ los 7 checks con evidencia real; 2 fixes de contraste aplicados por el gate (permitido) |
| D8 tweet-cards hardcoded + tabla semántica con wrapper | ✅ |

## Hallazgos

**CRITICAL** — Ninguno.

**WARNING** (desvíos tolerables, no bloquean archive):
1. **D4 parcial en la demo terminal**: el design pedía cursor `█` con blink `steps(2)` durante el tipeo y una "segunda tool con gate esperando"; lo implementado es un guion de 1 gate sin cursor visible durante la animación (el blink `steps(2)` existe solo en el caret del logo/footer). La spec web-landing R5 se cumple íntegra (secuencia hasta `[y/n]` con `y`, legible sin JS), por eso es desvío de design, no de spec.
2. **Colores fuera de la paleta theme.py**: `--accent-danger: #ff5f5f` (borde de callout-warning y fiction-disclaimer), los dots del titlebar (`#ff5f56/#ffbd2e/#27c93f`) y el fondo `#2e2e2e` del titlebar no provienen de la paleta cyan/verde/bg/blanco de la spec web-theme-terminal R1. Mitigantes: el danger está centralizado como token, los dots son chrome decorativo de ventana (spans vacíos) y ninguno se usa como color de acento de texto/interacción; contraste verificado donde aplica.

**SUGGESTION** (opcionales):
1. `assets/img/` solo contiene `favicon.svg`; el árbol D1 mencionaba también og-image y no hay meta tags OpenGraph — añadirlos mejoraría el share en redes (fuera de requisitos de spec).
2. Documentación: apply-progress dice "5 enlaces externos" pero son 6 (falta contar el crédito a byo-coding-agent en el footer de index). Todos en dominios permitidos por check_html.py; corregir el conteo al archivar.

## Veredicto

**PASS** — 29/29 tareas completas, 22/22 requirements implementados con evidencia de ejecución real, gate D7 re-verificado íntegro de forma independiente. Listo para `sdd-archive`.
