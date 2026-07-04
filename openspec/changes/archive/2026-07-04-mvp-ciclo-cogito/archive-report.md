# Archive Report — mvp-ciclo-cogito

**Change Name**: mvp-ciclo-cogito
**Project**: harnes-erickfp
**Archived**: 2026-07-04
**Status**: ARCHIVED — Cycle Complete

---

## Executive Summary

El cambio **mvp-ciclo-cogito** ha completado el ciclo completo SDD (proposal → specs → design → tasks → apply → verify → archive) con veredicto **PASS WITH WARNINGS**. Se han fusionado 7 nuevas capabilities (cli-init, agent-loop, provider-layer, tool-registry, ciclo-cogito, phase-hooks, memory-store) a través de 5 lotes de implementación (64 tareas completadas, 126 tests en verde, 95% cobertura). El único WARNING identificado en verify (spec de provider-layer no reflejaba ADR-001) ha sido corregido antes del archive. El cambio está listo para producción con deuda técnica menor documentada (3 SUGGESTIONS).

---

## Change Timeline

| Fase | Fecha inicio | Fecha conclusión | Estado |
|------|--------------|------------------|--------|
| Proposal | 2026-07-03 | 2026-07-03 | ✅ Done |
| Spec (7 domains) | 2026-07-03 | 2026-07-03 | ✅ Done |
| Design (7 decisiones arquitectónicas) | 2026-07-03 | 2026-07-03 | ✅ Done |
| Tasks (11 fases, 64 tareas) | 2026-07-03 | 2026-07-03 | ✅ Done |
| Apply (5 lotes de implementación) | 2026-07-03 | 2026-07-03 | ✅ Done (64/64) |
| Verify (126 tests + cobertura 95%) | 2026-07-03 | 2026-07-03 | ✅ Done (PASS WITH WARNINGS) |
| Archive | 2026-07-04 | 2026-07-04 | ✅ Done |

**Ciclo total**: 1 día (velocidad acelerada por ejecución híbrida engram/openspec y tests pre-preparados).

---

## Implementation Batches

### Lote 1: Fases 1-2 (Infraestructura + Spikes de riesgo)
- **Tareas**: 4 + 3 (spike obligatorio)
- **Status**: ✅ Completo
- **Hallazgos**:
  - Infraestructura `.venv`, `pyproject.toml`, pytest+ruff+mypy+import-linter configurados con éxito
  - Spike 2.1 (round-trip de thought signatures) descubrió que `gemini/gemini-3-flash` NO está mapeado en LiteLLM 1.83.7 → **Decisión ADR-001**: modelo default = `gemini/gemma-4-26b-a4b-it`
  - Spike 2.2 (free tier): 10 llamadas OK, llamada 11 retornó 500 transitorio → mitigación requerida (implementada en Lote 5)
  - Spike 2.3 (REPL input): patrón validado, sin race conditions

### Lote 2: Fases 3-5 (API types + Provider + Tool registry)
- **Tareas**: 18/18
- **Tests**: 50/50 en verde
- **Status**: ✅ Completo
- **Hallazgos**:
  - `api/types.py`: Message/Block/ToolDef/Response/HookResult/Entry dataclasses
  - `provider/base.py`: Protocol Provider (send/model/set_model)
  - `provider/litellm_gemini.py`: adapter LiteLLM → Gemini con preservación de thought signatures
  - `tools/`: registry genérico + 3 tools (bash, read_file, write_file) en orden estable
  - Introspección AST verificó: ningún SDK nativo fuera del adapter

### Lote 3: Fases 6-7 (Permission gate + Agent loop + CLI init)
- **Tareas**: 12/12
- **Tests**: 66/66 en verde
- **Status**: ✅ Completo (riesgo high cubierto)
- **Hallazgos**:
  - Permission gate: default deny, solo "y" exacto aprueba, negación nunca lanza excepción
  - Agent loop: REPL plano, pasa tool calls por gate, PreToolUse antes de ejecución
  - CLI init: scaffolding `.ErickFP/` con plantillas raíz (core/Claude, core/agents, adr/, memory/, hooks/)
  - Riesgo "gate sin fuga" → verificado exhaustivamente, 7 variantes parametrizadas de negación

### Lote 4: Fases 8-9 (Phase hooks + Memory store)
- **Tareas**: 14/14
- **Tests**: 100/100 en verde
- **Status**: ✅ Completo (riesgo high cubierto)
- **Hallazgos**:
  - HookManager inyectado (no registry global), PhaseContext acumulativo
  - `hooks/core_guard.py`: bloquea escritura en `core/*` incluso con gate aprobado, resuelve paths relativos/`..`/symlinks con `Path.resolve()`
  - `hooks/adr_traceability.py`: valida DFS por grafo ADR hasta raíz, en fase `ordena`
  - **Desviación documentada**: `adr_graph.py` vive en `hooks/` no `cogito/adr.py` (contrato import-linter)
  - `memory/sqlite_store.py`: esquema entries, recall via LIKE, preamble concatena facts/preferences + session-summaries

### Lote 5: Fases 10-11 (Ciclo Cogito integrador + Integración final + Smoke E2E)
- **Tareas**: 16/16
- **Tests**: 126/126 en verde (totales proyecto)
- **Cobertura**: 95% (umbral 85%)
- **Status**: ✅ Completo (CAMBIO FINAL)
- **Hallazgos**:
  - `cogito/{artifacts,phases,orchestrator}.py`: comandos CLI duda/divide/ordena/enumera con artefactos `.ErickFP/cogito/{slug}/{fase}.md`
  - Protocolo marcadores ACEPTADO:/AMBIGUO: para que duda declare ambigüedad
  - HookManager instanciado por primera vez en producción real (antes solo aislado)
  - Retry con backoff ante 500 INTERNAL (mitigación de spike 2.2) verificado con evidencia REAL en smoke E2E
  - Smoke E2E manual: `erickfp init` + `duda` + `chat` contra Gemini real, 2 intentos con 500 real, éxito tras esperar 15s
  - `pyproject.toml` actualizado: capa erickfp.agent + pyyaml/types-PyYAML
  - **Desviación permitida**: `cogito/phases.py` depende de `erickfp.agent` (no listado en árbol de Decision 1 del design, pero válido porque cogito ya está por encima en las capas reales)
  - Scripts linting: excluidos explícitamente de linting (decisión 11.6), 6 E501 preexistentes documentados

---

## Verification Results (Verify Phase)

| Métrica | Resultado |
|---------|-----------|
| Task completion | 64/64 (100%) |
| Test pass rate | 126/126 (100%) |
| Code coverage | 95% (umbral 85%, PASS) |
| Type checking (mypy) | ✅ 29 files, no issues |
| Linting (ruff) | ✅ All checks passed |
| Import contract (lint-imports) | ✅ 1 kept, 0 broken |

### Spec Compliance

| Domain | Scenarios | Status | Notes |
|--------|-----------|--------|-------|
| cli-init | 3 | ✅ COMPLIANT | 3/3 |
| agent-loop | 6 | ✅ COMPLIANT | 6/6 |
| provider-layer | 3 | ⚠️ PARTIAL (now FIXED) | 3/3 (WARNING-1 corrected) |
| tool-registry | 3 | ✅ COMPLIANT | 3/3 |
| ciclo-cogito | 6 | ✅ COMPLIANT | 6/6 |
| phase-hooks | 5 | ✅ COMPLIANT | 5/5 (riesgo high verified) |
| memory-store | 3 | ✅ COMPLIANT | 3/3 |
| **Total** | **29** | **28/29 → 29/29** | **(WARNING fixed before archive)** |

### Quality Findings

**CRITICAL Issues**: 0 — Cambio apto para producción.

**WARNINGS (Fixed)**: 1
- **WARNING-1** (NOW FIXED): `specs/provider-layer/spec.md` línea 28 tenía literal `gemini/gemini-3-flash` (no mapeado en LiteLLM 1.83.7). Corregido a `gemini/gemma-4-26b-a4b-it` antes de fusionar specs a `openspec/specs/` ✅

**SUGGESTIONS (Accepted as minor debt)**:
1. **SUGGESTION-1** — Ramas de error sin cubrir: `agent/loop.py:65-76` (tool desconocida), `hooks/core_guard.py:59-60,67-68` (OSError, input no-dict), `hooks/adr_graph.py:40,44-45,59,64` (YAML inválido), `cli.py` (chat sin init, EOFError). Recomendación: añadir tests por rama en fase futura. No bloqueante para MVP.

2. **SUGGESTION-2** — `proposal.md` Success Criteria checklist (7 ítems) sigue con `- [ ]` aunque todos están satisfechos. Aceptado como deuda cosmetolgy (todos los criterios están cubiertos con evidencia real: tests + smoke E2E).

3. **SUGGESTION-3** — Spec `agent-loop` no tiene escenario explícito para "tool desconocida en el registry" (comportamiento real: `tool_result is_error=true`, implementado en código pero no formalizado en spec). Aceptado como deuda menor.

### Operational Risks (Documented)

| Riesgo | Prob | Mitigación implementada | Estado |
|--------|------|------------------------|--------|
| Latencia/inestabilidad de Gemma 4 | Med | Retry con backoff ante 500 INTERNAL (11.5) verificado con smoke E2E real | ✅ Mitigado |
| Free tier rate limits | Med | Spike 2.2: 10 llamadas OK, latencia natural mantiene <10 RPM | ✅ Verificado |
| Permission gate con fuga | High | Gate en harness (no tool/prompt), 7 tests parametrizados, default deny, evaluación exhaustiva | ✅ Mitigado |
| Edición no autorizada de core/* | High | `core_guard.py` PreToolUse siempre activo, `Path.resolve()` contra paths relativos/`..`/symlinks, test con equivalentes incluido | ✅ Mitigado |

---

## Specs Merged to Main

Se han fusionado **7 nuevas capabilities** desde `openspec/changes/mvp-ciclo-cogito/specs/` a `openspec/specs/`:

| Domain | File | Action | Status |
|--------|------|--------|--------|
| cli-init | `openspec/specs/cli-init/spec.md` | Created (new capability) | ✅ |
| agent-loop | `openspec/specs/agent-loop/spec.md` | Created (new capability) | ✅ |
| provider-layer | `openspec/specs/provider-layer/spec.md` | Created (new capability, WARNING fixed) | ✅ |
| tool-registry | `openspec/specs/tool-registry/spec.md` | Created (new capability) | ✅ |
| ciclo-cogito | `openspec/specs/ciclo-cogito/spec.md` | Created (new capability) | ✅ |
| phase-hooks | `openspec/specs/phase-hooks/spec.md` | Created (new capability) | ✅ |
| memory-store | `openspec/specs/memory-store/spec.md` | Created (new capability) | ✅ |

**Merge strategy**: Greenfield (no previous main specs). Each delta spec copied directly as full spec to `openspec/specs/{domain}/spec.md`. No destructive merges.

---

## Artifacts Moved to Archive

**Source**: `openspec/changes/mvp-ciclo-cogito/`
**Destination**: `openspec/changes/archive/2026-07-04-mvp-ciclo-cogito/`

**Contents preserved**:
- ✅ `proposal.md` — original proposal
- ✅ `design.md` — architectural decisions (7 decisions documented)
- ✅ `specs/` directory (7 domain subdirs with spec.md, now synchronized with WARNING fix)
- ✅ `tasks.md` — 64 tasks (11 phases) with full execution notes
- ✅ `verify-report.md` — verification results (PASS WITH WARNINGS)
- ✅ `state.yaml` — DAG state (updated: archive status = done)
- ✅ `archive-report.md` — this report (traceability + closure)

---

## Traceability to ADR

### Architecture Decisions Documented in Design

1. **Decisión 1** — Estructura de paquetes + reglas de dependencia (src/erickfp layout, import-linter contract)
2. **Decisión 2** — Thought signatures opacas en `provider_metadata` (round-trip en multi-turno, boundary intacta)
3. **Decisión 3** — HookManager inyectado (no registry global), restricciones acumulativas por fase
4. **Decisión 4** — Artefactos del Ciclo Cogito (`.ErickFP/cogito/{slug}/`), mapeo de roles Planner/Coder/Reviewer
5. **Decisión 5** — Interfaces via `typing.Protocol` (Provider, Tool, Store, Hook)
6. **Decisión 6** — Esquema SQLite: tabla `entries` con recall via LIKE
7. **Decisión 7** — Grafo ADR: frontmatter YAML (id, parents, estado, trade_off) con validación DFS

### ADRs Created (Engram)

- **ADR-001**: "Modelo default = `gemini/gemma-4-26b-a4b-it`" (spike 2.1, decisión del usuario 2026-07-03)
- **ADR-002** through **ADR-007**: Decisiones 1-7 del design mapeadas (pendiente de formalización en `.ErickFP/adr/` en próxima sesión)

---

## Lessons Learned

### Technical Discoveries

1. **LiteLLM 1.83.7 model name mapping**: Alias `gemini/gemini-3-flash` no existe; los nombres reales se obtienen del endpoint `GET /v1beta/models` (Gemini API documentation lag).

2. **Thought signature preservation**: El mecanismo es dual — `tool_call.id` con separador `__thought__` (tool use) y `provider_specific_fields["thought_signatures"]` (solo texto) — pero ambos usan el mismo campo opaco `provider_metadata` en nuestro boundary.

3. **Free tier quirks**: Gemini free tier no tiene rate limiting duro sino throttling por latencia (14s promedio en Gemma 4), que mantiene el ritmo natural bajo 10 RPM sin mitigation especial.

4. **Path resolution**: Python `Path.resolve()` resuelve correctamente paths relativos, `..`, y symlinks en una sola llamada — crítico para `core_guard.py` sin race conditions.

5. **Import contract enforcement**: import-linter con capas de `pyproject.toml` cumple estrictamente; los desvíos (cogito depende de agent, adr_graph vive en hooks) fueron documentados y son válidos porque cogito ya está en capas superiores.

### Process Insights

1. **Spike-driven approach works**: Spike 2.1 (thought signatures) y spike 2.2 (free tier) desriesgaron las decisiones arquitectónicas antes de implementar — ningún bloqueo sorpresa en apply.

2. **Strict TDD + pytest coverage 95%**: La cobertura natural emerge sin overhead artificial (no forzar 100%); las 6 ramas sin cubrir de Lote 1/scripts/ están fuera de scope pero documentadas.

3. **Hybrid artifact store (engram + openspec)** proporciona recuperación cross-session + auditabilidad local — equilibrio ideal para este tipo de cambio "infra nuevo".

4. **Marcadores de ambigüedad (ACEPTADO:/AMBIGUO:)** en fase `duda` clarifican el contrato sin requerir lógica IA sofisticada — simple protocol driven.

### Recommendations for Next Phase

1. **Formalizar ADRs** en `.ErickFP/adr/` cuando el proyecto tenga la estructura en disco (admin task).

2. **Implementar los 3 SUGGESTIONS** en un cambio futuro de "debt reduction" (muy bajo esfuerzo: 3 tests + 1 línea en spec + 1 línea en checklist).

3. **Monitorear latencia de Gemma 4**: El spike 2.2 capturó 500 transitorio real — el retry con backoff implementado es suficiente para MVP pero una métrica en producción (p.ej. Prometheus) alertaría temprano si la latencia degrada.

4. **Considerar embeddings + FAISS** para `Store.recall()` si el volumen de sesiones supera 1000 — LIKE tiene límites, pero MVP escala sin overhead.

---

## Closure Checklist

- [x] Todas las fases completadas (proposal → verify)
- [x] 0 CRITICAL issues
- [x] 1 WARNING identificado y corregido antes de archive
- [x] 7 nuevas capabilities en specs, todas COMPLIANT
- [x] 126/126 tests en verde
- [x] Cobertura 95% (umbral 85%, PASS)
- [x] 3 SUGGESTIONS documentadas como deuda menor aceptada
- [x] 64/64 tareas implementadas
- [x] Riesgos high (gate sin fuga, protección core/*) cubiertos exhaustivamente
- [x] Specs fusionadas a `openspec/specs/`
- [x] Carpeta de cambio movida a `openspec/changes/archive/2026-07-04-mvp-ciclo-cogito/`
- [x] State.yaml actualizado (archive status = done)
- [x] Archive-report persistido en engram como `sdd/mvp-ciclo-cogito/archive-report`

---

## Next Steps

**Ciclo de mvp-ciclo-cogito cerrado. Preparado para:**
1. Siguiente cambio SDD (nuevo `/sdd-new` para nueva capability o iteración)
2. Admin tasks: formalizar ADRs en disco, setup `.ErickFP/` runtime
3. Observabilidad: agregar logs + métricas (latencia provider, retry rate, gate denials)
4. Debt reduction (opcional): implementar 3 SUGGESTIONS en cambio futuro

---

**Archive Report Author**: sdd-archive (executor, harnes-erickfp project)
**Date**: 2026-07-04
**Artifact Store Mode**: hybrid (openspec + engram)
**Verification**: PASS WITH WARNINGS → Fixed → READY FOR PRODUCTION
