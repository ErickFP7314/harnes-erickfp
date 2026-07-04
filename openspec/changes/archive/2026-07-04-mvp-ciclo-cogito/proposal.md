# Propuesta: MVP núcleo cartesiano de ErickFP (Ciclo Cogito)

## Intent

ErickFP nace para **aprender construyendo** un harness agéntico (decisión raíz 1). Hoy el repo es greenfield: no hay agente ejecutable ni forma de gobernar el trabajo del modelo con el método cartesiano de `idea.md`. Este MVP entrega el núcleo mínimo que hace real la filosofía: un agente CLI que pide permiso siempre, habla con un LLM vía interfaz propia, y estructura el trabajo en fases cartesianas bloqueantes (el **Ciclo Cogito**) gobernadas por hooks acumulativos y trazables al grafo ADR. Éxito = `erickfp init && erickfp duda → divide → ordena → enumera` produce artefactos encadenados sin que el agente jamás toque `core/*`.

## Scope

### In Scope
- **`cli-init`**: `erickfp init` genera `.ErickFP/` (core/Claude, core/agents, adr/, memory/, hooks/) con plantillas raíz.
- **`agent-loop`**: `erickfp chat` (REPL texto plano) + loop interno; permission gate y/n, negación → tool_result `is_error=true` (nunca excepción).
- **`provider-layer`**: interfaz Provider propia (Message/Block/ToolDef/Response) + adapter LiteLLM → Gemini 3 Flash; preserva thought signatures en multi-turno.
- **`tool-registry`**: interfaz Tool + registry con orden estable; tools bash, read_file, write_file.
- **`ciclo-cogito`**: fases secuenciales bloqueantes `duda` (Evidencia, exige spec clara y distinta) → `divide` (Análisis) → `ordena` (Síntesis) → `enumera` (Enumeración); cada fase emite artefacto markdown que alimenta la siguiente; modos interactivo/auto; usa roles de core/agents (Planner en duda/divide, Coder en ordena, Reviewer en enumera).
- **`phase-hooks`**: hooks PreToolUse/PostToolUse/PhaseStart/PhaseEnd; MVP incluye hook que protege `core/*` (siempre) y hook pre-síntesis que valida trazabilidad al grafo ADR; restricciones se acumulan por fase.
- **`memory-store`**: interfaz Store (save/recall/preamble) + impl SQLite; MVP persiste historial de decisiones/sesiones del ciclo.

### Out of Scope (fases futuras)
- TUI Textual, subagentes, compaction, MCP, PermissionPolicy avanzada, embeddings.

## Capabilities

### New Capabilities
- `cli-init`: scaffolding de `.ErickFP/` con plantillas raíz.
- `agent-loop`: REPL + loop + permission gate.
- `provider-layer`: interfaz Provider + adapter LiteLLM/Gemini.
- `tool-registry`: interfaz Tool + registry + 3 tools.
- `ciclo-cogito`: comandos por fase (duda/divide/ordena/enumera) con artefactos encadenados.
- `phase-hooks`: hooks por fase con restricciones acumulativas.
- `memory-store`: Store SQLite de decisiones/sesiones.

### Modified Capabilities
- None (greenfield).

## Approach

Paquete `erickfp` con venv propio, `pyproject.toml`, Typer como CLI. Arquitectura por capas de la guía byo-coding-agent traducida a Python: `api` sin dependencias (tipos Provider), lógica nunca depende de UI, glue arriba. El SDK del LLM se importa **solo** en el adapter LiteLLM. El Ciclo Cogito es análogo a Spec Kit (`/specify→/plan→/tasks→/implement`) y al ciclo SDD: fases obligatorias que encadenan artefactos markdown. Los hooks aplican el patrón "el modelo propone, el harness dispone determinísticamente". Naming validado: **Ciclo Cogito** con fases `duda / divide / ordena / enumera` — conservan el método cartesiano y son verbos de acción CLI claros (recomendado adoptar tal cual).

**Trazabilidad a axiomas raíz** (core/Claude vía decisiones raíz):
- provider-layer → decisión 4 (Provider propia, prohibido SDK nativo).
- agent-loop → decisión 10 (preguntar siempre) + 5 (alcance MVP).
- phase-hooks → decisión 9 (agente no edita core, solo humano) + 8 (grafo ADR).
- ciclo-cogito → decisión 1 (aprender construyendo) + `idea.md` (método cartesiano).
- memory-store → decisión 7 (Store SQLite). cli-init → decisión 8 (estructura ADR).

## Affected Areas

| Área | Impacto | Descripción |
|------|---------|-------------|
| `pyproject.toml`, `.venv/` | New | Paquete `erickfp`, deps Typer + LiteLLM |
| `src/erickfp/cli.py` | New | Comandos Typer (init, chat, duda/divide/ordena/enumera) |
| `src/erickfp/provider/` | New | Interfaz Provider + adapter LiteLLM |
| `src/erickfp/tools/` | New | Interfaz Tool + registry + bash/read/write |
| `src/erickfp/cogito/` | New | Fases del ciclo + orquestación de artefactos |
| `src/erickfp/hooks/` | New | Motor de hooks por fase |
| `src/erickfp/memory/` | New | Store SQLite |
| `.ErickFP/` (runtime) | New | Generado por `init`: core, adr, memory, hooks |

## Risks

| Riesgo | Prob. | Mitigación |
|--------|-------|------------|
| Gemini 3 pierde razonamiento en multi-turno | Med | Preservar thought signatures en el adapter; test de round-trip |
| Activar billing GCP elimina free tier | Med | Documentar en init; default flash gratis, no exigir billing |
| Permission gate con fuga (tool ejecuta sin y/n) | High | Gate en capa harness (no en tool/prompt); default = no; tests exhaustivos |
| Hook no bloquea edición de core/* | High | Hook de protección core como PreToolUse siempre activo, cubierto por test |
| Sobre-abstracción prematura (YAGNI) | Med | Simplicidad como regla de fase; interfaz gana su lugar solo con 2ª impl |
| Fases del ciclo acopladas / no bloqueantes | Med | Artefacto markdown por fase como contrato; fase falla si falta el previo |

## Rollback Plan

Cambio aislado en un paquete nuevo sin dependencias previas. Rollback = descartar el commit/rama (`git`) del paquete `erickfp` y borrar `.venv/` y `.ErickFP/` generados. No hay migraciones ni estado externo que revertir; el SQLite de memoria vive en `.ErickFP/memory/` y se elimina con el directorio. `core/Claude` y `core/agents` son de solo-lectura para el agente, así que ningún axioma raíz puede corromperse.

## Dependencies

- Python >=3.10 en venv propio; Typer, LiteLLM.
- Cuenta Gemini free tier (API key) para `chat` y fases del ciclo; el resto de la CLI funciona sin red.
- La primera fase de tareas instala pytest+ruff y activa `strict_tdd: true`.

## Success Criteria

- [x] `erickfp init` crea `.ErickFP/` completo con plantillas raíz.
- [x] `erickfp chat` conversa vía Gemini 3 Flash y ejecuta tools solo tras y/n; negar produce tool_result con `is_error=true`. (Nota: el default real, por decisión de usuario ADR-001, es `gemini/gemma-4-26b-a4b-it`, no `gemini-3-flash` — ver `verify-report.md` WARNING-1.)
- [x] Ningún SDK nativo del LLM se importa fuera del adapter.
- [x] `duda → divide → ordena → enumera` corre secuencial, bloquea ante ambigüedad y encadena artefactos markdown.
- [x] Hook de protección impide que el agente edite `core/*`; hook pre-síntesis exige trazabilidad ADR.
- [x] Store SQLite persiste decisiones/sesiones del ciclo.
- [x] pytest+ruff instalados y `strict_tdd` activado en la primera fase de tareas.
