# Design: Harness v0.2 — Agente pulido y extensible

## Technical Approach

Traducir los 8 patrones del roadmap byo-coding-agent + ui-polish a Python respetando el contrato import-linter y los axiomas raíz (#702). Toda interfaz nueva es `typing.Protocol` (Decisión raíz 5). Todo comportamiento nuevo es **opt-in con default bit-a-bit equivalente al ciclo 1** (AlwaysAsk, NoCompaction, retry attempts=2), de modo que el rollback de un lote solo desactiva la mejora sin regresión. Se reutilizan los seams ya existentes: `run_chat_session(read_line=...)` para el input decorado, `run_turn(hook_manager, ctx)` para colgar policy/compaction/tracker, y el patrón "adapter único" (litellm solo en un módulo) para MCP.

## Contrato de capas extendido (Decisión 1)

Nuevas capas: `ui`, `compaction`, `subagents`. Orden top→bottom (pyproject `[tool.importlinter]`):

```
erickfp.cli
erickfp.cogito
erickfp.subagents
erickfp.agent
erickfp.compaction
erickfp.hooks | erickfp.tools | erickfp.provider | erickfp.memory | erickfp.ui
erickfp.api
```

**Ciclo delegate (equivalente Python del "delegate en main" de Go, cap.11):** una `DelegateTool` necesita construir un sub-`Agent` (capa agent) + un subset del registry (capa tools). Si viviera en `tools/`, `tools → agent` cerraría el ciclo `tool→subagent→agent→tool`. **Resolución:** `DelegateTool` (y `research.py`) viven en la capa **subagents** (por encima de agent). Su *definición* está en subagents; su *registro* ocurre en el composition root (`cli.py`), que arma un registry extendido añadiendo delegate a las tools base. `tools/` nunca importa agent/subagents. Análogo a MCPTool/RecallTool: definidas abajo, inyectadas arriba.

## Architecture Decisions

### D2 — PermissionPolicy (padre: Decisión raíz 10 + Robustez innegociable)
| Aspecto | Decisión |
|--------|----------|
| Firma | `Protocol PermissionPolicy.decide(tool_name, tool_input) -> Literal["allow","deny","ask"]` en `agent/policy.py` |
| Punto de inyección | `run_tool_with_gate(tool, block, policy=None)`; `run_turn` threadea `policy` desde `cli`. Default `None`/`AlwaysAsk` → `confirm()` idéntico al ciclo 1 (bit-a-bit) |
| Semántica | `allow`→execute sin prompt; `ask`→`confirm()` actual; `deny`→`tool_result is_error` (nunca ejecuta) |
| Orden vs hooks | `core_guard` SIEMPRE por encima: `PreToolUse` corre en `loop.py` ANTES del gate; su `deny` bloquea sin consultar policy |
| AskOnce | set en memoria del objeto policy (session-scoped, no persiste a disco — YAGNI) |

**Rechazado:** decidir dentro de `confirm()` (mezcla UI con política) y policy en `api` (es concern de agent). **Rationale:** el seam nuevo es un parámetro opcional; el default preserva el axioma "preguntar siempre".

### D3 — ui-polish (padre: Legibilidad prio-1 + Decisión raíz 6)
| Aspecto | Decisión |
|--------|----------|
| Pipeline portada | `scripts/gen_portada.py` (exento de lint) parsea los spans rgb 25×149 → genera `ui/_portada_asset.py`: lista de `(char, fg, bg)` o `Text` Rich pre-ensamblado (**no HTML en runtime**) |
| Render | `rich.panel.Panel(Text truecolor, style=fondo #222222)`; tema cyan #00FFFF / verde #00FF00 |
| Fallback <149 cols | `Console.width`: ≥149 banner completo; <149 → versión mini (título estilizado en Panel), nunca recorte que rompa el arte |
| Input decorado | `cli` compone `decorated_read_line` = `ui.frame(label)` (Rich rule/Panel) + **`gate.read_line`** para el stdin; se pasa como `read_line=` a `run_chat_session`. Preserva el consumer único de stdin (spike 2.3) |

**Rechazado:** parsear HTML en runtime (lento, frágil) y un segundo `input()` en `ui` (rompería consumer único). **Rationale:** asset precomputado + inyección del reader ya soportada.

### D4 — slash-commands (padre: Decisión raíz 6)
Mini-registry `dict[str, handler]` en `cli.py`; dispatch al inicio del loop REPL **antes** del provider (si `startswith("/")` → maneja y `continue`). `/model`→`provider.set_model(arg)`; `/clear`→`messages=[]`, `first_turn=True` (re-inyecta contexto raíz el próximo turno); `/tools`→`tools.definitions()`; `/tokens`→tracker; `/help`. **Rechazado:** framework de plugins (YAGNI). **Rationale:** comandos locales, cli-layer, sinérgicos con token-viewer.

### D5 — compaction (padre: Extensibilidad + Robustez Gemma-4)
| Aspecto | Decisión |
|--------|----------|
| Interfaz | `Protocol CompactionStrategy.compact(messages) -> messages` (capa `compaction`) |
| Impls | `NoCompaction` (identidad, **default**), `SlidingWindow(max)`, `Summarize(provider)` |
| Invocación | inicio de `run_turn`, antes del primer `provider.send` |
| SafeSplitPoint | dado corte `k` (conservar cola), *mientras* `messages[k].role=="user"` contenga algún `tool_result`, `k -= 1` → nunca se retiene un `tool_result` huérfano ni se descarta un `tool_use` cuya respuesta se conserva |
| Thought signatures | la firma viaja DENTRO del mensaje assistant del `tool_use`; SafeSplitPoint que mantiene el par intacto **también** mantiene la firma. `Summarize` descarta a propósito firmas de turnos colapsados (ya no son round-trips vivos) |

**Rechazado:** compactar por bloque (rompería pares/firmas). **Rationale:** granularidad de mensaje = invariante testeable.

### D6 — token-viewer (padre: Legibilidad/transparencia)
`Usage(prompt, completion, total)` dataclass de dominio en `api/types.py`; `Response.usage: Usage | None` (el adapter lo llena desde `raw.usage`, **sin filtrar tipos litellm**). `TokenTracker` (agent) acumula por sesión: `run_turn(tracker=None)` hace `tracker.add(response.usage)`. Costo Gemma free tier = `—/gratis` (no se inventa precio). `/tokens` lee el tracker. **Rechazado:** exponer `raw` (fuga de tipos). **Rationale:** un campo de dominio cruza la frontera limpio.

### D7 — subagents (padre: Extensibilidad prio-2 + Decisión raíz 5)
Extraer clase `Agent` en `agent/agent.py` (estado: provider/tools/hooks/policy/compaction/tracker; método `run_turn(messages)`); `run_turn` libre queda como wrapper que preserva la firma (no rompe 129 tests). `subagents/research.py` construye un `Agent` con registry subset **read-only** (solo `read_file`) + policy de auto-aprobación (AllowList read-only) **con `core_guard` activo**. `DelegateTool` (subagents) instancia Research; salida en la UI indentada con `↳`. **Rechazado:** duplicar el loop. **Rationale:** una clase reutilizable habilita subagentes y MCP sin reescritura.

### D8 — mcp-support (padre: Extensibilidad + cap.14)
SDK oficial `mcp` **permitido**: el axioma "prohibido SDK nativo" (Decisión 4) protege la frontera **LLM** (interfaz Provider); MCP es transporte de *tools* (JSON-RPC/stdio), ortogonal al LLM → no viola el axioma. Se aísla en `tools/mcp.py` (único módulo que importa `mcp`, espejo de la regla litellm). `MCPTool` envuelve cada tool remota en el `Protocol Tool`; config `.ErickFP/mcp.json` (command/args, solo stdio, sin OAuth). Registro en el composition root. **Alternativa rechazada:** JSON-RPC propio (reinventa; el SDK ya está aislado tras la interfaz Tool).

### D9 — memoria-avanzada (padre: Decisión raíz 7)
`RecallTool` (tools) envuelve un objeto con `.recall(query,limit)` **inyectado** desde cli (no importa `memory.Store` → respeta capas); pasa por el gate. Resumen fin de sesión: al salir de `chat`, `provider.send` de síntesis + `store.save(Entry(kind="session-summary"))`, envuelto en `try/except ProviderError` → si falla, se omite sin crashear. `preamble()` acotado con límite de tamaño/entradas. **Rationale:** duck-typing evita cross-import de mismo tier.

### D10 — retry configurable (padre: Robustez innegociable)
`LiteLLMGeminiProvider.__init__(max_attempts=2, backoff_seconds=2.0)` reemplaza las constantes `_MAX_ATTEMPTS`/`_BACKOFF_SECONDS` por atributos; cli/config los pasa. Solo reintenta 5xx/timeout; agota → `ProviderError` limpio. Default preserva el comportamiento actual.

## Data Flow — Secuencia REPL v0.2

```
Usuario ─(input decorado: ui.frame + gate.read_line)→ REPL (cli.run_chat_session)
  │ ¿"/"? ── sí → SlashRegistry.dispatch → continue (/model→set_model, /clear→reset)
  └─ no → compone Message(user) (+system_context si first_turn)
        ▼
  Agent.run_turn (agent/loop):
    1. CompactionStrategy.compact(messages)      # SafeSplitPoint; NoCompaction default
    2. provider.send(messages, tools)            # adapter litellm, retry configurable
         → Response(content, stop_reason, usage)
    3. TokenTracker.add(response.usage)
    4. por cada tool_use:
         a. HookManager.run("PreToolUse")         # core_guard PRIMERO; deny→bloquea
         b. run_tool_with_gate(tool, block, policy)
              PermissionPolicy.decide → allow(exec) | ask(confirm/gate.read_line) | deny(is_error)
         c. HookManager.run("PostToolUse")
         # delegate → Agent Research read-only, auto-allow, core_guard activo, salida "↳"
    5. repite hasta stop_reason != "tool_use"
        ▼
  REPL imprime respuesta (Rich tema cyan/verde)
  ...
salir → resumen fin de sesión (provider.send; try/except ProviderError) → store.save(session-summary)
```

## File Changes (resumen)

| Área | Acción |
|------|--------|
| `ui/` + `ui/_portada_asset.py` + `scripts/gen_portada.py` | Crear (banner, input decorado, generador) |
| `agent/policy.py`, `agent/agent.py`, `agent/tokens.py` | Crear (policy, clase Agent, TokenTracker) |
| `agent/gate.py`, `agent/loop.py` | Modificar (policy+compaction+tracker opcionales) |
| `compaction/` | Crear (Strategy + SafeSplitPoint) |
| `subagents/` (research.py, delegate.py) | Crear |
| `tools/mcp.py`, `tools/recall.py` | Crear (adapters inyectados) |
| `provider/{base,litellm_gemini}.py`, `api/types.py` | Modificar (Usage, retry configurable) |
| `memory/sqlite_store.py` | Modificar (preamble acotado, session-summary) |
| `cli.py` | Modificar (banner, slash dispatch, composition root del registry extendido) |
| `pyproject.toml` | Modificar (capas ui/compaction/subagents + dep `mcp` en Lote 8) |

## Interfaces nuevas

```python
# agent/policy.py
class PermissionPolicy(Protocol):
    def decide(self, tool_name: str, tool_input: str) -> Literal["allow", "deny", "ask"]: ...
# compaction/base.py
class CompactionStrategy(Protocol):
    def compact(self, messages: list[Message]) -> list[Message]: ...
# api/types.py
@dataclass
class Usage: prompt_tokens: int; completion_tokens: int; total_tokens: int
```

## Testing Strategy (STRICT TDD, 129 tests base)
| Capa | Qué | Cómo |
|------|-----|------|
| Unit | SafeSplitPoint nunca parte par; AlwaysAsk==gate ciclo1; AllowList/AskOnce; policy deny no ejecuta | RED→GREEN parametrizado |
| Unit | Fallback ui por ancho; Usage cruza sin tipos litellm; retry solo 5xx | dobles/monkeypatch |
| Integration | delegate → Research no puede escribir; core_guard sobre subagente; MCPTool tras gate | registry extendido + fakes |
| Arch | lint-imports con capas ui/compaction/subagents | test_architecture_import_rules |

## Migration / Rollout
Sin migración de datos. 8 lotes aditivos, orden = propuesta: 1 ui-polish · 2 robustez/retry+3 SUGGESTIONS · 3 slash+tokens · 4 permission-policy · 5 memoria · 6 compaction · 7 subagentes · 8 mcp. Cada lote extiende el contrato de capas en su propio commit y deja la suite verde antes de avanzar.

## Open Questions
- [ ] `.ErickFP/mcp.json` como fuente de config MCP (asumido; confirmar en Lote 8).
- [ ] Umbral exacto del preamble acotado y de SlidingWindow(max) — calibrar con Gemma-4 real.
- [ ] Validación empírica de thought signatures bajo compaction (bloqueada por GEMINI_API_KEY revocada, spike 2.1).
