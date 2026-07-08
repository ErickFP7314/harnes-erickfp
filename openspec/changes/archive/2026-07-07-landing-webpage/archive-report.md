# Archive Report: landing-webpage

**Archivado**: 2026-07-07
**Ruta**: `openspec/changes/archive/2026-07-07-landing-webpage/`
**Veredicto verify**: PASS (0 CRITICAL, 2 WARNING, 2 SUGGESTION)
**Artifact store**: hybrid (openspec/ + engram `sdd/landing-webpage/*`)

## Qué se entregó

Landing estática de presentación del producto ErickFP en `WebPage/`:
sitio vanilla HTML/CSS/JS con **cero dependencias Node, cero CDNs y cero
fuentes externas** (funciona por doble clic vía `file://`). Contenido en
español, tema terminal cyan `#00FFFF` + verde `#00FF00` sobre `#222222`,
stack monoespaciado JetBrains Mono. 2 páginas: landing (`index.html`) y
guía (`guia.html`). Portada ASCII web generada de forma idempotente.

## Capabilities creadas (4 nuevas, 0 modificadas)

- `web-landing` — página de presentación (hero, secciones, terminal demo)
- `web-guia` — página de guía/documentación
- `web-theme-terminal` — sistema de tema (tokens CSS, contraste WCAG AA)
- `web-portada-asset` — portada ASCII web generada (bloque + portada.css)

Merge de deltas → `openspec/specs/web-{landing,guia,theme-terminal,portada-asset}/spec.md`.

## Lotes de entrega

- **Lote A** — fundaciones (estructura WebPage/, theme.css con tokens de theme.py)
- **Lote B** — contenido (landing + guía, componentes, JS mínimo)
- **Lote C** — portada ASCII web + pulido
- **Lote D** — gate de calidad (validación HTML, contraste, responsive, reduced-motion)

Total: 29/29 tareas completadas.

## Verificación

- 22/22 requirements cumplidos.
- Gate Lote D: validación HTML5 (0 errores), contraste WCAG AA ≥4.5:1
  (2 fallos reales corregidos: `.table-wrapper` 4.44→5.38:1, `.terminal-title`
  4.20→8.80:1), responsive real 360/768/1440 vía CDP headless Chrome,
  `prefers-reduced-motion` respetado, sin CDNs externos.

### WARNINGs aceptados (2)

1. La terminal demo no tiene cursor parpadeante `█` ni el segundo paso de
   herramienta con gate y/n descritos en design D4 (simplificación aceptada).
2. Colores decorativos del titlebar (#ff5f56/#ffbd2e/#27c93f) y `--accent-danger`
   quedan fuera de la paleta estricta cyan/verde (decorativos, aceptados).

### SUGGESTIONs pendientes (2, no bloqueantes)

1. Faltan metas OpenGraph + `og-image.png` (1200×630) para previews sociales.
2. apply-progress mencionaba "5 external links" pero hay 6 (falta crédito
   footer a byo-coding-agent) — discrepancia de conteo, no defecto funcional.

Ambas quedan como candidatas para la mejora visual post-ciclo.

## Deploy

- **Vivo en**: https://erickfp7314.github.io/harnes-erickfp/
- Workflow: `.github/workflows/deploy-pages.yml` (auto-deploy en push a `main`
  que toque `WebPage/**`). GitHub Pages gratis (repo público).

## Verificación de integridad del archive

Copia byte-idéntica confirmada por `diff -r` externo del orquestador
(design.md, proposal.md, tasks.md, verify-report.md y specs/ todos idénticos
al original) — sin la corrupción silenciosa que ocurrió en el archive de v0-2.

## Estado del ciclo

**COMPLETO Y CERRADO.** `next_recommended: none`.
