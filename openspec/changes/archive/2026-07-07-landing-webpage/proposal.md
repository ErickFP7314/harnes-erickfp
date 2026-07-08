# Propuesta: landing-webpage — Web de presentación de ErickFP

## Intent

ErickFP (v0.1+v0.2 completados, 126+ tests) no tiene presencia web. Erick pide una landing de marketing en `WebPage/` (hoy vacía) que explique la idea del producto, sus diferenciadores frente a otros harnesses, todas sus características con navegación interesante, preview de instalación, guía de uso en subpágina, testimonios ficticios y el arte ASCII de portada con estética terminal neón. Éxito = sitio estático navegable, fiel a la paleta del tema (`cyan #00FFFF` / `verde #00FF00` sobre `#222222`), deployable sin toolchain.

## Scope

### In Scope
- `index.html`: hero + diferenciadores, instalación con tabs, demo terminal animada, grid de ~14 features, comparativa vs otros harnesses, Ciclo Cogito narrativo, testimonios ficticios, CTA + footer.
- `guia.html`: guía de uso con sidebar, traducida ~1:1 desde `docs/guia-de-uso.md`.
- Tema terminal compartido (CSS): paleta exacta de `theme.py`, monospace, neón solo en acentos.
- Script build-time `WebPage/scripts/gen_portada_web.py`: `_portada_asset.py` → HTML (`<pre>` + spans).

### Out of Scope
- Versión en inglés (estructura preparada, contenido diferido).
- Blog, newsletter, analytics, backend/formularios.
- Publicación real del paquete npm/pip; automatización de deploy (el sitio queda listo para GitHub Pages/Netlify).
- Cambios a cualquier código Python del harness (el script solo LEE el asset).

## Capabilities

### New Capabilities
- `web-landing`: página principal con todas sus secciones y navegación.
- `web-guia`: subpágina de guía con sidebar de navegación.
- `web-theme-terminal`: sistema visual compartido (paleta, tipografía, componentes base).
- `web-portada-asset`: pipeline build-time del arte ASCII 25×149 a HTML.

### Modified Capabilities
- Ninguna (no se toca ninguna capability del producto Python).

## Decisiones (con trade-offs)

| Decisión | Elección | Trade-off descartado |
|---|---|---|
| Stack | **Vanilla HTML/CSS/JS estático multi-página** | Astro/Next: componentes y markdown→HTML, pero meten node_modules + build step en un repo Python para solo 2 páginas; vanilla duplica header/footer (aceptable) y encaja con el pipeline Stitch/Magic que emite HTML/CSS |
| Idioma | **Español**, comandos/snippets/UI en inglés | Bilingüe duplica mantenimiento sin audiencia EN actual; docs y producto ya están en ES |
| npm no publicado | Tabs estilo opencode: `npm` con badge "coming soon" + `pip`/`uv`/`git clone` reales | Solo npm mentiría; solo pip ignora el pedido de Erick |
| Arte ASCII | Script build-time desde `_portada_asset.py` (mismo patrón que `scripts/gen_portada.py`) | Incrustar `portada.html` (319KB minificado, inviable) o recrear a mano (frágil, no regenerable) |

## Approach

1. Contenido desde el inventario de la exploración (14 features verificadas en código) y `docs/guia-de-uso.md`.
2. Anatomía basada en referencias: hero (openclaw), tabs de instalación (opencode), comparativa con checkmarks (bun), testimonios tweet-card (openclaw), Cogito como narrativa scroll (bun/warp).
3. Demo terminal con typing-effect en JS puro mostrando `erickfp chat` y el gate `¿aprobar? [y/n]` — el gancho visual diferenciador.
4. **Pipeline de diseño en apply (decisión de Erick)**: Stitch MCP genera el diseño base con la paleta terminal → Magic MCP mejora componentes → skill `ui-ux-pro-max` para retoque final.

## Affected Areas

| Área | Impacto | Descripción |
|---|---|---|
| `WebPage/index.html`, `WebPage/guia.html` | Nuevo | Páginas |
| `WebPage/assets/{css,js,img}/` | Nuevo | Tema, animaciones, arte generado |
| `WebPage/scripts/gen_portada_web.py` | Nuevo | Asset ASCII → HTML (solo lectura del asset) |

## Risks

| Riesgo | Prob. | Mitigación |
|---|---|---|
| MCPs de diseño (Stitch/Magic) fallan o no disponibles | Media | Fallback: diseño manual con paleta y anatomía ya definidas |
| Arte 149 cols ilegible en mobile | Alta | font-size fluido (clamp/vw) o versión recortada |
| Neón sobre #222 fatiga la vista | Media | Neón solo acentos; texto base gris claro |
| npm ficticio rompe confianza | Baja | Badge "coming soon" explícito |

## Rollback Plan

`WebPage/` está aislada y nada del producto depende de ella: revertir los commits del cambio (o borrar la carpeta) restaura el estado previo sin ningún efecto sobre el harness Python ni sus gates de calidad.

## Dependencies

- `src/erickfp/ui/_portada_asset.py` y `theme.py` (solo lectura) · `docs/guia-de-uso.md` (fuente de la guía) · MCPs Stitch/Magic + skill ui-ux-pro-max en fase apply.

## Success Criteria

- [ ] Landing explica producto + ≥5 diferenciadores; las ~14 features presentes.
- [ ] Tabs de instalación: npm (coming soon) + pip/uv/git reales, copiables.
- [ ] `guia.html` cubre `docs/guia-de-uso.md` con sidebar navegable.
- [ ] Testimonios ficticios como tweet-cards; arte ASCII fiel a la paleta, legible en mobile.
- [ ] Sitio abre en local con doble click (sin build obligatorio salvo el script del arte) y sin tocar código Python.
