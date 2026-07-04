# ErickFP 🧠

**Harness agéntico de línea de comandos gobernado por el método cartesiano y un grafo de decisiones de arquitectura (ADR).**

ErickFP es un agente de IA para terminal que crea software de manera autónoma pero **estrictamente regulada**: ninguna acción ocurre sin consultar los axiomas raíz del proyecto, ninguna herramienta se ejecuta sin permiso humano explícito, y ninguna decisión técnica es válida si no traza un camino lógico hasta la raíz del grafo de decisiones.

> El modelo es el motor. El harness es todo lo demás. — filosofía heredada de la guía [byo-coding-agent](https://github.com/betta-tech/byo-coding-agent), traducida de Go a Python y extendida con el método de Descartes.

---

## Índice

1. [Filosofía](#filosofía)
2. [Características](#características)
3. [Arquitectura](#arquitectura)
4. [Requisitos](#requisitos)
5. [Instalación](#instalación)
6. [Configuración](#configuración)
7. [Uso rápido](#uso-rápido)
8. [El Ciclo Cogito](#el-ciclo-cogito)
9. [Desarrollo](#desarrollo)
10. [Estructura del proyecto](#estructura-del-proyecto)
11. [Flujo de trabajo con Git y GitHub](#flujo-de-trabajo-con-git-y-github)
12. [Seguridad](#seguridad)
13. [Documentación adicional](#documentación-adicional)

---

## Filosofía

ErickFP aplica los **cuatro preceptos del Discurso del Método de Descartes** al desarrollo de software con IA:

| Precepto cartesiano | Fase del harness | Comando |
|---|---|---|
| **Evidencia** (duda metódica) | Validación de requisitos: la IA se niega a avanzar ante ambigüedad | `erickfp duda` |
| **Análisis** (división) | Descomposición del problema en partes mínimas | `erickfp divide` |
| **Síntesis** (orden) | Implementación de lo simple a lo complejo | `erickfp ordena` |
| **Enumeración** (revisión) | Revisión completa de los resultados | `erickfp enumera` |

Todo gira en torno al directorio `.ErickFP/`, cuyo núcleo son dos artefactos **sagrados**:

- **`.ErickFP/core/Claude`** — los axiomas inmutables y trade-offs arquitectónicos del proyecto. Es la raíz del grafo de decisiones.
- **`.ErickFP/core/agents/`** — los roles de la IA (Planner, Coder, Reviewer) y sus límites.

**Regla de oro**: el agente **jamás** puede modificar esos archivos — un hook lo bloquea *incluso si el humano aprobó la operación en el permission gate*. Solo el humano los edita, y todo cambio exige un ADR de enmienda.

## Características

- 🤖 **Agent loop completo**: REPL conversacional donde el modelo llama herramientas (`bash`, `read_file`, `write_file`) en bucle hasta resolver la tarea.
- 🛡️ **Permission gate sin fuga**: toda ejecución de herramienta pide aprobación `y/n`. El default es denegar (Enter vacío, respuestas ambiguas → no). La negación vuelve al modelo como resultado de error — nunca como excepción — para que adapte su estrategia.
- 🔌 **Capa de proveedor agnóstica**: interfaz `Provider` propia con tipos propios; el único módulo que conoce LiteLLM es el adapter. Cambiar de modelo/proveedor es una línea. Prohibido (y verificado por test) importar SDKs nativos fuera del adapter.
- 🧭 **Ciclo Cogito**: cuatro comandos por fases secuenciales y bloqueantes que emiten artefactos markdown encadenados — cada fase valida el artefacto de la anterior o falla limpiamente.
- 🪝 **Hooks acumulativos por fase**: PreToolUse/PostToolUse/PhaseStart/PhaseEnd. El `core_guard` protege la raíz siempre; el hook de trazabilidad ADR valida que toda síntesis trace hasta un nodo raíz (búsqueda DFS sobre frontmatter YAML).
- 🗃️ **Memoria persistente**: `Store` con SQLite (`save`/`recall`/`preamble`) — las decisiones y sesiones sobreviven entre ejecuciones y se inyectan como preámbulo del contexto.
- 🧪 **Desarrollado con TDD estricto**: 126 tests (cobertura 95%), cada pieza escrita test-primero. Arquitectura de capas verificada por `import-linter`.
- 🎨 Tema de terminal cyan (`#00FFFF`) + verde (`#00FF00`).

## Arquitectura

Capas con dependencia unidireccional (verificadas por contrato de `import-linter` — nada de una capa inferior conoce a una superior):

```
cli.py            ← glue: Typer + Rich; ÚNICO módulo que toca la UI
  └── cogito/     ← orquestador del Ciclo Cogito (fases, artefactos)
        └── agent/    ← permission gate + agent loop
              └── hooks/ | tools/ | provider/ | memory/
                    └── api/    ← tipos propios, sin dependencias
```

- **`api/types.py`** — `Message`, `Block`, `ToolDef`, `Response`: la *lingua franca* interna. `Block.provider_metadata` transporta de forma opaca las *thought signatures* de Gemini entre turnos.
- **`provider/litellm_gemini.py`** — único import de `litellm`. Modelo default: `gemini/gemma-4-26b-a4b-it` (ADR-001, elegido con evidencia empírica). Incluye reintento acotado ante errores `500/INTERNAL` transitorios del proveedor.
- **`tools/`** — registry con orden estable de definiciones + `bash`, `read_file`, `write_file`.
- **`hooks/`** — motor inyectado (no global): `CoreGuardHook` (protege `core/*` resolviendo paths equivalentes: relativos, `..`, symlinks) y `AdrTraceabilityHook`.
- **`memory/sqlite_store.py`** — persistencia en `.ErickFP/memory/`.

## Requisitos

- **Python ≥ 3.10**
- **Una API key de Google Gemini** (gratuita, sin tarjeta): créala en [Google AI Studio](https://aistudio.google.com/apikey). El modelo default (Gemma 4) corre dentro del free tier.
- Linux/macOS (desarrollado y probado en Linux).

## Instalación

```bash
# 1. Clona el repositorio
git clone git@github.com:ErickFP7314/harnes-erickfp.git
cd harnes-erickfp

# 2. Crea el entorno virtual del proyecto (NUNCA instalar en el Python del sistema)
python3 -m venv .venv
source .venv/bin/activate

# 3. Instala el paquete en modo editable con dependencias de desarrollo
pip install -e ".[dev]"

# 4. Verifica la instalación
erickfp --help
```

## Configuración

Crea un archivo `.env` en la raíz del repositorio (ya está en `.gitignore` — **jamás lo commitees**):

```bash
# Edítalo directamente con tu editor; no pegues la key en chats ni terminales compartidas
printf 'GEMINI_API_KEY=TU_KEY_AQUI\n' > .env && chmod 600 .env
```

El modelo default es `gemini/gemma-4-26b-a4b-it` (ver `docs/spikes/thought-signature.md` para la comparativa que respaldó la decisión). Puedes usar cualquier modelo soportado por LiteLLM cambiándolo por código vía `LiteLLMGeminiProvider(model_name=...)` o `set_model()`.

## Uso rápido

```bash
# 1. Inicializa la raíz cartesiana en tu proyecto
erickfp init
#    → crea .ErickFP/ con core/Claude, core/agents/{planner,coder,reviewer}.md,
#      adr/, memory/ y hooks/. Re-ejecutarlo NUNCA sobrescribe la raíz sin confirmación.

# 2. (Recomendado) Edita .ErickFP/core/Claude con TUS axiomas y trade-offs

# 3. Conversa con el agente
erickfp chat
#    tu> lista los archivos de este directorio
#    [tool] bash {"command": "ls"}   ¿aprobar? [y/n] y
#    erickfp> Estos son los archivos: ...
#    ("salir", "exit" o Ctrl+D para terminar)
```

Cada herramienta que el modelo quiera ejecutar pedirá tu aprobación. **Solo `y` exacto aprueba** — todo lo demás deniega.

## El Ciclo Cogito

El flujo estructurado para crear software con el método cartesiano:

```bash
# Fase 1 — Evidencia: somete tu objetivo a duda metódica
erickfp duda "una API REST para gestionar tareas"
#   → si el objetivo es ambiguo, la IA PIDE CLARIFICACIÓN y no genera artefacto
#   → si es claro: genera .ErickFP/cogito/<slug>/duda.md y te muestra el slug

# Fase 2 — Análisis: descompone en partes mínimas (rol: Planner)
erickfp divide una-api-rest-para-gestionar-tareas

# Fase 3 — Síntesis: implementa según el plan (rol: Coder)
erickfp ordena una-api-rest-para-gestionar-tareas

# Fase 4 — Enumeración: revisión completa (rol: Reviewer)
erickfp enumera una-api-rest-para-gestionar-tareas
```

Reglas del ciclo:

- **Las fases son secuenciales y bloqueantes**: `divide` sin `duda.md` previo falla limpiamente con un mensaje claro (exit 1, sin traceback).
- Cada fase usa el **rol** correspondiente de `core/agents/` como contexto de sistema, siempre precedido por los axiomas de `core/Claude`.
- Los **hooks acumulan restricciones**: `core_guard` está activo en todas las fases; el hook de trazabilidad ADR exige que la síntesis trace hasta un nodo raíz del grafo.
- Los artefactos quedan en `.ErickFP/cogito/<slug>/` como markdown legible y versionable.

## Desarrollo

El proyecto se desarrolló (y se mantiene) con **TDD estricto**: test en rojo primero, implementación después.

```bash
source .venv/bin/activate

# Suite completa (126 tests, cobertura mínima 85%)
python -m pytest -q

# Linter + formato
python -m ruff check .
python -m ruff format --check .

# Tipos
python -m mypy src/erickfp

# Contrato de capas (arquitectura)
lint-imports
```

Los cuatro comandos deben pasar antes de cualquier commit. Reglas de contribución:

1. **Test primero**: ninguna funcionalidad sin su test RED→GREEN.
2. **Respeta las capas**: si `lint-imports` falla, tu diseño está en la capa equivocada — no "arregles" el contrato.
3. **Ningún SDK nativo de LLM** fuera de `provider/litellm_gemini.py` (hay un test AST que lo vigila).
4. **Decisiones de arquitectura → ADR**: cambios que alteren trade-offs se documentan trazando hasta la raíz.

## Estructura del proyecto

```
harnes-erickfp/
├── src/erickfp/          # el paquete (ver Arquitectura)
│   └── templates/        # plantillas raíz que erickfp init instala
├── tests/                # 126 tests (espejo de src/, + support/ con MockProvider)
├── docs/
│   ├── guia-de-uso.md    # guía paso a paso para usuarios
│   ├── smoke-e2e.md      # evidencia del smoke E2E real
│   └── spikes/           # investigaciones técnicas con evidencia empírica
├── scripts/              # spikes exploratorios (excluidos del linting)
├── openspec/
│   ├── specs/            # especificaciones vigentes (fuente de verdad, 7 capabilities)
│   └── changes/archive/  # ciclos SDD completados (proposal → verify → archive)
├── idea.md               # la idea original que dio origen al proyecto
└── pyproject.toml        # paquete, deps, pytest/ruff/mypy/import-linter
```

## Flujo de trabajo con Git y GitHub

Buenas prácticas adoptadas por este repositorio:

### Ramas

- **`main` siempre está verde**: nunca se commitea directo un cambio que rompa `pytest`/`ruff`/`mypy`/`lint-imports`.
- Trabaja en **ramas de feature** con prefijo por tipo: `feat/permission-policy`, `fix/gate-empty-input`, `docs/readme`.

```bash
git checkout -b feat/mi-cambio
# ... trabajo con TDD ...
git push -u origin feat/mi-cambio
# abre un Pull Request en GitHub
```

### Commits

- **Atómicos y descriptivos**: un commit = una unidad lógica (idealmente un ciclo RED→GREEN o un lote coherente).
- **Mensaje en imperativo con cuerpo explicativo**: la primera línea resume (≤72 caracteres), el cuerpo explica *qué* y *por qué* (el *cómo* ya está en el diff).
- Los commits de este repo siguen el patrón `<área>: <resumen>` con cuerpo detallado — revisa `git log` como referencia.

### Pull Requests

- Un PR por cambio SDD o feature; descripción con contexto, evidencia de tests y riesgos.
- Antes de abrir el PR, corre localmente los cuatro comandos de verificación (sección [Desarrollo](#desarrollo)).

### Lo que NUNCA se versiona

- `.env` y cualquier credencial (ya en `.gitignore`). Si una key toca un commit por accidente: **revócala inmediatamente** — reescribir el historial no des-filtra un secreto.
- `.venv/`, `__pycache__/`, `.codegraph/`, artefactos de runtime.

## Seguridad

- **Las API keys nunca viajan por chats, capturas de pantalla ni terminales compartidas.** Este proyecto lo aprendió en carne propia: Google detectó y revocó una key expuesta con `403 "reported as leaked"` en cuestión de horas.
- El `.env` vive con permisos `600` y gitignored.
- El permission gate y el `core_guard` son las dos defensas del harness: no las desactives; si necesitas menos fricción, el diseño previsto es una `PermissionPolicy` configurable (ver roadmap en `openspec/`).

## Documentación adicional

| Documento | Contenido |
|---|---|
| [`docs/guia-de-uso.md`](docs/guia-de-uso.md) | Guía paso a paso para usuarios generales, con sesión de ejemplo y solución de problemas |
| [`openspec/specs/`](openspec/specs/) | Las 7 especificaciones vigentes (Given/When/Then, RFC 2119) |
| [`openspec/changes/archive/`](openspec/changes/archive/) | Historia completa del ciclo SDD: propuesta, diseño, 64 tareas, verificación y cierre |
| [`docs/spikes/`](docs/spikes/) | Evidencia empírica: thought signatures, límites del free tier, manejo de input |
| [`idea.md`](idea.md) | La conversación original que dio origen al proyecto |

---

*Proyecto creado por Erick Flores Paz (ErickFP). Licencia: pendiente de definir.*
