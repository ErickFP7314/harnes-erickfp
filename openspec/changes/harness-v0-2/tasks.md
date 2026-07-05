# Tasks: Harness v0.2 — Agente pulido y extensible

Convención: cada tarea de implementación es RED (test que falla) → GREEN (mínimo código que lo pasa). STRICT TDD activo. Cada Lote termina con `pytest -q` + `ruff check .` + `mypy src/erickfp` + `lint-imports` en verde antes de avanzar (regla del ciclo 1). 56 escenarios de las 11 specs mapeados 1:1 a un test nombrado.

## Lote 1 — ui-polish (prioridad 1, pedido explícito del usuario)

- [x] 1.1 Extender `pyproject.toml [tool.importlinter]` con el contrato COMPLETO (ui, compaction, subagents, y el resto) ANTES de crear código en capas nuevas. Test: `tests/test_architecture_import_rules.py::test_extended_layer_contract_ui_compaction_subagents`
- [x] 1.2 GREEN: paquetes placeholder `ui/__init__.py`, `compaction/__init__.py`, `subagents/__init__.py`; lint-imports pasa.
- [x] 1.3 RED `scripts/gen_portada.py` parsea `portada.html`→asset Rich. Test: `tests/ui/test_gen_portada.py::test_parses_portada_html_into_rich_text_asset`
- [x] 1.4 GREEN: implementar generador; producir `ui/_portada_asset.py` real (exento de lint).
- [x] 1.5 RED banner completo si `Console.width>=149`. Test: `tests/ui/test_banner.py::test_wide_terminal_renders_full_banner`
- [x] 1.6 GREEN `ui/banner.py::render_banner(console)` con `Panel` + fondo #222222.
- [x] 1.7 RED fallback <149 cols sin cortar arte ni error. Test: `tests/ui/test_banner.py::test_narrow_terminal_renders_fallback_panel`
- [x] 1.8 GREEN branch de ancho en `render_banner`.
- [x] 1.9 RED runtime nunca parsea HTML (introspección de imports). Test: `tests/ui/test_banner.py::test_runtime_never_parses_html`
- [x] 1.10 RED input decorado en Panel con bordes tema. Test: `tests/ui/test_input_frame.py::test_decorated_prompt_uses_theme_panel`
- [x] 1.11 GREEN `ui/input_frame.py::frame(label)` + composición con `gate.read_line` (consumer único de stdin).
- [x] 1.12 RED banner e input comparten paleta (#00FFFF/#00FF00/#222222). Test: `tests/ui/test_theme.py::test_banner_and_input_share_same_palette`
- [x] 1.13 GREEN `ui/theme.py` constantes compartidas.
- [x] 1.14 Cablear en `cli.py`: banner al arranque de `chat` + `decorated_read_line` como `read_line=` de `run_chat_session`. Test: `tests/cli/test_chat.py::test_chat_startup_renders_banner_and_uses_decorated_input`
- [x] 1.15 Suite completa verde (pytest+ruff+mypy+lint-imports) antes de Lote 2.

## Lote 2 — Robustez/deuda ciclo 1 (retry configurable + 3 SUGGESTIONS)

- [x] 2.1 RED reintento exitoso tras 5xx transitorio. Test: `tests/provider/test_litellm_gemini_retry.py::test_retries_on_5xx_then_succeeds`
- [x] 2.2 GREEN `LiteLLMGeminiProvider.__init__(max_attempts=2, backoff_seconds=2.0)` reemplaza constantes `_MAX_ATTEMPTS`/`_BACKOFF_SECONDS`.
- [x] 2.3 RED agotar intentos → `ProviderError` limpio, sin excepción nativa. Test: `tests/provider/test_litellm_gemini_retry.py::test_exhausts_attempts_raises_clean_provider_error`
- [x] 2.4 RED error 4xx no transitorio no reintenta. Test: `tests/provider/test_litellm_gemini_retry.py::test_non_transient_4xx_does_not_retry`
- [x] 2.5 RED retry preserva thought signature entre reintentos. Test: `tests/provider/test_thought_signature_roundtrip.py::test_retry_preserves_thought_signature`
- [x] 2.6 GREEN cli/config pasan `max_attempts`/`backoff_seconds` al constructor.
- [x] 2.7 RED (SUGGESTION-1/3) tool desconocida en registry → `is_error=true`, sin excepción, loop continúa. Test: `tests/agent/test_loop.py::test_unknown_tool_returns_is_error_result_without_raising`
- [x] 2.8 GREEN formalizar branch en `agent/loop.py` con mensaje claro.
- [x] 2.9 RED (SUGGESTION-1) `core_guard.py` rama `OSError` de `resolve()` + `tool_input` no-dict. Test: `tests/hooks/test_core_guard.py::test_core_guard_handles_oserror_and_non_dict_input`
- [x] 2.10 GREEN cubrir branches en `core_guard.py`.
- [x] 2.11 RED (SUGGESTION-1) `adr_graph.py` YAML inválido / `id` no-int. Test: `tests/hooks/test_adr_graph.py::test_invalid_yaml_and_non_int_id_handled_cleanly`
- [x] 2.12 GREEN cubrir branches en `adr_graph.py`.
- [x] 2.13 RED (SUGGESTION-1) `cli.py`: `chat` sin `init` previo + `EOFError` en REPL. Test: `tests/cli/test_chat.py::test_chat_without_init_reports_clear_error` + `test_repl_handles_eof_gracefully`
- [x] 2.14 GREEN cubrir branches en `cli.py`.
- [x] 2.15 (SUGGESTION-2) Marcar `[x]` los 7 ítems pendientes de `openspec/changes/archive/2026-07-04-mvp-ciclo-cogito/proposal.md` (evidencia ya real, solo higiene documental).
- [x] 2.16 Suite completa verde antes de Lote 3.

## Lote 3 — slash-commands + token-viewer — [x] COMPLETO (20/20)

- [x] 3.1 RED `/help` lista comandos. Test: `tests/cli/test_slash_commands.py::test_help_lists_available_commands`
- [x] 3.2 GREEN `SlashRegistry: dict[str, handler]` en `cli.py` + `/help`.
- [x] 3.3 RED `/tools` en orden estable del registry. Test: `test_tools_lists_registry_in_stable_order`
- [x] 3.4 GREEN implementar `/tools`.
- [x] 3.5 RED `/clear` vacía historial y re-inyecta contexto raíz (`first_turn=True`). Test: `test_clear_resets_history_and_reinjects_context`
- [x] 3.6 GREEN implementar `/clear`.
- [x] 3.7 RED `/model` muestra/cambia modelo activo. Test: `test_model_shows_and_sets_active_model`
- [x] 3.8 GREEN `/model` → `provider.set_model(arg)`.
- [x] 3.9 RED entrada `/` nunca llega al Provider (comando válido). Test: `test_slash_input_never_reaches_provider`
- [x] 3.10 RED comando desconocido `/foo` → error local, sin llamar Provider. Test: `test_unknown_slash_command_reports_local_error`
- [x] 3.11 GREEN dispatch al inicio del loop REPL (`startswith("/")` → `continue`).
- [x] 3.12 RED `Usage(prompt,completion,total)` cruza sin filtrar tipos litellm. Test: `tests/provider/test_litellm_gemini.py::test_response_usage_is_domain_type_no_litellm_leak`
- [x] 3.13 GREEN `api/types.py::Usage` + `Response.usage`; adapter llena desde `raw.usage`.
- [x] 3.14 RED `TokenTracker.add` acumula por sesión. Test: `tests/agent/test_tokens.py::test_tracker_accumulates_usage_across_turns`
- [x] 3.15 GREEN `agent/tokens.py::TokenTracker`; `run_turn(tracker=None)` llama `tracker.add(response.usage)`.
- [x] 3.16 RED `/tokens` con pricing conocido. Test: `test_tokens_reports_usage_and_cost_known_pricing`
- [x] 3.17 RED `/tokens` con modelo sin pricing → "desconocido/0", sin error. Test: `test_tokens_unknown_pricing_reports_unknown_cost`
- [x] 3.18 RED `/tokens` antes del primer turno → 0/0. Test: `test_tokens_before_first_turn_reports_zero`
- [x] 3.19 GREEN implementar `/tokens` (tabla pricing Gemma free-tier "—/gratis").
- [x] 3.20 Suite completa verde antes de Lote 4.

## Lote 4 — permission-policy — [x] COMPLETO (12/12)

- [x] 4.1 RED `AlwaysAsk` idéntico al gate ciclo 1. Test: `tests/agent/test_policy.py::test_always_ask_matches_cycle1_gate_behavior`
- [x] 4.2 GREEN `agent/policy.py`: `Protocol PermissionPolicy.decide(tool_name,tool_input)->Literal["allow","deny","ask"]`; clase `AlwaysAsk`.
- [x] 4.3 RED `AllowList` aprueba sin preguntar. Test: `test_allowlist_approves_without_asking`
- [x] 4.4 GREEN implementar `AllowList`.
- [x] 4.5 RED `AskOnce` pregunta una vez por sesión, memoriza en el objeto. Test: `test_askonce_asks_once_then_reuses_decision`
- [x] 4.6 GREEN implementar `AskOnce` (estado session-scoped, no persiste a disco).
- [x] 4.7 RED respuesta ambigua bajo `AskOnce` = negación, no se cachea. Test: `test_askonce_ambiguous_response_is_denial_not_cached`
- [x] 4.8 RED **TRANSVERSAL (b)** AllowList/AskOnce NO alcanzan `core/*`; core_guard interviene igual. Test: `tests/hooks/test_core_guard_policy.py::test_allowlist_and_askonce_never_bypass_core_guard` (parametrizado ambas policies)
- [x] 4.9 GREEN orden en `loop.py`: `PreToolUse`/core_guard SIEMPRE antes de consultar policy.
- [x] 4.10 RED **TRANSVERSAL (a)** ninguna tool se ejecuta sin pasar por gate+policy, con cualquier policy configurada. Test: `tests/agent/test_loop.py::test_no_tool_executes_without_gate_and_policy_regardless_of_policy_impl` (parametrizado AlwaysAsk/AllowList/AskOnce)
- [x] 4.11 GREEN `agent/gate.py::run_tool_with_gate(tool, block, policy=None)`; default `None`→`AlwaysAsk`; `cli` threadea `policy`.
- [x] 4.12 Suite completa verde antes de Lote 5.

## Lote 5 — memoria-avanzada — [x] COMPLETO (9/9)

- [x] 5.1 RED `preamble()` incluye resumen de sesión anterior si existe. Test: `tests/memory/test_sqlite_store.py::test_preamble_includes_latest_session_summary`
- [x] 5.2 GREEN enriquecer `preamble()` acotado por tamaño/entradas.
- [x] 5.3 RED resumen fin de sesión persistido al salir de `chat`. Test: `tests/cli/test_chat.py::test_session_end_persists_summary_via_provider_synthesis`
- [x] 5.4 GREEN hook de salida: `provider.send` síntesis + `store.save(Entry(kind="session-summary"))`; `try/except ProviderError` → omite sin crash.
- [x] 5.5 RED sesión sin turnos no genera resumen vacío innecesario/no falla. Test: `test_session_without_turns_skips_or_saves_empty_summary_safely`
- [x] 5.6 RED `RecallTool` usa objeto `.recall(query,limit)` inyectado (duck-typing, sin importar `memory.Store`). Test: `tests/tools/test_recall.py::test_recall_tool_uses_injected_duck_typed_store`
- [x] 5.7 GREEN `tools/recall.py::RecallTool` + registro en composition root `cli.py`.
- [x] 5.8 RED `recall` pasa por el gate igual que `bash`/`read_file`/`write_file`. Test: `tests/agent/test_loop.py::test_recall_tool_passes_through_gate_like_other_tools`
- [x] 5.9 Suite completa verde antes de Lote 6.

## Lote 6 — compaction (capa nueva, contrato ya extendido en 1.1) — [x] COMPLETO (12/12)

- [x] 6.1 RED `NoCompaction` identidad (default). Test: `tests/compaction/test_base.py::test_no_compaction_is_identity_default`
- [x] 6.2 GREEN `compaction/base.py::Protocol CompactionStrategy.compact(messages)->messages` + `NoCompaction`.
- [x] 6.3 RED `SlidingWindow(max)` reduce historial conservando turnos recientes. Test: `tests/compaction/test_sliding_window.py::test_history_exceeding_threshold_shrinks_keeping_recent_turns`
- [x] 6.4 GREEN implementar `SlidingWindow` (`compaction/sliding_window.py`).
- [x] 6.5 RED **TRANSVERSAL (c)** SafeSplitPoint nunca parte un par tool_use/tool_result — parametrizado. Test: `tests/compaction/test_safe_split_point.py::test_never_splits_a_tool_use_tool_result_pair`
- [x] 6.6 GREEN `SafeSplitPoint`: corte `k`; mientras `messages[k].role=="user"` contenga `tool_result`, `k-=1` (`compaction/safe_split.py`).
- [x] 6.7 RED sin pares pendientes, corte aplica directo por umbral. Test: `test_no_pending_pairs_applies_threshold_cut_directly`
- [x] 6.8 RED compaction NUNCA corre dentro de `Provider.send`. Test: `tests/provider/test_litellm_gemini.py::test_provider_send_never_invokes_compaction_strategy`
- [x] 6.9 GREEN invocar `CompactionStrategy.compact` al inicio de `run_turn`, antes del primer `provider.send` (`agent/loop.py`, param `compaction=None`).
- [x] 6.10 RED `Summarize(provider)` condensa turnos antiguos, descarta firmas de turnos colapsados. Test: `tests/compaction/test_summarize.py::test_summarize_condenses_old_turns_and_drops_stale_signatures`
- [x] 6.11 GREEN implementar `Summarize` (`compaction/summarize.py`).
- [x] 6.12 Suite completa verde (lint-imports valida capa `compaction` con código real) antes de Lote 7: pytest 215 passed, ruff clean, mypy clean (43 files), lint-imports "1 kept, 0 broken".

## Lote 7 — subagentes

- [ ] 7.1 RED clase `Agent` extraída; `run_turn` libre queda wrapper con firma preservada (no rompe tests previos). Test: `tests/agent/test_agent_class.py::test_free_run_turn_wraps_agent_class_same_signature`
- [ ] 7.2 GREEN `agent/agent.py::Agent` (provider/tools/hooks/policy/compaction/tracker).
- [ ] 7.3 RED `Research` se instancia solo con tools read-only; `write_file` no registrada. Test: `tests/subagents/test_research.py::test_research_registry_contains_only_read_only_tools`
- [ ] 7.4 GREEN `subagents/research.py`: `Agent` con registry subset + `AllowList` read-only.
- [ ] 7.5 RED **TRANSVERSAL (d)** Research NO puede escribir — tool desconocida, sin ejecución. Test: `tests/subagents/test_research.py::test_research_cannot_write_unknown_tool_no_execution`
- [ ] 7.6 RED core_guard sigue activo dentro del subagente. Test: `test_core_guard_active_inside_subagent`
- [ ] 7.7 RED tool calls internas del subagente no piden aprobación adicional más allá de la de `delegate`. Test: `tests/subagents/test_delegate.py::test_internal_subagent_calls_do_not_reask_approval`
- [ ] 7.8 GREEN `subagents/delegate.py::DelegateTool` instancia `Research`; salida UI indentada `↳`; registro en composition root `cli.py` (registry extendido; `tools/` nunca importa `agent`/`subagents`).
- [ ] 7.9 Suite completa verde (lint-imports valida capa `subagents` y el ciclo delegate resuelto) antes de Lote 8.

## Lote 8 — mcp-support

- [ ] 8.1 Añadir dependencia SDK `mcp` a `pyproject.toml` (única, aislada a este lote).
- [ ] 8.2 RED `MCPTool` satisface `Protocol Tool`; único módulo que importa `mcp`. Test: `tests/tools/test_mcp.py::test_only_mcp_module_imports_mcp_sdk`
- [ ] 8.3 GREEN `tools/mcp.py::MCPTool` + parseo `.ErickFP/mcp.json` (command/args, stdio).
- [ ] 8.4 RED tool MCP se registra en el mismo registry, sin reordenar las locales. Test: `tests/tools/test_registry.py::test_mcp_tool_appended_at_end_without_reordering_locals`
- [ ] 8.5 GREEN registrar en composition root tras discovery.
- [ ] 8.6 RED tool MCP pasa por el mismo gate/policy que las locales. Test: `tests/agent/test_loop.py::test_mcp_tool_passes_through_same_gate_and_policy`
- [ ] 8.7 RED transporte no-stdio (p.ej. HTTP/OAuth) se rechaza con error claro, sin intentar OAuth. Test: `tests/tools/test_mcp.py::test_non_stdio_transport_rejected_with_clear_error`
- [ ] 8.8 GREEN validar config: solo stdio soportado, resto → error explícito.
- [ ] 8.9 Suite completa verde (pytest+ruff+mypy+lint-imports) tras Lote 8.

## Lote 9 — Verificación final y smoke E2E

- [ ] 9.1 Ejecutar `pytest -q`, `ruff check .`, `mypy src/erickfp`, `lint-imports`: 0 fallos, cobertura ≥85%.
- [ ] 9.2 Smoke E2E real (GEMINI_API_KEY vigente): `erickfp chat` — banner (+fallback si aplica), `/help /model /tools /clear /tokens`, un turno con tool call aprobado y uno denegado, `/tokens` tras el turno.
- [ ] 9.3 Documentar el smoke en `docs/smoke-e2e-v0-2.md` con evidencia real (comandos y salidas).
- [ ] 9.4 Tabla de trazabilidad final: confirmar los 56 escenarios de las 11 specs mapeados a un test real que pasa (insumo directo para `sdd-verify`).

## Dependencias entre lotes

Secuencial estricta 1→9 (cada uno depende del anterior en verde). Dentro de cada lote, tareas RED→GREEN son secuenciales; tareas del mismo Requirement (p.ej. 3.1-3.11 slash-commands vs 3.12-3.19 token-viewer) pueden paralelizarse entre sí si hay más de un desarrollador, ya que tocan requirements distintos del mismo lote.
