# Propuesta: Harness v0.2 — De MVP a agente pulido y extensible

## Intent

El ciclo 1 (mvp-ciclo-cogito) entregó el núcleo cartesiano funcional (129 tests, 95% cobertura, gate y core_guard verificados). Ahora el harness es correcto pero **crudo**: arranca sin identidad visual, pregunta permiso de forma rígida, no tiene comandos de control, no gestiona ventanas largas (Gemma 4 se degrada) y su memoria es pasiva. Este cambio traduce los 8 patrones del roadmap byo-coding-agent (caps. 02/05/07/11/14/16/19) + 1 capability de branding pedida hoy por el usuario, y endurece la base con las deudas del ciclo 1. Éxito = agente con identidad visual, control de sesión, robustez ante inestabilidad del modelo y extensibilidad probada (subagentes, MCP), sin romper ningún axioma raíz ni el contrato de capas.

## Scope

### In Scope (8 capabilities + robustez)
- **ui-polish** (nueva, prioridad 1 — pedido explícito): banner ASCII de portada.html (25×149, paleta del tema) como asset **precomputado** con Rich truecolor en cuadro, fallback adaptativo <149 cols; input de prompts decorado en cuadro con bordes.
- **permission-policy**: interfaz PermissionPolicy (AlwaysAsk default, AllowList, AskOnce) entre loop y registry.
- **slash-commands**: /help /model /tools /clear en el REPL.
- **token-viewer**: /tokens — uso y costo por sesión.
- **memoria-avanzada**: preamble automático mejorado + recall como tool + resumen fin de sesión.
- **compaction**: CompactionStrategy (sliding window + summarize + SafeSplitPoint).
- **subagentes**: Agent reutilizable + Research subagent read-only + delegate tool.
- **mcp-support**: tools remotas MCP tras la interfaz Tool.
- **Robustez/deuda**: retry configurable del adapter (attempts/backoff por config) + las 3 SUGGESTIONS del verify-report ciclo 1.

### Out of Scope
- **tui-textual (cap.12) — diferido a Ciclo 3.** Trade-off: es el lote más grande (viewport, scrollback, event loop de Textual, aprobación visual) y **solaparía** con ui-polish. Meterlo aquí infla el cambio y contradice YAGNI por fase. **Recomendación: fuera.** ui-polish da el valor visual inmediato que el usuario pidió hoy sobre el REPL de texto plano ya existente; Textual merece su propio ciclo cuando la superficie CLI se estabilice.
- Cache/optimización de tokens más allá del contador; auth OAuth para MCP (solo transports locales/stdio en esta fase).

## Capabilities

### New Capabilities
- `ui-polish`: banner de arranque + input decorado con Rich truecolor y fallback por ancho.
- `permission-policy`: política de permisos pluggable (AlwaysAsk/AllowList/AskOnce) delante del gate.
- `slash-commands`: comandos de control del REPL (/help /model /tools /clear).
- `token-viewer`: contabilidad y reporte de uso/costo por sesión (/tokens).
- `compaction`: estrategia de compactación de historial segura (nunca parte tool_use/tool_result).
- `subagents`: agente reutilizable + subagente Research read-only + tool delegate.
- `mcp-support`: descubrimiento e invocación de tools MCP remotas tras la interfaz Tool.

### Modified Capabilities
- `agent-loop`: el gate consulta PermissionPolicy antes de preguntar; el REPL despacha slash-commands; escenario formal "tool desconocida en el registry" (SUGGESTION-1/3).
- `provider-layer`: retry configurable con backoff; exposición de uso de tokens/costo para token-viewer.
- `memory-store`: preamble enriquecido + recall expuesto como Tool + resumen de fin de sesión.
- `tool-registry`: admite tools remotas MCP junto a las locales sin reordenar las existentes.

## Approach

Traducir cada patrón de la guía a Python respetando el contrato import-linter (cli → cogito → agent → hooks|tools|provider|memory → api). Todas las interfaces nuevas son `typing.Protocol` (patrón Decisión 5). Cambios clave de arquitectura a resolver en sdd-design:
- **PermissionPolicy** se inyecta en el gate (capa agent); default AlwaysAsk preserva la Decisión 10 (preguntar siempre) — la política es opt-in, la robustez del gate es innegociable.
- **compaction** es capa nueva entre agent y provider → **extiende el contrato import-linter**; SafeSplitPoint garantiza que nunca se parte entre un tool_use y su tool_result.
- **subagents**: Agent se vuelve reutilizable; Research recibe solo tools read-only; delegate es una Tool que instancia un sub-Agent acotado.
- **mcp-support** vive tras la interfaz Tool existente (adapter MCP análogo al adapter LiteLLM único).
- **ui-polish**: portada.html se parsea **en build-time** a un asset de rich.text.Text (no HTML en runtime).

## Trazabilidad a axiomas raíz (por capability)

| Capability | Axioma raíz / Decisión |
|-----------|------------------------|
| ui-polish | Legibilidad (prioridad 1) + Decisión 6 (REPL texto; TUI posterior) |
| permission-policy | Decisión 10 (permisos; policy en fase posterior) + Robustez innegociable del gate |
| slash-commands | Decisión 6 (interfaz REPL) + Legibilidad |
| token-viewer | Legibilidad/transparencia del costo |
| memoria-avanzada | Decisión 7 (Store: save/recall/preamble) |
| compaction | Extensibilidad + Robustez (Gemma 4 en ventanas largas) |
| subagentes | Extensibilidad (prioridad 2) + Decisión 5 (Agent reutilizable) |
| mcp-support | Extensibilidad + interfaz Tool propia (cap.14) |
| robustez/retry | Robustez secundaria-innegociable + aprendizaje ciclo 1 |

## Affected Areas

| Área | Impacto | Descripción |
|------|---------|-------------|
| `src/erickfp/ui/` (nuevo) + asset portada | Nuevo | Banner Rich + input decorado + fallback por ancho |
| `src/erickfp/agent/{gate,loop}.py` | Modificado | Consulta PermissionPolicy; despacho slash-commands |
| `src/erickfp/agent/policy.py` (nuevo) | Nuevo | PermissionPolicy Protocol + 3 impls |
| `src/erickfp/cli.py` + REPL | Modificado | Banner al arrancar; slash-commands; /tokens |
| `src/erickfp/provider/{base,litellm_gemini}.py` | Modificado | Retry/backoff configurable; uso de tokens/costo |
| `src/erickfp/compaction/` (nuevo) | Nuevo | CompactionStrategy + SafeSplitPoint (capa nueva) |
| `src/erickfp/memory/sqlite_store.py` | Modificado | Preamble++, recall tool, resumen fin de sesión |
| `src/erickfp/subagents/` (nuevo) + `tools/delegate.py` | Nuevo | Agent reutilizable + Research + delegate |
| `src/erickfp/tools/mcp.py` (nuevo) | Nuevo | Adapter de tools MCP tras interfaz Tool |
| `pyproject.toml` (import-linter) | Modificado | Añadir capa `compaction` y `subagents` al contrato |
| `hooks/core_guard.py`, `hooks/adr_graph.py`, `agent/loop.py` | Modificado | Cobertura de ramas de error (SUGGESTION-1) |

## Risks

| Riesgo | Prob. | Mitigación |
|--------|-------|-----------|
| PermissionPolicy abre fuga en el gate (robustez innegociable) | Media | Default AlwaysAsk; tests de "ninguna tool sin gate"; AllowList/AskOnce opt-in con negación por defecto |
| ui-polish frágil en terminales angostas/sin truecolor | Media | Fallback adaptativo por ancho + degradación a Panel simple; asset precomputado, no parseo runtime |
| SafeSplitPoint parte tool_use/tool_result → error de API | Media | Invariante testeado: nunca cortar dentro de un par; tests parametrizados de límites |
| MCP añade dependencia externa inestable | Media | Adapter aislado tras interfaz Tool; solo transports locales/stdio; timeouts + retry |
| Retry enmascara errores reales de Gemma 4 | Baja | Solo reintenta 5xx/timeout; ProviderError limpio tras agotar attempts; backoff config |
| Alcance de 8 capabilities infla el ciclo | Alta | Entrega en 8 lotes independientes; cada lote deja la suite verde antes de avanzar |
| Nuevas capas rompen contrato import-linter | Media | Extender pyproject.toml en el mismo lote que introduce la capa; lint-imports en CI de cada lote |

## Rollback Plan

Cada capability es un lote aislado en su propio commit/rama de feature. Rollback = revertir el commit del lote sin tocar los demás (las capabilities nuevas son aditivas). Para capabilities **modificadas** (agent-loop, provider-layer, memory-store): el comportamiento previo se preserva por defecto (PermissionPolicy=AlwaysAsk, retry attempts=1, preamble legacy) → revertir solo desactiva la mejora sin regresión funcional. El asset de ui-polish y las capas nuevas (compaction, subagents, mcp) no tienen dependientes: eliminarlos no rompe el núcleo del ciclo 1. Si un lote deja la suite roja, no avanza (gate de lotes del ciclo 1).

## Secuencia de entrega por lotes

1. **Lote 1 — ui-polish** (pedido explícito, valor visual inmediato, independiente): asset precomputado + banner + input decorado + fallback.
2. **Lote 2 — Robustez/deuda ciclo 1**: retry configurable del adapter + 3 SUGGESTIONS (ramas de error loop/core_guard/adr_graph/cli + escenario "tool desconocida" en spec agent-loop). Endurece la base antes de construir encima.
3. **Lote 3 — slash-commands + token-viewer**: ambos en capa cli/REPL, simples y sinérgicos.
4. **Lote 4 — permission-policy**: interfaz entre loop y registry; toca el gate (riesgo medio, va tras la base endurecida).
5. **Lote 5 — memoria-avanzada**: modifica memory-store (preamble++, recall tool, resumen).
6. **Lote 6 — compaction**: capa nueva + extensión del contrato import-linter + SafeSplitPoint.
7. **Lote 7 — subagentes**: Agent reutilizable + Research read-only + delegate tool.
8. **Lote 8 — mcp-support**: el más complejo, dependencia externa aislada tras interfaz Tool.

Orden: pedido del usuario primero (1), robustez fundacional (2), luego de lo simple a lo complejo (3→8).

## Dependencies

- Rich (ya presente para CLI). Cliente MCP Python (nueva dep en Lote 8). Sin nuevas deps para lotes 1-7 más allá de las existentes.
- portada.html en la raíz del repo como fuente del asset (build-time).

## Success Criteria

- [ ] Banner ASCII se renderiza con paleta exacta del tema en cuadro; fallback legible en terminal <149 cols; input decorado en cuadro (ui-polish).
- [ ] PermissionPolicy con default AlwaysAsk no altera el comportamiento del gate del ciclo 1; AllowList/AskOnce probadas; ninguna tool se ejecuta sin política resuelta.
- [ ] /help /model /tools /clear /tokens operativos en el REPL; /tokens reporta uso y costo por sesión.
- [ ] Adapter reintenta 5xx/timeout con backoff configurable y emite ProviderError limpio tras agotar attempts.
- [ ] compaction reduce historial largo sin partir jamás un par tool_use/tool_result (invariante testeado).
- [ ] recall disponible como Tool; resumen de fin de sesión persistido; preamble enriquecido cargado antes del primer turno.
- [ ] delegate instancia un subagente Research read-only que no puede escribir (verificado por test).
- [ ] Al menos una tool MCP remota descubierta e invocada tras la interfaz Tool.
- [ ] Suite verde en cada lote; cobertura ≥85%; ruff/mypy/lint-imports limpios; contrato de capas extendido para compaction y subagents.
- [ ] Las 3 SUGGESTIONS del verify-report ciclo 1 cerradas.
