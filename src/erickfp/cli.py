"""cli.py -- entrypoint Typer (glue arriba, Decision 1 del design: `cli.py`
depende de todo lo demas y NADA depende de `cli.py`).

Comandos del MVP: `init` (scaffolding de `.ErickFP/`, spec cli-init), `chat`
(REPL agentico, spec agent-loop) y `duda`/`divide`/`ordena`/`enumera` (Ciclo
Cogito, spec ciclo-cogito, Fase 10) -- estos ultimos reutilizan
`CicloCogitoOrchestrator`. Este modulo es el UNICO lugar donde la logica se
conecta con la interfaz de usuario -- ningun otro modulo del paquete debe
importar `typer`/`rich`.

Tema de color (preferencia del usuario): cyan primario (banner, prompts,
nombres de fase), verde acento (exitos/aprobaciones), rojo estandar para
errores. Se usan codigos truecolor explicitos para consistencia entre
terminales.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import typer
from rich.console import Console

from erickfp.agent.gate import read_line as gate_read_line
from erickfp.agent.loop import run_turn
from erickfp.agent.policy import PermissionPolicy
from erickfp.agent.tokens import TokenTracker
from erickfp.api.types import Block, Entry, Message, ToolDef
from erickfp.cogito.artifacts import ArtifactMissingError
from erickfp.cogito.orchestrator import CicloCogitoOrchestrator, PhaseBlockedError, PhaseOutcome
from erickfp.hooks.adr_traceability import AdrTraceabilityHook
from erickfp.hooks.core_guard import CoreGuardHook
from erickfp.hooks.manager import HookManager, PhaseContext
from erickfp.memory.sqlite_store import SqliteStore
from erickfp.provider.base import Provider, ProviderError
from erickfp.provider.litellm_gemini import DEFAULT_MODEL, LiteLLMGeminiProvider
from erickfp.subagents.delegate import DelegateTool
from erickfp.subagents.research import Research
from erickfp.tools.recall import RecallTool
from erickfp.tools.registry import ToolRegistry
from erickfp.tools.registry import registry as tool_registry
from erickfp.ui.banner import render_banner
from erickfp.ui.input_frame import frame

app = typer.Typer(help="ErickFP -- harness agentico CLI con Ciclo Cogito.")

_CYAN = "#00FFFF"
_GREEN = "#00FF00"
_RED = "red"

console = Console(highlight=False)

_ROOT_DIR_NAME = ".ErickFP"
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_CORE_ROLE_FILES = ("planner.md", "coder.md", "reviewer.md")
_CORE_AGENT_ROLES = ("planner", "coder", "reviewer")
_EXIT_COMMANDS = {"salir", "exit", "quit"}

# Retry configurable del Provider (Lote 2, tarea 2.6, design.md Decision 10):
# la composition root (`cli.py`) es quien decide `max_attempts`/
# `backoff_seconds` -- el adapter solo expone el seam. Los valores
# preservan bit-a-bit el default del ciclo 1 (2 intentos, 2s de backoff);
# ajustarlos aqui no requiere tocar `provider/litellm_gemini.py`.
_PROVIDER_MAX_ATTEMPTS = 2
_PROVIDER_BACKOFF_SECONDS = 2.0


def _build_provider() -> LiteLLMGeminiProvider:
    return LiteLLMGeminiProvider(
        max_attempts=_PROVIDER_MAX_ATTEMPTS,
        backoff_seconds=_PROVIDER_BACKOFF_SECONDS,
    )


# -- init -----------------------------------------------------------------


def _write_if_absent_or_confirmed(path: Path, content: str, *, protect: bool) -> str:
    """Escribe `content` en `path` y retorna el estado resultante para el
    reporte final: 'creado', 'existente' o 'sobrescrito'.

    Si `protect` es True y `path` ya existe, pide confirmacion explicita
    antes de sobrescribir (spec cli-init: re-init NO sobrescribe
    `core/Claude` ni `core/agents` sin confirmacion explicita del humano).
    """
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return "creado"

    if not protect:
        return "existente"

    overwrite = typer.confirm(
        f"{path} ya existe. Sobrescribir con la plantilla base?", default=False
    )
    if overwrite:
        path.write_text(content)
        return "sobrescrito"
    return "existente"


@app.command()
def init() -> None:
    """Crea (o repara) el arbol `.ErickFP/` (spec cli-init: Scaffolding)."""
    root = Path.cwd() / _ROOT_DIR_NAME
    report: dict[Path, str] = {}

    claude_path = root / "core" / "Claude"
    report[claude_path] = _write_if_absent_or_confirmed(
        claude_path, (_TEMPLATES_DIR / "core_claude.md").read_text(), protect=True
    )

    for role_file in _CORE_ROLE_FILES:
        role_path = root / "core" / "agents" / role_file
        report[role_path] = _write_if_absent_or_confirmed(
            role_path, (_TEMPLATES_DIR / "agents" / role_file).read_text(), protect=True
        )

    adr_readme = root / "adr" / "README.md"
    report[adr_readme] = _write_if_absent_or_confirmed(
        adr_readme, (_TEMPLATES_DIR / "adr_readme.md").read_text(), protect=False
    )

    for extra_dir in ("memory", "hooks"):
        (root / extra_dir).mkdir(parents=True, exist_ok=True)

    for path, status in report.items():
        color = _GREEN if status == "creado" else _CYAN
        console.print(f"[{color}]{status}[/{color}] {path}")


# -- chat -------------------------------------------------------------------


class PreambleSource(Protocol):
    """Forma estructural minima que `chat` necesita del Memory Store
    (Decision 5 del design: `Store.preamble() -> str`). Se define aqui, en
    lugar de importar `erickfp.memory.store.Store` directamente, para que
    `build_system_context` acepte cualquier objeto con `.preamble() -> str`
    (duck typing estructural) -- hoy lo satisface `SqliteStore` (Fase 9), y
    en tests lo satisfacen dobles ad-hoc sin depender de `erickfp.memory`.
    """

    def preamble(self) -> str: ...


class SessionSummaryStore(Protocol):
    """Forma estructural minima que `run_chat_session` necesita para
    persistir el resumen de fin de sesion (Lote 5 harness-v0-2, spec
    memory-store delta, Requirement 'Resumen de fin de sesion', design.md
    D9): mismo patron de duck typing que `PreambleSource` -- se define
    aqui, no se importa `erickfp.memory.store.Store`, para que un doble de
    prueba ad-hoc (o cualquier otro objeto con `.save(entry)`) la
    satisfaga sin depender de `erickfp.memory`. Hoy la satisface
    `SqliteStore`."""

    def save(self, entry: Entry) -> None: ...


# Resumen de fin de sesion (Lote 5, spec memory-store delta, design.md D9):
# instruccion de sintesis enviada al Provider como un turno adicional, SOLO
# al salir del REPL y SOLO si hubo al menos un turno real (Scenario 'Sesion
# sin turnos no genera resumen vacio innecesario').
_SESSION_SUMMARY_PROMPT = (
    "Resume esta sesion de chat en 2-3 frases breves, en tercera persona, "
    "para que quede como contexto util al iniciar la proxima sesion."
)


def _persist_session_summary(
    provider: Provider,
    console: Console,
    store: SessionSummaryStore | None,
    messages: list[Message],
) -> None:
    """Al salir de `run_chat_session` (spec memory-store delta, Requirement
    'Resumen de fin de sesion'): si hubo al menos un turno completado, pide
    al Provider una sintesis breve (`provider.send`, un turno adicional) y
    la persiste como `Entry(kind="session-summary")`. Un `ProviderError`
    (el Provider agoto sus reintentos) NUNCA bloquea la salida -- se
    informa por consola y se omite el resumen, sin relanzar la excepcion
    (mismo axioma que el resto del REPL: fallar limpio, jamas crashear).
    Sesion vacia (`messages == []`) u objeto `store` ausente: no-op.
    """
    if store is None or not messages:
        return

    summary_request = [
        *messages,
        Message(role="user", content=[Block(type="text", text=_SESSION_SUMMARY_PROMPT)]),
    ]
    try:
        response = provider.send(summary_request, [])
    except ProviderError as exc:
        console.print(
            f"[{_RED}]No se pudo generar el resumen de la sesion "
            f"(el proveedor fallo tras los reintentos): {exc}[/{_RED}]"
        )
        return

    summary_text = " ".join(
        block.text for block in response.content if block.type == "text" and block.text
    ).strip()
    if not summary_text:
        return
    store.save(Entry(kind="session-summary", content=summary_text))


def _read_or_empty(path: Path) -> str:
    return path.read_text() if path.is_file() else ""


def _load_role_files(agents_dir: Path) -> str:
    if not agents_dir.is_dir():
        return ""
    parts = [p.read_text() for p in sorted(agents_dir.glob("*.md")) if p.is_file()]
    return "\n\n".join(parts)


def build_system_context(root: Path, store: PreambleSource) -> str:
    """Compone el contexto de sistema del chat (axioma de idea.md: 'la IA no
    actua sin consultar la raiz'): `core/Claude` + roles de `core/agents/` +
    preamble del Store. Se antepone SOLO al primer turno del usuario.

    Nunca lanza si algun archivo aun no existe (falla a texto vacio, no a
    excepcion, para no bloquear `chat` en un repo sin `init` previo --
    aunque se recomienda correr `init` primero).
    """
    claude_text = _read_or_empty(root / "core" / "Claude")
    agents_text = _load_role_files(root / "core" / "agents")
    preamble = store.preamble()
    sections = [section for section in (claude_text, agents_text, preamble) if section]
    return "\n\n---\n\n".join(sections)


# -- Slash commands (Lote 3, tareas 3.1-3.11, design.md Decision D4) --------
#
# Mini-registry `dict[str, handler]` (SlashRegistry): entradas que empiecen
# con "/" NUNCA llegan al Provider -- se interceptan al inicio del loop REPL
# y se resuelven localmente (`handler(...)` + `continue`), comando conocido
# o no. `_SLASH_HELP` documenta cada comando para `/help`; el nombre (sin la
# barra) es la clave tanto de `_SLASH_HELP` como del registry que arma
# `_build_slash_registry` (necesita closures sobre el estado del loop, por
# eso se construye DENTRO de `run_chat_session`, no a nivel de modulo).
_SLASH_HELP: dict[str, str] = {
    "help": "lista los comandos disponibles",
    "model": "muestra el modelo activo, o lo cambia con /model <nombre>",
    "tools": "lista las tools registradas (orden estable del registry)",
    "clear": "vacia el historial de la sesion en curso",
    "tokens": "muestra tokens acumulados y costo estimado de la sesion",
}

# -- Token viewer (Lote 3, tareas 3.16-3.19, design.md Decision D6) ---------
#
# Tabla de pricing USD por 1000 tokens. `DEFAULT_MODEL` (Gemma free tier) se
# reporta como "gratis" en vez de un numero -- no tiene costo real que
# calcular. Un modelo ausente de esta tabla reporta "desconocido/0" (nunca
# un error): el pricing de modelos de terceros no siempre esta disponible.
_FREE_TIER_MODELS = {DEFAULT_MODEL}
_MODEL_PRICING_USD_PER_1K: dict[str, tuple[float, float]] = {
    # Ejemplo de modelo con pricing real y no-gratis (referenciado ya en el
    # docstring de litellm_gemini.py como alternativa a Gemma 4), para que
    # el calculo de costo tenga un caso numerico ejercitado de verdad.
    "gemini/gemini-3.5-flash": (0.0005, 0.0015),
}


def _format_cost(model_name: str, tracker: TokenTracker) -> str:
    """Traduce el estado de `tracker` + el modelo activo a un string de
    costo (spec token-viewer, Requirement '/tokens reporta uso y costo').
    """
    if model_name in _FREE_TIER_MODELS:
        return "—/gratis"
    pricing = _MODEL_PRICING_USD_PER_1K.get(model_name)
    if pricing is None:
        return "desconocido/0"
    prompt_price, completion_price = pricing
    cost = (tracker.prompt_tokens / 1000) * prompt_price + (
        tracker.completion_tokens / 1000
    ) * completion_price
    return f"${cost:.6f}"


class _ReplState:
    """Estado mutable del loop REPL (historial + bandera de primer turno).
    Objeto simple (no dataclass) para que `/clear` (design.md D4) pueda
    reasignar sus atributos desde una closure sin depender de `nonlocal`
    sobre variables de `run_chat_session` -- las mismas instancia se
    comparte entre el loop y el SlashRegistry."""

    def __init__(self) -> None:
        self.messages: list[Message] = []
        self.first_turn: bool = True


def _build_slash_registry(
    provider: Provider,
    tools: ToolRegistry,
    tool_defs: list[ToolDef],
    console: Console,
    tracker: TokenTracker,
    state: _ReplState,
) -> dict[str, Callable[[str], None]]:
    """Arma el SlashRegistry (design.md D4) con closures sobre el estado
    mutable del loop REPL (`state.messages`/`state.first_turn`) -- se
    reconstruye por sesion dentro de `run_chat_session`, no a nivel de
    modulo, porque cada sesion tiene su propio historial."""

    def _handle_help(_argument: str) -> None:
        lines = [f"/{name} -- {desc}" for name, desc in _SLASH_HELP.items()]
        console.print(f"[{_CYAN}]Comandos disponibles:[/{_CYAN}]\n" + "\n".join(lines))

    def _handle_tools(_argument: str) -> None:
        names = ", ".join(tool_def.name for tool_def in tool_defs)
        console.print(f"[{_CYAN}]tools registradas:[/{_CYAN}] {names}")

    def _handle_clear(_argument: str) -> None:
        state.messages = []
        state.first_turn = True
        console.print(f"[{_GREEN}]Historial de la sesion limpiado.[/{_GREEN}]")

    def _handle_model(argument: str) -> None:
        if argument:
            provider.set_model(argument)
            console.print(f"[{_GREEN}]Modelo activo: {provider.model()}[/{_GREEN}]")
        else:
            console.print(f"[{_CYAN}]Modelo activo: {provider.model()}[/{_CYAN}]")

    def _handle_tokens(_argument: str) -> None:
        cost = _format_cost(provider.model(), tracker)
        console.print(
            f"[{_CYAN}]tokens[/{_CYAN}] entrada={tracker.prompt_tokens} "
            f"salida={tracker.completion_tokens} total={tracker.total_tokens} "
            f"costo={cost}"
        )

    return {
        "help": _handle_help,
        "tools": _handle_tools,
        "clear": _handle_clear,
        "model": _handle_model,
        "tokens": _handle_tokens,
    }


def run_chat_session(
    provider: Provider,
    tools: ToolRegistry,
    console: Console,
    system_context: str,
    read_line: Callable[[str], str] = gate_read_line,
    tracker: TokenTracker | None = None,
    hook_manager: HookManager | None = None,
    policy: PermissionPolicy | None = None,
    store: SessionSummaryStore | None = None,
) -> None:
    """Bucle REPL (spec agent-loop, Requirement 'Loop REPL con Provider'):
    un turno de texto plano por iteracion. El contexto de sistema se
    antepone SOLO en el primer turno -- no se re-inyecta en cada mensaje.
    Termina con "salir"/"exit"/"quit".

    Comandos slash (spec slash-commands, design.md Decision D4): cualquier
    entrada que empiece con "/" se intercepta ANTES de tocar el Provider --
    comando conocido o no (Requirement 'Entradas con "/" nunca se envian al
    modelo'). `/clear` reinyecta el contexto raiz en el turno siguiente
    (`state.first_turn = True`).

    `hook_manager`/`policy` (Lote 4 harness-v0-2, spec permission-policy)
    son OPCIONALES (default `None`, mismo patron que `tracker`): `chat()`
    (composition root) inyecta un `HookManager([CoreGuardHook(root)])` real
    para que `core_guard` este SIEMPRE activo tambien en el REPL de chat, no
    solo en las fases del Ciclo Cogito -- `policy=None` preserva el
    comportamiento identico al ciclo 1 (`AlwaysAsk` implicito en el gate).

    `store` (Lote 5 harness-v0-2, spec memory-store delta, design.md D9) es
    OPCIONAL (default `None`, mismo patron que `tracker`/`hook_manager`):
    si se inyecta, AL SALIR del REPL -- por comando ("salir"/"exit"/"quit")
    o por `EOFError` propagado (Ctrl+D) -- se persiste un resumen de la
    sesion via `_persist_session_summary`. El `try/finally` que envuelve el
    loop garantiza que esto ocurra en AMBAS rutas de salida sin duplicar
    logica: un `return` normal ejecuta el `finally` antes de retornar, y una
    excepcion que se propaga (`EOFError`) tambien lo ejecuta antes de seguir
    subiendo hacia `chat()`.
    """
    tool_defs = tools.definitions()
    active_tracker = tracker if tracker is not None else TokenTracker()
    state = _ReplState()
    slash_registry = _build_slash_registry(
        provider, tools, tool_defs, console, active_tracker, state
    )
    ctx = PhaseContext(phase="chat") if hook_manager is not None else None

    try:
        while True:
            user_input = read_line("tu> ")
            if user_input.strip().lower() in _EXIT_COMMANDS:
                return

            if user_input.startswith("/"):
                command, _, argument = user_input[1:].partition(" ")
                handler = slash_registry.get(command.strip().lower())
                if handler is None:
                    console.print(
                        f"[{_RED}]Comando desconocido: /{command}. "
                        f"Usa /help para ver los comandos disponibles.[/{_RED}]"
                    )
                else:
                    handler(argument.strip())
                continue

            messages = state.messages
            first_turn = state.first_turn
            content = [Block(type="text", text=system_context)] if first_turn else []
            content.append(Block(type="text", text=user_input))
            previous_messages = messages
            messages = [*messages, Message(role="user", content=content)]

            try:
                messages = run_turn(
                    provider,
                    tools,
                    messages,
                    tool_defs,
                    hook_manager=hook_manager,
                    ctx=ctx,
                    tracker=active_tracker,
                    policy=policy,
                )
            except ProviderError as exc:
                # Hotfix 2026-07-04: un fallo definitivo del proveedor (p. ej.
                # 500 persistente tras agotar el retry) NO mata el REPL. Se
                # informa, se revierte el turno fallido (para no dejar un mensaje
                # de usuario huerfano ni perder el contexto raiz del primer
                # turno) y se espera el siguiente prompt.
                console.print(
                    f"[{_RED}]El proveedor fallo tras los reintentos: {exc}[/{_RED}]\n"
                    f"[{_RED}]Suele ser inestabilidad temporal del modelo -- "
                    f"espera unos segundos y vuelve a intentarlo.[/{_RED}]"
                )
                messages = previous_messages
                continue

            state.messages = messages
            state.first_turn = False

            last_message = messages[-1]
            for block in last_message.content:
                if block.type == "text" and block.text:
                    console.print(f"[{_CYAN}]erickfp>[/{_CYAN}] {block.text}")
    finally:
        _persist_session_summary(provider, console, store, state.messages)


def _decorated_read_line(prompt: str) -> str:
    """Compone el input decorado (Lote 1, tarea 1.14, spec ui-polish,
    Requirement 'Input decorado en cuadro'): imprime el cuadro Rich de
    `ui.input_frame.frame(prompt)` con la paleta del tema y DESPUES lee la
    linea real con `agent.gate.read_line` -- el UNICO consumer de stdin
    (spike 2.3) no cambia, solo se decora visualmente lo que lo precede."""
    console.print(frame(prompt))
    return gate_read_line(prompt)


@app.command()
def chat() -> None:
    """REPL agentico (spec agent-loop): conecta al Provider LiteLLM/Gemini,
    ejecuta tools SOLO bajo el permission gate."""
    root = Path.cwd() / _ROOT_DIR_NAME
    if not root.is_dir():
        console.print(
            f"[{_RED}]No se encontro {root}. Corre 'erickfp init' primero.[/{_RED}]"
        )
        raise typer.Exit(code=1)

    render_banner(console)
    console.print(
        f"[{_CYAN}]ErickFP chat -- Ctrl+D o 'salir' para terminar. "
        f"Escribe /help para ver los comandos disponibles.[/{_CYAN}]"
    )

    store = SqliteStore(root=root)
    system_context = build_system_context(root, store)
    provider = _build_provider()
    # core_guard SIEMPRE activo (Lote 4, spec permission-policy, Requirement
    # 'core_guard prevalece sobre cualquier policy'): tambien en el REPL de
    # chat, no solo en las fases del Ciclo Cogito (`_build_orchestrator`).
    hook_manager = HookManager([CoreGuardHook(root)])
    # RecallTool (Lote 5, spec memory-store delta, design.md D9): se
    # instancia con el `store` real EN el composition root -- `tools/`
    # nunca importa `memory/` (capas hermanas). Registrar en el `registry`
    # compartido del proceso hace que `recall` este disponible como
    # cualquier otra tool, pasando por el mismo gate/policy.
    tool_registry.register(RecallTool(store))
    # DelegateTool (Lote 7, spec subagents, design.md "Ciclo delegate"): el
    # `Research` interno reutiliza el MISMO `provider`/`hook_manager` que el
    # agente principal -- `core_guard` sigue activo dentro del subagente
    # (Requirement 'core_guard sigue activo dentro del subagente'). Se
    # registra en `tools/` -- que nunca importa `agent`/`subagents` -- solo
    # AQUI, en el composition root, igual que `RecallTool`/`MCPTool`.
    tool_registry.register(DelegateTool(Research(provider, hook_manager=hook_manager)))

    try:
        run_chat_session(
            provider,
            tool_registry,
            console,
            system_context,
            read_line=_decorated_read_line,
            hook_manager=hook_manager,
            store=store,
        )
    except EOFError:
        console.print(f"\n[{_CYAN}]Hasta luego.[/{_CYAN}]")


# -- Ciclo Cogito (duda/divide/ordena/enumera) -------------------------------


def _slugify(text: str) -> str:
    """Convierte `text` en un slug ascii-kebab-case (decision registrada en
    Lote 3/tarea 7.5, implementada aqui en la Fase 10: `cogito/` no puede
    importar `cli.py` por la regla de dependencia -- Decision 1 -- y esta
    funcion es exclusiva de la interfaz de usuario)."""
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower()
    return slug or "objetivo"


def _load_role_prompt(root: Path, role: str) -> str:
    """Contexto de sistema de UN solo rol (a diferencia de
    `build_system_context`, que concatena los 3 roles para `chat`): axiomas
    de `core/Claude` + el archivo especifico de `core/agents/{role}.md`
    (Decision 4 del design: duda/divide -> Planner, ordena -> Coder,
    enumera -> Reviewer)."""
    claude_text = _read_or_empty(root / "core" / "Claude")
    role_text = _read_or_empty(root / "core" / "agents" / f"{role}.md")
    return "\n\n---\n\n".join(part for part in (claude_text, role_text) if part)


def _build_orchestrator(root: Path) -> CicloCogitoOrchestrator:
    role_prompts = {role: _load_role_prompt(root, role) for role in _CORE_AGENT_ROLES}
    hook_manager = HookManager([CoreGuardHook(root), AdrTraceabilityHook(root)])
    provider = _build_provider()
    store = SqliteStore(root=root)
    return CicloCogitoOrchestrator(
        root=root,
        provider=provider,
        tools=tool_registry,
        hook_manager=hook_manager,
        role_prompts=role_prompts,
        store=store,
    )


def _require_root() -> Path:
    root = Path.cwd() / _ROOT_DIR_NAME
    if not root.is_dir():
        console.print(f"[{_RED}]No se encontro {root}. Corre 'erickfp init' primero.[/{_RED}]")
        raise typer.Exit(code=1)
    return root


def _print_outcome(outcome: PhaseOutcome) -> None:
    if outcome.status == "clarification":
        console.print(
            f"[{_RED}]{outcome.phase}[/{_RED}] pide clarificacion, no genero artefacto:\n"
            f"{outcome.content}"
        )
    else:
        console.print(f"[{_GREEN}]{outcome.phase}[/{_GREEN}] artefacto generado en {outcome.path}")


@app.command()
def duda(objetivo: str) -> None:
    """Fase 'duda' (Evidencia, spec ciclo-cogito): somete `objetivo` a duda
    metodica. Si es ambiguo, pide clarificacion en vez de generar artefacto."""
    root = _require_root()
    slug = _slugify(objetivo)
    orchestrator = _build_orchestrator(root)

    try:
        outcome = orchestrator.run_phase(
            "duda", slug, PhaseContext(phase="duda"), objetivo=objetivo
        )
    except PhaseBlockedError as exc:
        console.print(f"[{_RED}]{exc}[/{_RED}]")
        raise typer.Exit(code=1) from exc
    except ProviderError as exc:
        console.print(f"[{_RED}]El proveedor fallo tras los reintentos: {exc}[/{_RED}]")
        raise typer.Exit(code=1) from exc

    _print_outcome(outcome)
    console.print(f"[{_CYAN}]slug: {slug}[/{_CYAN}]")


def _run_single_phase_command(phase: str, slug: str) -> None:
    """Cablea `divide`/`ordena`/`enumera`: cada una exige el artefacto de la
    fase previa (Requirement 'Fases secuenciales bloqueantes', spec
    ciclo-cogito) y falla limpiamente -- sin crashear -- si falta."""
    root = _require_root()
    orchestrator = _build_orchestrator(root)

    try:
        outcome = orchestrator.run_phase(phase, slug, PhaseContext(phase=phase))
    except ArtifactMissingError as exc:
        console.print(f"[{_RED}]{exc}[/{_RED}]")
        raise typer.Exit(code=1) from exc
    except PhaseBlockedError as exc:
        console.print(f"[{_RED}]{exc}[/{_RED}]")
        raise typer.Exit(code=1) from exc
    except ProviderError as exc:
        console.print(f"[{_RED}]El proveedor fallo tras los reintentos: {exc}[/{_RED}]")
        raise typer.Exit(code=1) from exc

    _print_outcome(outcome)


@app.command()
def divide(slug: str) -> None:
    """Fase 'divide' (Analisis, spec ciclo-cogito): descompone el objetivo
    validado por `duda` en sus partes minimas."""
    _run_single_phase_command("divide", slug)


@app.command()
def ordena(slug: str) -> None:
    """Fase 'ordena' (Sintesis, spec ciclo-cogito): sintetiza segun el plan
    de `divide`, trazable a un ADR raiz (`adr_traceability`)."""
    _run_single_phase_command("ordena", slug)


@app.command()
def enumera(slug: str) -> None:
    """Fase 'enumera' (Revision, spec ciclo-cogito): revisa y enumera los
    resultados de `ordena`."""
    _run_single_phase_command("enumera", slug)
