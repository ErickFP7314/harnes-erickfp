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
from erickfp.api.types import Block, Message
from erickfp.cogito.artifacts import ArtifactMissingError
from erickfp.cogito.orchestrator import CicloCogitoOrchestrator, PhaseBlockedError, PhaseOutcome
from erickfp.hooks.adr_traceability import AdrTraceabilityHook
from erickfp.hooks.core_guard import CoreGuardHook
from erickfp.hooks.manager import HookManager, PhaseContext
from erickfp.memory.sqlite_store import SqliteStore
from erickfp.provider.base import Provider, ProviderError
from erickfp.provider.litellm_gemini import LiteLLMGeminiProvider
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


def run_chat_session(
    provider: Provider,
    tools: ToolRegistry,
    console: Console,
    system_context: str,
    read_line: Callable[[str], str] = gate_read_line,
) -> None:
    """Bucle REPL (spec agent-loop, Requirement 'Loop REPL con Provider'):
    un turno de texto plano por iteracion. El contexto de sistema se
    antepone SOLO en el primer turno -- no se re-inyecta en cada mensaje.
    Termina con "salir"/"exit"/"quit".
    """
    messages: list[Message] = []
    tool_defs = tools.definitions()
    first_turn = True

    while True:
        user_input = read_line("tu> ")
        if user_input.strip().lower() in _EXIT_COMMANDS:
            return

        content = [Block(type="text", text=system_context)] if first_turn else []
        content.append(Block(type="text", text=user_input))
        previous_messages = messages
        messages = [*messages, Message(role="user", content=content)]

        try:
            messages = run_turn(provider, tools, messages, tool_defs)
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

        first_turn = False

        last_message = messages[-1]
        for block in last_message.content:
            if block.type == "text" and block.text:
                console.print(f"[{_CYAN}]erickfp>[/{_CYAN}] {block.text}")


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
    console.print(f"[{_CYAN}]ErickFP chat -- Ctrl+D o 'salir' para terminar.[/{_CYAN}]")

    system_context = build_system_context(root, SqliteStore(root=root))
    provider = LiteLLMGeminiProvider()

    try:
        run_chat_session(
            provider, tool_registry, console, system_context, read_line=_decorated_read_line
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
    provider = LiteLLMGeminiProvider()
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
