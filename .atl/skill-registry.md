# Skill Registry — Harnes-ErickFP

Generado por sdd-init el 2026-07-03. Proyecto greenfield Python (harness agéntico ErickFP).

## User Skills (triggers relevantes)

| Skill | Trigger | Aplica a |
|-------|---------|----------|
| judgment-day | "judgment day", "review adversarial", "dual review", "juzgar" | Revisión adversarial paralela de código/artefactos |
| skill-creator | crear una nueva skill / documentar patrones para IA | Cuando ErickFP genere sus propias skills o docs de agente |
| issue-creation | crear un GitHub issue, reportar bug, pedir feature | Flujo issue-first del workspace |
| branch-pr | crear un pull request / preparar cambios para review | Flujo de PRs del workspace |

Skills omitidas por irrelevancia para este stack: familia hyperframes/video (10+), figma, ui-ux-pro-max, cqrs-nestjs, go-testing, embedded-captions y demás skills de video/diseño/otros stacks.

## Project Skills

Ninguna (no existe `.claude/skills/` ni `.agent/skills/` en el proyecto).

## Project Conventions

Ninguna aún (no hay CLAUDE.md/AGENTS.md a nivel proyecto). Fuente de convenciones del proyecto:
- `idea.md` — filosofía cartesiana + grafo ADR + stack obligatorio (Python, Typer, LiteLLM, sin SDKs nativos)
- `openspec/config.yaml` — contexto y reglas SDD
- Engram topic `architecture/erickfp-root-decisions` — las 12 decisiones raíz

## Compact Rules (inyectar en sub-agentes que escriban código)

```
## Project Standards (auto-resolved)
- Python >=3.10. CLI con Typer. Capa LLM: interfaz Provider propia; impl default LiteLLM → Gemini free tier. PROHIBIDO importar SDKs nativos (anthropic, openai, google-genai) fuera del adapter.
- Prioridades: 1) Legibilidad 2) Extensibilidad. Robustez innegociable en el permission gate. YAGNI dentro de cada fase.
- Toda decisión técnica debe trazar hasta un axioma de .ErickFP/core/Claude; decisiones nuevas se registran como ADR markdown con frontmatter (id, parents, estado, trade-off).
- El agente jamás edita .ErickFP/core/Claude ni core/agents (solo el humano, vía ADR amendment).
- Permission gate: toda tool call pregunta y/n; negación = tool result con is_error=true (nunca excepción).
- Instalar paquetes SOLO en venv del proyecto (nunca pip global; fallback ~/.venvs/global).
- Tema de color CLI: cyan #00FFFF primario (banners, prompts, fases) + verde #00FF00 acento (éxitos, aprobaciones). Rojo estándar para errores.
```
