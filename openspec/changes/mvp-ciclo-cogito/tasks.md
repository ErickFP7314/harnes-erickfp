# Tareas: MVP núcleo cartesiano de ErickFP (Ciclo Cogito)

Orden: infraestructura → spikes de riesgo → implementación (cartesiano simple→complejo) → integración/verificación.
Strict TDD activo desde la Fase 1: cada tarea de implementación indica su test primero (RED → GREEN).

## Fase 1: Infraestructura

- [x] 1.1 Crear `.venv` del proyecto y `pyproject.toml` (paquete `erickfp`, layout `src/`, deps Typer + LiteLLM, Python >=3.10).
- [x] 1.2 Instalar en el venv del proyecto: pytest, pytest-cov, ruff, mypy, import-linter. Configurar secciones `[tool.pytest.ini_options]`, `[tool.ruff]`, `[tool.mypy]`, `[tool.importlinter]` (contratos de capas de Decisión 1 del design).
- [x] 1.3 Actualizar `openspec/config.yaml`: `strict_tdd: true`, `testing.test_runner: pytest`, `linter/type_checker/formatter` a `ruff`/`mypy`/`ruff format`. Reflejar el mismo estado en engram `sdd/harnes-erickfp/testing-capabilities`.
- [x] 1.4 Verificar `pytest` (0 tests, exit 0) y `ruff check`/`mypy` corren limpio sobre `src/` vacío — smoke de la infraestructura. **Nota**: pytest sin tests reporta exit code 5 (`NO_TESTS_COLLECTED`, comportamiento estándar y documentado de pytest 9.1.1, no un error de infraestructura); `ruff check` y `mypy` sí retornan exit 0 limpio. Ver deviations en apply-progress.

## Fase 2: Spikes de riesgo (de-risking antes de implementar)

- [x] 2.1 **[SPIKE obligatorio]** Round-trip de thought signatures: script `scripts/spike_thought_signature.py`, LiteLLM real, 2 turnos con tool calling. **CERRADO 2026-07-03 con key nueva** (el bloqueo previo por key filtrada quedó documentado en el historial de este archivo y en engram `config/gemini-api-key-status`). Resultado: los 5 modelos probados (`gemini-3-flash-preview`, `gemini-flash-latest`, `gemini-3.5-flash`, `gemma-4-26b-a4b-it`, `gemma-4-31b-it`) aceptan `tools`, devuelven tool calls parseables y completan el round-trip de thought signatures re-inyectando `tool_call.id` (mecanismo `__thought__` confirmado empíricamente). Nota: `gemma-3-27b-it` NO existe en v1beta (404); los nombres reales de Gemma se obtuvieron del endpoint `GET /v1beta/models`. **Desenlace: ADR-001 — el usuario eligió `gemini/gemma-4-26b-a4b-it` como modelo default** (registrado en engram `adr/001-modelo-default`; `DEFAULT_MODEL` actualizado con test RED→GREEN). Tabla completa en `docs/spikes/thought-signature.md`.
- [x] 2.2 **[SPIKE]** Límites free tier con tool calling. **CERRADO 2026-07-03** con el modelo del ADR-001 (`gemma-4-26b-a4b-it`): 10 llamadas reales consecutivas OK sin ningún 429 — la latencia propia del modelo (3.8–13s/llamada) mantiene el ritmo bajo 10 RPM de forma natural; un turno agéntico multi-tool cabe sin mitigación. Hallazgo adicional: la llamada 11 devolvió `500 INTERNAL` transitorio del servidor (no de cuota) → **mitigación requerida: retry con backoff ante 500 esporádicos en el adapter** (anotado para Fase 11). Detalle en `docs/spikes/free-tier-limits.md`.
- [x] 2.3 **[SPIKE]** Prompt y/n compartido en REPL (Typer/Rich): validar que la lectura de stdin del permission gate y la de prompts de fase no compiten (pitfall "scanner races" del cap. 02, versión Python). Criterio de salida: doc `docs/spikes/repl-input.md` con el patrón validado (un único consumer de `input()`) o el fix necesario. Completado: patrón validado (única función `read_line()` wrapper de `input()`, Rich `Console.input()` confirmado equivalente por código fuente), sin dependencia de red.

## Fase 3: `api/types` (sin dependencias — base cartesiana)

- [x] 3.1 RED: `tests/api/test_types.py` — Message/Block/ToolDef/Response/HookResult/Entry son construibles; `Block.provider_metadata` default `{}` y opaco.
- [x] 3.2 GREEN: crear `src/erickfp/api/types.py` (dataclasses de Decisión 5 del design).

## Fase 4: Provider layer

- [x] 4.1 RED: `tests/provider/test_base.py` — `MockProvider` satisface el Protocol `Provider` (send/model/set_model).
- [x] 4.2 GREEN: crear `src/erickfp/provider/base.py`.
- [x] 4.3 RED: `tests/provider/test_litellm_gemini.py` (mock de `litellm.completion`) — el adapter traduce la respuesta cruda a `Response`/`Block`; ningún tipo nativo cruza la frontera.
- [x] 4.4 GREEN: crear `src/erickfp/provider/litellm_gemini.py` (único import de `litellm`). **Deviación documentada**: el modelo default NO es el literal `gemini/gemini-3-flash` (no mapeado en litellm 1.83.7, spike 2.1) sino la constante `DEFAULT_MODEL = "gemini/gemini-3-flash-preview"` con comentario `TODO-ADR` — provisional hasta que el spike 2.1 corra con una `GEMINI_API_KEY` nueva (la actual sigue revocada/filtrada) y confirme el alias exacto.
- [x] 4.5 RED: `tests/provider/test_thought_signature_roundtrip.py` — aplica el hallazgo del spike 2.1: `provider_metadata` del turno 1 se re-inyecta en el payload del turno 2. Cubre ambos mecanismos documentados: `tool_call.id` con separador `__thought__` (tool use) y `provider_specific_fields["thought_signatures"]` (solo texto). Verificado con mocks de `litellm.completion`, sin llamadas reales (key revocada).
- [x] 4.6 GREEN: preservación de thought signature en `litellm_gemini.py` según spike 2.1 (implementada junto con 4.4, verificada por 4.5; ambos tests pasaron en verde sin cambios adicionales de código).
- [x] 4.7 RED: `tests/test_no_native_sdk_leak.py` — introspección AST de imports: ningún módulo fuera de `litellm_gemini.py` importa `anthropic`/`openai`/`google-genai`, y ningún módulo fuera de `litellm_gemini.py` importa `litellm`.
- [x] 4.8 GREEN: no fue necesario ajustar imports — 4.7 pasó en verde de inmediato (la frontera ya estaba respetada desde 4.4). Verificado, no un salto de tarea.

## Fase 5: Tool registry

- [x] 5.1 RED: `tests/tools/test_base.py` — `FakeTool` satisface `@runtime_checkable` Protocol `Tool`.
- [x] 5.2 GREEN: crear `src/erickfp/tools/base.py`.
- [x] 5.3 RED: `tests/tools/test_registry.py` — mecánica del registry (register/get/orden estable/tool nueva al final) con `FakeTool` genérico, más una prueba adicional (`test_module_level_registry_singleton_has_the_three_mvp_tools_registered`) que queda en RED intencional hasta 5.8, cuando bash/read_file/write_file existen y se cablean.
- [x] 5.4 GREEN: crear `src/erickfp/tools/registry.py` (mecánica genérica en verde; la prueba de las 3 tools concretas queda en rojo hasta 5.8, confirmado con `pytest` mostrando 5 passed / 1 failed en ese punto intermedio).
- [x] 5.5 RED: `tests/tools/test_bash.py` — `execute()` retorna `(stdout, is_error)`.
- [x] 5.6 GREEN: crear `src/erickfp/tools/bash.py`.
- [x] 5.7 RED: `tests/tools/test_read_file.py` + `test_write_file.py` — lectura/escritura real sobre `tmp_path`.
- [x] 5.8 GREEN: crear `read_file.py`/`write_file.py`; registrar las 3 tools (`BashTool`, `ReadFileTool`, `WriteFileTool`) en el singleton `registry` del módulo `tools/registry.py`. Suite completa de Fase 5 en verde (todas las pruebas de `tests/tools/` pasan, incluida la que había quedado en rojo en 5.3/5.4).

## Fase 6: Permission gate + Agent loop (riesgo alto: gate sin fuga)

- [x] 6.1 RED (nombrado): `test_gate_denies_by_default_on_empty_or_invalid_input` — Enter vacío o texto distinto de "y"/"n" → deny.
- [x] 6.2 RED (nombrado): `test_gate_approves_only_on_explicit_y` — solo "y" ejecuta la tool real.
- [x] 6.3 RED (nombrado): `test_gate_denial_produces_tool_result_is_error_true_no_exception` — "n" produce `tool_result(is_error=true)` sin lanzar excepción.
- [x] 6.4 GREEN: crear `src/erickfp/agent/gate.py` (consume `input()` según patrón validado en spike 2.3).
- [x] 6.5 RED: `tests/agent/test_loop.py::test_no_tool_use_skips_gate` — turno solo texto no invoca el gate.
- [x] 6.6 RED (nombrado): `test_every_tool_use_passes_through_gate_no_direct_path` — todo `tool_use` pasa por el gate antes de `execute()`, sin ruta alternativa.
- [x] 6.7 GREEN: crear `src/erickfp/agent/loop.py` (loop hasta `stop_reason=end_turn`, probado con `MockProvider`).

## Fase 7: CLI `init` + `chat`

- [x] 7.1 RED: `tests/cli/test_init.py::test_first_init_creates_full_tree` — crea `.ErickFP/{core/Claude,core/agents,adr/,memory/,hooks/}` con plantillas no vacías (`tmp_path`).
- [x] 7.2 RED: `tests/cli/test_init.py::test_reinit_does_not_overwrite_core_without_confirmation` — re-init no sobrescribe `core/Claude`/`core/agents` sin confirmación explícita; informa rutas existentes vs. creadas.
- [x] 7.3 GREEN: crear `src/erickfp/cli.py` con comando `init` (Typer) + plantillas raíz en `src/erickfp/templates/`.
- [x] 7.4 RED: `tests/cli/test_chat.py::test_preamble_loaded_before_first_turn` — `Store.preamble()` (mock) se incluye en el contexto antes del primer turno.
- [x] 7.5 GREEN: agregar comando `chat` a `cli.py`, cableando Provider real + agent loop + gate + tool registry. Slug de fase (`slug-objetivo`) = slugify del argumento CLI (resuelve pregunta abierta del design).

## Fase 8: Phase hooks (riesgo alto: fuga en protección de `core/*`)

- [x] 8.1 RED: `tests/hooks/test_base.py` — `FakeHook` satisface Protocol `Hook`; `HookResult(decision, reason)`.
- [x] 8.2 GREEN: crear `src/erickfp/hooks/base.py`.
- [x] 8.3 RED: `tests/hooks/test_manager.py::test_constraints_accumulate_across_phase_starts` — `PhaseContext.constraints` se acumulan entre `PhaseStart` sucesivos (divide→ordena).
- [x] 8.4 GREEN: crear `src/erickfp/hooks/manager.py` (`HookManager` inyectado, `PhaseContext`).
- [x] 8.5 RED (nombrado): `test_core_guard_blocks_write_to_core_even_after_gate_approval` — `write_file` a `.ErickFP/core/*` bloqueado en `PreToolUse` pese a "y" del gate.
- [x] 8.6 RED (nombrado): `test_core_guard_allows_writes_outside_core` — escritura fuera de `core/*` no bloqueada por este hook.
- [x] 8.7 RED (nombrado): `test_core_guard_active_in_every_phase_and_chat` — hook activo igual en `duda`/`divide`/`ordena`/`enumera`/`chat`.
- [x] 8.8 GREEN: crear `src/erickfp/hooks/core_guard.py`.
- [x] 8.9 RED: `tests/hooks/test_adr_traceability.py` — bloquea `PhaseStart` de `ordena` si el artefacto de `divide` no referencia un ADR padre; detecta ciclo e id inexistente; permite si el DFS llega a un nodo raíz.
- [x] 8.10 GREEN: crear `src/erickfp/hooks/adr_traceability.py` + parseo frontmatter YAML/DFS. **Deviación documentada**: la lógica de grafo vive en `src/erickfp/hooks/adr_graph.py` (NO en `src/erickfp/cogito/adr.py` como decía el design) porque el contrato `import-linter` ya vigente en `pyproject.toml` (Decisión 1) prohíbe que `hooks` dependa de `cogito` (jerarquía inversa); mantenerlo dentro de `hooks/` preserva la regla sin tocar el contrato. Además, extendida (no reescrita) `src/erickfp/agent/loop.py::run_turn` con parámetros opcionales `hook_manager`/`ctx` (default `None`, retrocompatible con Fase 6): `PreToolUse` corre ANTES del gate y un `deny` bloquea la tool sin consultar `input()`. `pyproject.toml` actualizado: capa `erickfp.agent` añadida al contrato de `import-linter` (dependencia real introducida `agent→hooks`) y dependencia explícita `pyyaml>=6.0` (+ `types-PyYAML` dev, mypy limpio).

## Fase 9: Memory store

- [x] 9.1 RED: `tests/memory/test_store.py` — `FakeStore` satisface Protocol `Store`.
- [x] 9.2 GREEN: crear `src/erickfp/memory/store.py`.
- [x] 9.3 RED: `tests/memory/test_sqlite_store.py` — `save()` persiste en `.ErickFP/memory/erickfp.db` (`tmp_path`); `recall(query, limit)` retorna coincidencias por `LIKE`; `preamble()` concatena `fact`/`preference` + últimas `session-summary`.
- [x] 9.4 GREEN: crear `src/erickfp/memory/sqlite_store.py` (schema `entries`, `CREATE TABLE IF NOT EXISTS`). Cableado adicional (no listado como subtarea propia, pedido explícito de la orquestación): `src/erickfp/cli.py::chat()` reemplaza `_NullStore` por `SqliteStore(root=root)` real; `_NullStore` eliminada del código (ya no tiene uso). Cubierto por `tests/cli/test_chat_memory_wiring.py` (RED→GREEN).

## Fase 10: Ciclo Cogito (integra todas las capas)

- [ ] 10.1 RED: `tests/cogito/test_artifacts.py` — `artifacts.require(prev)` falla limpiamente (sin crash, sin artefacto parcial) si el artefacto previo falta o está vacío.
- [ ] 10.2 GREEN: crear `src/erickfp/cogito/artifacts.py`.
- [ ] 10.3 RED: `tests/cogito/test_phases.py` — `duda` detecta ambigüedad (requisitos contradictorios) y pide clarificación sin generar artefacto; entrada clara produce artefacto aceptado.
- [ ] 10.4 GREEN: crear `src/erickfp/cogito/phases.py` (duda/divide/ordena/enumera + roles Planner/Coder/Reviewer desde `core/agents`; `save` explícito de session-summary, auto-summary fuera de alcance por YAGNI).
- [ ] 10.5 RED: `tests/cogito/test_orchestrator.py` — cadena completa `duda→divide→ordena→enumera` con `MockProvider` + `.ErickFP/` en `tmp_path`; modo interactivo pausa entre fases; modo automático encadena sin pausa.
- [ ] 10.6 GREEN: crear `src/erickfp/cogito/orchestrator.py` (invoca `HookManager` en `PhaseStart`/`PhaseEnd`, agent loop por fase, `artifacts.require`).
- [ ] 10.7 GREEN: cablear comandos `duda`, `divide`, `ordena`, `enumera` en `cli.py` reutilizando el orquestador.

## Fase 11: Integración final y verificación de robustez

- [ ] 11.1 `tests/test_architecture_import_rules.py` + config `import-linter`: valida la regla de dependencia completa (`api→nada`; `provider|tools|memory→api`; `hooks→api`; `cogito→api,provider,tools,hooks,memory`; `cli→todo`).
- [ ] 11.2 Ejecutar `ruff check` y `mypy` sobre `src/erickfp/`; corregir hallazgos.
- [ ] 11.3 Smoke manual (E2E, no automatizado): `erickfp init` + `erickfp chat` real contra el modelo default del ADR-001 (`gemini/gemma-4-26b-a4b-it`) con API key; documentar resultado en `docs/smoke-e2e.md`.
- [ ] 11.4 Actualizar `openspec/config.yaml` (`verify.test_command: pytest`, `coverage_threshold` acordado).
- [ ] 11.5 Retry con backoff acotado ante `500 INTERNAL` transitorios en `litellm_gemini.py` (hallazgo del spike 2.2 con Gemma 4: 1 de 11 llamadas reales fallo con 500 esporadico; extender el patron de `scripts/spike_thought_signature.py::_call_with_backoff` a "500"/"INTERNAL"). TDD: test con mock que falla 1 vez con 500 y luego responde OK.
- [ ] 11.6 Limpiar los 6 `E501` preexistentes de `scripts/spike_thought_signature.py` o excluir `scripts/` del linting (decision menor pendiente desde Lote 2).
