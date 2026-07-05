# Smoke E2E manual -- harness-v0-2, Lote 9 (tareas 9.2-9.3)

**Fecha**: 2026-07-05. **Modelo**: `gemini/gemma-4-26b-a4b-it` (default ADR-001).
**Entorno**: `.venv` del proyecto, `GEMINI_API_KEY` real cargada desde `.env` de la
raiz solo en el entorno del subproceso (`source .env; set -a; export GEMINI_API_KEY;
set +a`), **nunca impresa ni logueada** en ningun comando ni archivo de este smoke.
Ejecutado sobre un directorio temporal aislado fuera del repo, via `erickfp init`.
`stdin` se alimento con archivos de texto (un comando/mensaje por linea) via
redireccion (`erickfp chat < input.txt`); para capturar los codigos ANSI truecolor
reales del banner se uso ademas `script -qec "... " out.txt` (pty real), ya que con
stdout redirigido a un archivo plano Rich degrada a texto sin color (comportamiento
esperado y no un bug).

## Resumen ejecutivo

Todo el flujo v0.2 (banner + fallback, comandos slash locales, turno real de texto,
`/tokens`, resumen de sesion persistido, arranque limpio sin `mcp.json`) funciono
correctamente contra la API real. El smoke tambien **encontro y corrigio un bug real
de integracion** (no detectable por los 243 tests con dobles/fakes): el adapter
reenviaba el `finish_reason` crudo de litellm (convencion OpenAI-style:
`"stop"`/`"tool_calls"`) sin normalizar a la convencion canonica de dominio
(Anthropic-style: `"end_turn"`/`"tool_use"`) que usa `Agent.run_turn` para decidir si
continuar el loop de tools. Esto hacia que **ninguna tool se ejecutara jamas contra el
modelo real** (el gate ni siquiera se consultaba), pese a que la suite completa
pasaba en verde. Se corrigio con TDD (RED -> GREEN) en
`src/erickfp/provider/litellm_gemini.py` y se re-verifico el smoke completo tras el
fix: la suite paso de 243 a **247 tests** (4 nuevos, parametrizados), y el turno con
tool call aprobada ahora ejecuta realmente el comando y persiste su efecto en disco.

## 0. Verificacion integral previa (tarea 9.1)

```
$ .venv/bin/python -m pytest -q
243 passed in 2.98s          # antes del fix del bug de stop_reason
...
247 passed in 4.04s          # despues del fix (4 tests nuevos, ver seccion 3)

$ .venv/bin/python -m pytest -q --cov=erickfp --cov-report=term
TOTAL   1236 stmts  64 miss  95%   (umbral >=85% -- OK)

$ .venv/bin/python -m ruff check .
All checks passed!

$ .venv/bin/python -m mypy src/erickfp
Success: no issues found in 47 source files

$ .venv/bin/lint-imports
Contracts: 1 kept, 0 broken.
```

## 1. `erickfp init` -- OK, sin red

```
$ erickfp init
creado .../.ErickFP/core/Claude
creado .../.ErickFP/core/agents/planner.md
creado .../.ErickFP/core/agents/coder.md
creado .../.ErickFP/core/agents/reviewer.md
creado .../.ErickFP/adr/README.md
```

Arbol resultante verificado con `find`:

```
.ErickFP/adr/README.md
.ErickFP/core/agents/{coder,planner,reviewer}.md
.ErickFP/core/Claude
.ErickFP/hooks/          (vacio, listo para hooks futuros)
.ErickFP/memory/         (vacio hasta el primer `chat` real)
```

## 2. Banner (ui-polish) -- completo y fallback

### 2.1 Terminal ancha (`COLUMNS=200 >= 149`)

Renderiza el banner completo 25x149 dentro de un `Panel` con borde cyan y fondo
`#222222`, seguido del mensaje de bienvenida y el primer prompt decorado (`tu>` en un
`Panel` propio). Confirmado con pty real (`script -qec ...`) que el banner emite
secuencias ANSI truecolor genuinas:

```
\x1b[38;2;0;255;255;48;2;34;34;34m   -> fg RGB(0,255,255)=#00FFFF sobre bg RGB(34,34,34)=#222222
```

1400 secuencias ANSI truecolor detectadas en la sesion de `/help` via pty (paleta
exacta del tema, cyan primario + fondo del banner).

### 2.2 Terminal angosta (`COLUMNS=80 < 149`) -- fallback

```
╭──────────────────────────────────────────────────────────────────────────────╮
│ ErickFP                                                                      │
╰──────────────────────────────────────────────────────────────────────────────╯
ErickFP chat -- Ctrl+D o 'salir' para terminar. Escribe /help para ver los
comandos disponibles.
```

Nunca corta el arte 25x149 ni lanza error -- degrada limpiamente al mini-panel
(`ui/banner.py::_build_fallback_text`, border_style verde). Confirma el
Requirement "Fallback adaptativo por ancho de terminal" con el binario real, no solo
con el doble `BannerConsole` de los tests unitarios.

## 3. Comandos slash locales -- CERO llamadas al Provider

Entrada: `/help`, `/tools`, `/model`, `/clear`, `salir` -- sesion completa sin
`GEMINI_API_KEY` en el entorno (se omitio deliberadamente para esta prueba, para
demostrar que ninguno de estos comandos toca la red):

```
tu> Comandos disponibles:
/help -- lista los comandos disponibles
/model -- muestra el modelo activo, o lo cambia con /model <nombre>
/tools -- lista las tools registradas (orden estable del registry)
/clear -- vacia el historial de la sesion en curso
/tokens -- muestra tokens acumulados y costo estimado de la sesion

tu> tools registradas: bash, read_file, write_file, recall, delegate_research
tu> Modelo activo: gemini/gemma-4-26b-a4b-it
tu> Historial de la sesion limpiado.
```

Nota: `tools registradas` **no incluye ninguna tool MCP** -- no existe
`.ErickFP/mcp.json` en este directorio de smoke, y `discover_tools` retorno `[]` en
silencio (sin advertencia impresa, comportamiento documentado del Lote 8: "el chat
arranca igual sin tools MCP"). Confirmado por `grep -il mcp out_*.txt` -> 0
coincidencias en ningun archivo de salida de todo el smoke.

## 4. Turno real de texto contra Gemma 4

Primer intento: `500 INTERNAL` transitorio de Google (mismo patron ya documentado en
`docs/smoke-e2e.md` del ciclo 1) -- el retry configurable agoto sus 2 intentos y el
REPL **no crasheo**, informo el error en rojo y siguio esperando el siguiente prompt:

```
El proveedor fallo tras los reintentos: litellm.InternalServerError: GeminiException
InternalServerError - {"error": {"code": 500, "message": "Internal error
encountered.", "status": "INTERNAL"}}
Suele ser inestabilidad temporal del modelo -- espera unos segundos y vuelve a
intentarlo.
```

Tras esperar ~15s y reintentar el turno completo (instruccion de la orquestacion),
la llamada completo exitosamente:

```
tu> Hola, en una sola frase breve dime que eres.
erickfp> Soy un agente del Ciclo Cogito de ErickFP, regido por sus axiomas y roles
especializados.
tu> tokens entrada=1512 salida=768 total=2280 costo=—/gratis
```

`/tokens` reporta uso real acumulado (no simulado): `entrada=1512 salida=768
total=2280`, `costo=—/gratis` (Gemma 4 esta en `_FREE_TIER_MODELS`, spec
token-viewer).

## 5. Hallazgo critico: tool calls reales nunca ejecutaban (bug de `stop_reason`)

### 5.1 Sintoma

Con la instruccion explicita "Llama a la funcion bash con el argumento
command=...", el modelo SI generaba (confirmado con una prueba aislada directa al
adapter, sin pasar por el REPL) un `tool_use` block real:

```python
response = provider.send(messages, tool_defs)
# stop_reason: tool_calls
# BLOCK: tool_use | tool_name= bash | tool_input= {"command": "echo hola_marca"}
```

Pero en el REPL completo, la respuesta final se imprimia **sin que apareciera jamas
el prompt de confirmacion del gate** (`Ejecutar bash(...)? [y/N]`) y sin que el
comando se ejecutara realmente en disco (verificado con un archivo marcador que
nunca se creaba). El modelo, al no recibir un `tool_result` real, alucinaba una
respuesta describiendo una ejecucion que nunca ocurrio.

### 5.2 Causa raiz

`src/erickfp/provider/litellm_gemini.py::_to_response` reenviaba
`choice.finish_reason` **crudo** de litellm (convencion nativa OpenAI-style:
`"stop"`, `"tool_calls"`, `"length"`, ...) directo a `Response.stop_reason`, sin
normalizar -- exactamente el tipo de fuga que la Decision 2 del design prohibe (ya
resuelta para `Usage` y `Block.provider_metadata`, pero nunca aplicada a
`stop_reason`). `src/erickfp/agent/agent.py::Agent.run_turn` decide si continuar el
loop de tools comparando `response.stop_reason != "tool_use"` -- convencion
Anthropic-style, la misma que usan **todos** los `Provider` fake de
`tests/agent/*.py`. Contra un fake, el string coincidia siempre (los fakes ya
emiten `"tool_use"`/`"end_turn"` literalmente); contra Gemini/Gemma real, el
string era `"tool_calls"`/`"stop"` -- **nunca** igual a `"tool_use"` -- por lo que
`Agent.run_turn` retornaba el turno de inmediato en cuanto recibia la primera
respuesta, saltandose el permission gate por completo, incluso cuando el modelo si
pedia ejecutar una tool.

Esto explica por que los 243 tests de la suite (dobles/fakes en todas las capas)
seguian en verde: el bug solo se manifiesta en la frontera real
Provider-real <-> Agent, que ningun test unitario ni de integracion con doble
ejercita -- exactamente el tipo de gap que el smoke E2E de la tarea 9.2 existe para
encontrar.

### 5.3 Fix (TDD, RED -> GREEN)

**RED**: se actualizaron las aserciones de `tests/provider/test_litellm_gemini.py`
(`test_send_translates_text_response_to_response_and_block`,
`test_send_translates_tool_call_response_to_tool_use_block`) para exigir el
`stop_reason` canonico (`"end_turn"`/`"tool_use"`) en vez del crudo de litellm, y se
agrego `test_stop_reason_is_domain_type_no_litellm_leak` (parametrizado:
`tool_calls->tool_use`, `stop->end_turn`, `length->end_turn`, `None->end_turn`).
5 tests fallaron contra el codigo pre-fix, confirmando el RED.

**GREEN**: se agrego `_STOP_REASON_MAP` (tabla de normalizacion
OpenAI-style -> Anthropic-style) en `litellm_gemini.py`, aplicada en `_to_response`
antes de construir el `Response`. Cualquier `finish_reason` no listado cae a
`"end_turn"` (mismo default seguro que ya existia). 13/13 tests del archivo pasan;
suite completa 247/247, ruff/mypy/lint-imports limpios tras el fix.

### 5.4 Re-verificacion post-fix contra el modelo real

**Tool call aprobada** (`y`) -- el prompt del gate SI aparece y el comando SI se
ejecuta de verdad:

```
tu> Ejecutar bash({"command": "echo hola_marca > smoke_marker.txt"})? [y/N]
erickfp> OK. He ejecutado el comando `echo hola_marca > smoke_marker.txt`. El
archivo ha sido creado correctamente.
```

Verificacion en disco (fuera del proceso del chat):

```
$ cat smoke_marker.txt
hola_marca
```

**Tool call denegada** (`n`) -- el gate bloquea la ejecucion real, el modelo recibe
`is_error=true` con el motivo de denegacion y responde en consecuencia, el archivo
NUNCA se crea:

```
tu> Ejecutar bash({"command": "echo deny_test > smoke_marker_denied.txt"})? [y/N]
erickfp> El comando ... ha recibido una respuesta de denegacion segun el contexto
del entorno de pruebas, lo que confirma que el sistema de permisos esta operando
segun lo esperado ...
```

```
$ ls smoke_marker_denied.txt
ls: cannot access 'smoke_marker_denied.txt': No such file or directory
```

`/tokens` tras estos turnos reporta acumulado real no-cero en ambos casos
(`entrada=3652 salida=228 total=3880` aprobado; `entrada=3625 salida=338 total=3963`
denegado -- sesiones independientes, cada una arranca su propio `TokenTracker`).

## 6. Resumen de sesion persistido en SQLite (memoria-avanzada)

Cada sesion de chat con al menos un turno real, al salir (`salir` o `EOFError`),
dispara `_persist_session_summary`: una sintesis real via `provider.send` (turno
adicional) guardada como `Entry(kind="session-summary")`. Verificado directamente
en el `SqliteStore` real del directorio de smoke, tras la bateria completa de
sesiones de este smoke:

```
$ sqlite3 .ErickFP/memory/erickfp.db \
    "SELECT id, kind, ts, substr(content,1,120) FROM entries ORDER BY id;"
1|session-summary|2026-07-05T13:12:04Z|El usuario definio los axiomas raiz y los
  roles especializados del Ciclo Cogito de ErickFP. El agente asimilo este marco
  operativo...
2|session-summary|2026-07-05T13:12:45Z|...
...
6|session-summary|2026-07-05T13:22:03Z|...
```

6 filas `session-summary` -- una por cada sesion real de este smoke (turno de texto,
tool aprobada, tool denegada, y los reintentos por el 500 transitorio inicial que SI
llegaron a tener al menos un turno). Ninguna sesion vacia (solo comandos slash,
sin `GEMINI_API_KEY`) genero una fila -- confirma el Scenario "sesion sin turnos no
genera resumen vacio innecesario" tambien con el Store real (no solo con el doble de
`tests/cli/test_chat.py`).

## 7. Arranque limpio sin `mcp.json`

Ningun archivo de salida de todo el smoke (`grep -il mcp out_*.txt`) contiene
mencion alguna a MCP: `discover_tools(root, warn=...)` retorno `[]` en silencio en
las 8+ sesiones de chat de este smoke, sin imprimir advertencia (comportamiento
esperado -- MCP es opt-in, spec mcp-support). El registry de tools quedo identico en
todas las sesiones: `bash, read_file, write_file, recall, delegate_research`.
Conforme al riesgo documentado del Lote 8 (MCP contra servidor real diferido al
Ciclo 3), este smoke **no** probo un servidor MCP real -- solo el camino "config
ausente".

## Conclusion

- Suite: **247/247** tests (243 previos + 4 nuevos del fix), cobertura 95%,
  ruff/mypy/lint-imports limpios.
- Banner + fallback: verificados con pty real (colores truecolor confirmados) y
  con salida redirigida (branch de ancho confirmado).
- Slash commands: 100% locales, cero llamadas al Provider.
- Turno real de texto + `/tokens`: OK tras un reintento por inestabilidad transitoria
  del proveedor (esperado, mismo patron del ciclo 1).
- **Tool call real, aprobada y denegada: OK unicamente despues del fix de
  `stop_reason` documentado en la seccion 5** -- antes del fix, el harness nunca
  ejecutaba una tool real contra Gemini/Gemma pese a que la suite con dobles pasaba
  en verde. Este es el hallazgo mas importante del ciclo: el gap entre "los tests
  con fakes pasan" y "el sistema funciona contra el proveedor real" solo lo revela
  un smoke E2E real, justificando su lugar como tarea obligatoria del Lote 9.
- Resumen de sesion: persistido correctamente en SQLite real, sesion por sesion.
- MCP: chat arranca limpio sin `mcp.json`, sin fugas de advertencias.

## 8. Tabla de trazabilidad final (tarea 9.4)

Insumo directo para `sdd-verify`: cada escenario `Scenario:` de las 11 specs de
`openspec/changes/harness-v0-2/specs/*/spec.md` mapeado a un test real que pasa hoy
(`pytest --collect-only` confirma **247 tests recolectados**, `pytest -q` confirma
**247 passed**). Conteo real de escenarios con encabezado `#### Scenario:` en los 11
archivos: **55** (no 56 -- el docstring de cabecera de `tasks.md`, escrito en la fase
`sdd-tasks`, redondeo/estimo antes de que los specs quedaran finalizados; los 55
reales estan todos cubiertos, ver detalle abajo -- diferencia de conteo documentada
aqui para que `sdd-verify` no la reporte como escenario faltante).

### ui-polish (6)

| Scenario | Test |
|---|---|
| Arranque muestra el banner desde el asset | `tests/cli/test_chat.py::test_chat_startup_renders_banner_and_uses_decorated_input` |
| Regeneración del asset | `tests/ui/test_gen_portada.py::test_parses_portada_html_into_rich_text_asset` (+ `test_parses_real_portada_html_25x149`) |
| Terminal ancha (>=149 columnas) | `tests/ui/test_banner.py::test_wide_terminal_renders_full_banner` |
| Terminal angosta (<149 columnas) | `tests/ui/test_banner.py::test_narrow_terminal_renders_fallback_panel` |
| Prompt en cuadro con tema | `tests/ui/test_input_frame.py::test_decorated_prompt_uses_theme_panel` |
| Consistencia de tema entre banner e input | `tests/ui/test_theme.py::test_banner_and_input_share_same_palette` |

### permission-policy (6)

| Scenario | Test |
|---|---|
| AlwaysAsk equivalente al gate del ciclo 1 | `tests/agent/test_policy.py::test_always_ask_matches_cycle1_gate_behavior` |
| AllowList aprueba sin preguntar | `tests/agent/test_policy.py::test_allowlist_approves_without_asking` |
| AskOnce pregunta una sola vez por sesión | `tests/agent/test_policy.py::test_askonce_asks_once_then_reuses_decision` |
| AllowList no cubre escrituras en core | `tests/hooks/test_core_guard_policy.py::test_allowlist_and_askonce_never_bypass_core_guard[AllowList]` |
| AskOnce no memoriza aprobación sobre core | `tests/hooks/test_core_guard_policy.py::test_allowlist_and_askonce_never_bypass_core_guard[AskOnce]` |
| Respuesta ambigua bajo AskOnce | `tests/agent/test_policy.py::test_askonce_ambiguous_response_is_denial_not_cached` |

### slash-commands (5)

| Scenario | Test |
|---|---|
| /help lista comandos | `tests/cli/test_slash_commands.py::test_help_lists_available_commands` |
| /tools lista tools registradas | `tests/cli/test_slash_commands.py::test_tools_lists_registry_in_stable_order` |
| /clear limpia el historial | `tests/cli/test_slash_commands.py::test_clear_resets_history_and_reinjects_context` |
| Comando válido interceptado | `tests/cli/test_slash_commands.py::test_slash_input_never_reaches_provider` |
| Comando desconocido | `tests/cli/test_slash_commands.py::test_unknown_slash_command_reports_local_error` |

### token-viewer (3)

| Scenario | Test |
|---|---|
| Reporte con modelo de pricing conocido | `tests/cli/test_slash_commands.py::test_tokens_reports_usage_and_cost_known_pricing` |
| Modelo sin pricing conocido | `tests/cli/test_slash_commands.py::test_tokens_unknown_pricing_reports_unknown_cost` |
| /tokens antes del primer turno | `tests/cli/test_slash_commands.py::test_tokens_before_first_turn_reports_zero` |

### memory-store (delta, 6)

| Scenario | Test |
|---|---|
| Resumen persistido al salir | `tests/cli/test_chat.py::test_session_end_persists_summary_via_provider_synthesis` |
| Sesión sin turnos no genera resumen vacío innecesario | `tests/cli/test_chat.py::test_session_without_turns_skips_or_saves_empty_summary_safely` |
| Recall exitoso | `tests/tools/test_recall.py::test_recall_tool_uses_injected_duck_typed_store` (+ `tests/memory/test_sqlite_store.py::test_recall_matches_by_like_on_content_and_tags` a nivel Store) |
| Recall como Tool pasa por el gate | `tests/agent/test_loop.py::test_recall_tool_passes_through_gate_like_other_tools` |
| Preamble presente al iniciar sesión | `tests/cli/test_chat.py::test_preamble_loaded_before_first_turn` |
| Preamble incluye resumen de la sesión anterior | `tests/memory/test_sqlite_store.py::test_preamble_includes_latest_session_summary` |

### provider-layer (delta, 6)

| Scenario | Test |
|---|---|
| Reintento exitoso tras 5xx transitorio | `tests/provider/test_litellm_gemini_retry.py::test_retries_on_5xx_then_succeeds` |
| Agotar intentos produce ProviderError limpio | `tests/provider/test_litellm_gemini_retry.py::test_exhausts_attempts_raises_clean_provider_error` |
| Errores no transitorios no se reintentan | `tests/provider/test_litellm_gemini_retry.py::test_non_transient_4xx_does_not_retry` |
| Respuesta incluye conteo de tokens | `tests/provider/test_litellm_gemini.py::test_response_usage_is_domain_type_no_litellm_leak` (+ `tests/agent/test_tokens.py::test_tracker_accumulates_usage_across_turns`) |
| Multi-turno preserva thought signature | `tests/provider/test_thought_signature_roundtrip.py::test_tool_use_raw_id_with_thought_signature_is_reinjected_on_next_turn` (+ `test_text_only_thought_signature_is_reinjected_on_next_turn`) |
| Retry preserva thought signature entre reintentos | `tests/provider/test_thought_signature_roundtrip.py::test_retry_preserves_thought_signature` |

### compaction (5)

| Scenario | Test |
|---|---|
| Historial excede el umbral configurado | `tests/compaction/test_sliding_window.py::test_history_exceeding_threshold_shrinks_keeping_recent_turns` (Summarize: `tests/compaction/test_summarize.py::test_summarize_condenses_old_turns_and_drops_stale_signatures`, cobertura adicional del mismo Requirement) |
| Compaction nunca corre dentro de Provider.send | `tests/provider/test_litellm_gemini.py::test_provider_send_never_invokes_compaction_strategy` |
| Corte candidato cae dentro de un par tool_use/tool_result | `tests/compaction/test_safe_split_point.py::test_split_candidate_falls_inside_a_pair_adjusts_backward` |
| Ningún par roto tras compactar (invariante parametrizado) | `tests/compaction/test_safe_split_point.py::test_never_splits_a_tool_use_tool_result_pair` |
| Sin bloques tool_use pendientes | `tests/compaction/test_safe_split_point.py::test_no_pending_pairs_applies_threshold_cut_directly` |

### subagents (4)

| Scenario | Test |
|---|---|
| Research solo tiene tools de lectura | `tests/subagents/test_research.py::test_research_registry_contains_only_read_only_tools` |
| Research no puede escribir | `tests/subagents/test_research.py::test_research_cannot_write_unknown_tool_no_execution` |
| Tool calls internas del subagente no piden aprobación individual | `tests/subagents/test_delegate.py::test_internal_subagent_calls_do_not_reask_approval` |
| core_guard bloquea escritura en core incluso dentro del subagente | `tests/subagents/test_research.py::test_core_guard_active_inside_subagent` |

### mcp-support (3)

| Scenario | Test |
|---|---|
| Tool MCP descubierta se registra como cualquier tool local | `tests/tools/test_registry.py::test_mcp_tool_appended_at_end_without_reordering_locals` |
| Tool MCP pasa por el gate | `tests/agent/test_loop.py::test_mcp_tool_passes_through_same_gate_and_policy` |
| Transporte no soportado (edge, fuera de alcance) | `tests/tools/test_mcp.py::test_non_stdio_transport_rejected_with_clear_error` |

### tool-registry (delta, 4)

| Scenario | Test |
|---|---|
| Tool MCP se registra en el mismo registry | `tests/tools/test_registry.py::test_mcp_tool_appended_at_end_without_reordering_locals` |
| Mismo orden en llamadas repetidas | `tests/tools/test_registry.py::test_definitions_order_is_stable_across_repeated_calls` |
| Nueva tool se añade al final | `tests/tools/test_registry.py::test_new_tool_is_appended_at_the_end_without_reordering` |
| Tool MCP se añade al final sin reordenar las locales | `tests/tools/test_registry.py::test_mcp_tool_appended_at_end_without_reordering_locals` |

### agent-loop (delta, 7)

| Scenario | Test |
|---|---|
| Entrada con "/" no llega al Provider | `tests/cli/test_slash_commands.py::test_slash_input_never_reaches_provider` |
| Provider solicita una tool inexistente | `tests/agent/test_loop.py::test_unknown_tool_returns_is_error_result_without_raising` |
| Aprobación explícita | `tests/agent/test_gate.py::test_gate_approves_only_on_explicit_y` (+ `test_gate_approval_executes_the_real_tool`) |
| Negación explícita | `tests/agent/test_gate.py::test_gate_denial_produces_tool_result_is_error_true_no_exception` |
| Respuesta vacía o no reconocida (default deny) | `tests/agent/test_gate.py::test_gate_denies_by_default_on_empty_or_invalid_input` |
| Ninguna tool se ejecuta sin pasar por el gate | `tests/agent/test_loop.py::test_no_tool_executes_without_gate_and_policy_regardless_of_policy_impl` |
| PermissionPolicy AlwaysAsk preserva comportamiento del ciclo 1 | `tests/agent/test_policy.py::test_always_ask_matches_cycle1_gate_behavior` |

**Total verificado: 55/55 escenarios con al menos un test real que pasa hoy** (247
tests totales en la suite, incluyendo triangulaciones y tests de arquitectura no
mapeados 1:1 a un escenario pero que refuerzan el mismo Requirement). Este smoke
ademas sumo 4 tests nuevos (`tests/provider/test_litellm_gemini.py`) fuera de esta
tabla, especificos del hallazgo de la seccion 5 (normalizacion de `stop_reason`) --
no corresponden a un escenario de spec nuevo, sino a un contrato de dominio
(Decision 2: "ningun tipo nativo de litellm cruza hacia el llamador") que ya existia
implicitamente pero no estaba probado para `stop_reason`.
