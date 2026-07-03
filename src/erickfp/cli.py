"""cli.py -- entrypoint Typer (glue arriba, Decision 1 del design: `cli.py`
depende de todo lo demas y NADA depende de `cli.py`).

Comandos del MVP: `init` (scaffolding de `.ErickFP/`, spec cli-init) y
`chat` (REPL agentico, spec agent-loop). Los comandos `duda`/`divide`/
`ordena`/`enumera` del Ciclo Cogito se cablean en Fase 10 (orquestador).
Este modulo es el UNICO lugar donde la logica se conecta con la interfaz de
usuario -- ningun otro modulo del paquete debe importar `typer`/`rich`.

Tema de color (preferencia del usuario): cyan primario (banner, prompts,
nombres de fase), verde acento (exitos/aprobaciones), rojo estandar para
errores. Se usan codigos truecolor explicitos para consistencia entre
terminales.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import typer
from rich.console import Console

from erickfp.agent.gate import read_line as gate_read_line
from erickfp.agent.loop import run_turn
from erickfp.api.types import Block, Message
from erickfp.memory.sqlite_store import SqliteStore
from erickfp.provider.base import Provider
from erickfp.provider.litellm_gemini import LiteLLMGeminiProvider
from erickfp.tools.registry import ToolRegistry
from erickfp.tools.registry import registry as tool_registry

app = typer.Typer(help="ErickFP -- harness agentico CLI con Ciclo Cogito.")

_CYAN = "#00FFFF"
_GREEN = "#00FF00"
_RED = "red"

console = Console(highlight=False)

_ROOT_DIR_NAME = ".ErickFP"
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_CORE_ROLE_FILES = ("planner.md", "coder.md", "reviewer.md")
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
        messages = [*messages, Message(role="user", content=content)]
        first_turn = False

        messages = run_turn(provider, tools, messages, tool_defs)

        last_message = messages[-1]
        for block in last_message.content:
            if block.type == "text" and block.text:
                console.print(f"[{_CYAN}]erickfp>[/{_CYAN}] {block.text}")


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

    console.print(f"[{_CYAN}]ErickFP chat -- Ctrl+D o 'salir' para terminar.[/{_CYAN}]")

    system_context = build_system_context(root, SqliteStore(root=root))
    provider = LiteLLMGeminiProvider()

    try:
        run_chat_session(provider, tool_registry, console, system_context)
    except EOFError:
        console.print(f"\n[{_CYAN}]Hasta luego.[/{_CYAN}]")
