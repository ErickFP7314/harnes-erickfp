"""tests/cli/test_chat.py -- comando `erickfp chat` (spec agent-loop, axioma
idea.md: 'la IA no actua sin consultar la raiz'). Fase 7, tarea 7.4.

Prueba la composicion del contexto de sistema (`core/Claude` + roles de
`core/agents/` + `Store.preamble()`) y que se antepone al primer turno
enviado al Provider. NO ejercita la I/O real de terminal -- eso queda para
el smoke E2E manual (Fase 11.3). `_MockStore` es un doble ad-hoc (duck
typing estructural, Decision 5 del design): satisface la forma de
`Store.preamble()` sin depender de `erickfp.memory` (Fase 9, aun no existe
en este lote).
"""

from __future__ import annotations

from pathlib import Path

from rich.panel import Panel
from typer.testing import CliRunner

import erickfp.cli as cli_module
from erickfp.api.types import Block, Entry, Message, Response
from erickfp.cli import app, build_system_context, run_chat_session
from erickfp.provider.base import ProviderError
from erickfp.tools.registry import ToolRegistry
from tests.support import MockProvider

runner = CliRunner()


class _MockStore:
    def preamble(self) -> str:
        return "PREAMBLE-DE-PRUEBA: el usuario prefiere Python."


class _RecordingStore:
    """Doble de prueba (Lote 5 harness-v0-2, spec memory-store delta,
    Requirement 'Resumen de fin de sesion'): solo satisface `.save(entry)`
    -- run_chat_session no necesita `.preamble()` para persistir el
    resumen, esa responsabilidad es de `build_system_context`."""

    def __init__(self) -> None:
        self.saved: list[Entry] = []

    def save(self, entry: Entry) -> None:
        self.saved.append(entry)


class _ProviderThatFailsOnSummary:
    """Provider de prueba: responde normalmente al/los turno(s) del REPL,
    pero falla con `ProviderError` en la llamada de sintesis del resumen de
    fin de sesion (la que ocurre DESPUES del ultimo turno real)."""

    def __init__(self, turn_response: Response) -> None:
        self._turn_response = turn_response
        self._used_turn = False
        self.sent_messages: list[list[Message]] = []

    def send(self, messages: list[Message], tools: list[object]) -> Response:
        self.sent_messages.append(messages)
        if not self._used_turn:
            self._used_turn = True
            return self._turn_response
        raise ProviderError("fallo definitivo simulado (sintesis de resumen)")

    def model(self) -> str:
        return "mock-model"

    def set_model(self, name: str) -> None:
        pass


class _DummyConsole:
    def __init__(self) -> None:
        self.printed: list[str] = []

    def print(self, *args: object, **kwargs: object) -> None:
        self.printed.append(" ".join(str(a) for a in args))


def _make_root(tmp_path: Path) -> Path:
    root = tmp_path / ".ErickFP"
    (root / "core" / "agents").mkdir(parents=True)
    (root / "core" / "Claude").write_text("AXIOMA: legibilidad ante todo.")
    (root / "core" / "agents" / "planner.md").write_text("Rol: Planner.")
    return root


def test_preamble_loaded_before_first_turn(tmp_path: Path) -> None:
    root = _make_root(tmp_path)

    context = build_system_context(root, _MockStore())

    assert "AXIOMA: legibilidad ante todo." in context
    assert "Rol: Planner." in context
    assert "PREAMBLE-DE-PRUEBA" in context

    provider = MockProvider(
        responses=[Response(content=[Block(type="text", text="hola")], stop_reason="end_turn")]
    )
    inputs = iter(["hola agente", "salir"])

    run_chat_session(
        provider=provider,
        tools=ToolRegistry(),
        console=_DummyConsole(),
        system_context=context,
        read_line=lambda prompt: next(inputs),
    )

    assert len(provider.sent_messages) == 1  # un solo turno antes de "salir"
    first_call_messages = provider.sent_messages[0]
    combined_text = " ".join(
        block.text for message in first_call_messages for block in message.content
    )
    assert "PREAMBLE-DE-PRUEBA" in combined_text
    assert "hola agente" in combined_text


def test_system_context_not_repeated_on_second_turn(tmp_path: Path) -> None:
    """El contexto de sistema se antepone SOLO al primer mensaje de usuario
    -- el mensaje NUEVO que agrega el segundo turno no lo vuelve a incluir
    (si reaparece en el historial completo es porque el primer mensaje sigue
    ahi, lo cual es correcto para una API stateless; lo que NO debe pasar es
    que se inyecte un bloque de contexto adicional en cada turno nuevo)."""
    root = _make_root(tmp_path)
    context = build_system_context(root, _MockStore())

    provider = MockProvider(
        responses=[
            Response(content=[Block(type="text", text="uno")], stop_reason="end_turn"),
            Response(content=[Block(type="text", text="dos")], stop_reason="end_turn"),
        ]
    )
    inputs = iter(["primer turno", "segundo turno", "salir"])

    run_chat_session(
        provider=provider,
        tools=ToolRegistry(),
        console=_DummyConsole(),
        system_context=context,
        read_line=lambda prompt: next(inputs),
    )

    assert len(provider.sent_messages) == 2
    newest_message = provider.sent_messages[1][-1]  # el mensaje agregado en este turno
    newest_text = " ".join(block.text for block in newest_message.content)
    assert "PREAMBLE-DE-PRUEBA" not in newest_text
    assert "segundo turno" in newest_text


def test_chat_startup_renders_banner_and_uses_decorated_input(
    tmp_path: Path, monkeypatch
) -> None:
    """Lote 1, tarea 1.14 (spec ui-polish): `erickfp chat` renderiza el
    banner de portada al arranque y pasa un `read_line` decorado (cuadro
    Rich + `agent.gate.read_line`, unico consumer real de stdin -- spike
    2.3) a `run_chat_session`, en vez del `gate_read_line` crudo."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    printed: list[object] = []

    def _fake_print(*args: object, **kwargs: object) -> None:
        printed.append(args[0] if args else None)

    monkeypatch.setattr(cli_module.console, "print", _fake_print)

    read_line_calls: list[str] = []
    monkeypatch.setattr(
        cli_module, "gate_read_line", lambda prompt: read_line_calls.append(prompt) or "salir"
    )

    captured: dict[str, object] = {}

    def fake_run_chat_session(
        provider, tools, console, system_context, read_line=None, hook_manager=None, store=None
    ):
        # `hook_manager` (Lote 4, spec permission-policy): `chat()` ahora
        # inyecta un HookManager real con CoreGuardHook -- el stub solo
        # necesita aceptar el kwarg, no lo ejercita en este test de UI.
        captured["read_line"] = read_line

    monkeypatch.setattr(cli_module, "run_chat_session", fake_run_chat_session)

    result = runner.invoke(app, ["chat"])

    assert result.exit_code == 0, result.output
    # El banner (Panel Rich) se renderiza al arranque, antes de entrar al REPL.
    assert any(isinstance(item, Panel) for item in printed)

    decorated_read_line = captured["read_line"]
    assert decorated_read_line is not None
    assert decorated_read_line is not cli_module.gate_read_line

    panels_before = sum(isinstance(item, Panel) for item in printed)
    result_text = decorated_read_line("tu> ")

    assert result_text == "salir"
    # `gate_read_line` sigue siendo el UNICO consumer real de stdin.
    assert read_line_calls == ["tu> "]
    # El cuadro del prompt (ui.input_frame.frame) se imprimio ademas del banner.
    panels_after = sum(isinstance(item, Panel) for item in printed)
    assert panels_after > panels_before


def test_chat_without_init_reports_clear_error(tmp_path: Path, monkeypatch) -> None:
    """Lote 2, tarea 2.13 (SUGGESTION-1 del verify-report de ciclo 1):
    `erickfp chat` sin `.ErickFP/` previo no crashea -- informa un error
    claro (mencionando `init`) y sale con `exit_code == 1`, sin llegar a
    renderizar el banner ni entrar al REPL."""
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["chat"])

    assert result.exit_code == 1
    assert "init" in result.output.lower()
    assert "Traceback" not in result.output


def test_run_chat_session_wires_core_guard_via_chat_command(
    tmp_path: Path, monkeypatch
) -> None:
    """Lote 4 harness-v0-2 (spec permission-policy, Requirement 'core_guard
    prevalece sobre cualquier policy'): antes de este lote, `chat()` no
    inyectaba ningun `hook_manager` en `run_chat_session` -- `core_guard`
    solo corria en las fases del Ciclo Cogito. Este test fija que `chat()`
    ahora construye un `HookManager([CoreGuardHook(root)])` real y lo pasa,
    de modo que una escritura en `.ErickFP/core/*` durante el REPL de chat
    se bloquea SIEMPRE, sin importar la policy (default `AlwaysAsk`)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    captured: dict[str, object] = {}

    def fake_run_chat_session(
        provider, tools, console, system_context, read_line=None, hook_manager=None, store=None
    ):
        captured["hook_manager"] = hook_manager

    monkeypatch.setattr(cli_module, "run_chat_session", fake_run_chat_session)

    result = runner.invoke(app, ["chat"])

    assert result.exit_code == 0, result.output
    assert captured["hook_manager"] is not None


def test_repl_handles_eof_gracefully(tmp_path: Path, monkeypatch) -> None:
    """Lote 2, tarea 2.13: un `EOFError` durante el REPL (p.ej. Ctrl+D o
    stdin cerrado) no crashea `chat` -- se captura, se imprime una
    despedida y el comando termina con `exit_code == 0`."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    def _raise_eof(*_args: object, **_kwargs: object) -> None:
        raise EOFError

    monkeypatch.setattr(cli_module, "run_chat_session", _raise_eof)

    result = runner.invoke(app, ["chat"])

    assert result.exit_code == 0, result.output
    assert "Hasta luego" in result.output
    assert "Traceback" not in result.output


def test_session_end_persists_summary_via_provider_synthesis() -> None:
    """Lote 5 harness-v0-2 (spec memory-store delta, Requirement 'Resumen de
    fin de sesion', Scenario 'Resumen persistido al salir'): con al menos un
    turno completado, al salir del REPL ('salir') el sistema pide una
    sintesis breve al Provider (una llamada `send` adicional DESPUES del
    ultimo turno real) y la persiste via `store.save(Entry(kind=
    'session-summary'))`."""
    store = _RecordingStore()
    turn_response = Response(content=[Block(type="text", text="hola")], stop_reason="end_turn")
    summary_response = Response(
        content=[Block(type="text", text="Resumen: el usuario saludo.")], stop_reason="end_turn"
    )
    provider = MockProvider(responses=[turn_response, summary_response])
    inputs = iter(["hola agente", "salir"])

    run_chat_session(
        provider=provider,
        tools=ToolRegistry(),
        console=_DummyConsole(),
        system_context="",
        read_line=lambda prompt: next(inputs),
        store=store,
    )

    assert len(provider.sent_messages) == 2  # 1 turno real + 1 sintesis de resumen
    assert len(store.saved) == 1
    assert store.saved[0].kind == "session-summary"
    assert "Resumen: el usuario saludo." in store.saved[0].content


def test_session_without_turns_skips_or_saves_empty_summary_safely() -> None:
    """Lote 5 harness-v0-2 (spec memory-store delta, Scenario 'Sesion sin
    turnos no genera resumen vacio innecesario'): salir INMEDIATAMENTE (sin
    ningun turno real) no invoca al Provider para sintetizar nada y no
    persiste ningun `Entry` -- ni falla."""
    store = _RecordingStore()
    provider = MockProvider(responses=[])
    inputs = iter(["salir"])

    run_chat_session(
        provider=provider,
        tools=ToolRegistry(),
        console=_DummyConsole(),
        system_context="",
        read_line=lambda prompt: next(inputs),
        store=store,
    )

    assert provider.sent_messages == []
    assert store.saved == []


def test_session_end_summary_provider_error_does_not_block_exit() -> None:
    """Lote 5 harness-v0-2 (design.md D9: 'try/except ProviderError -> si
    falla se omite sin crashear'): si la sintesis del resumen falla porque
    el Provider agoto sus reintentos, `run_chat_session` retorna igual
    (salir NUNCA se bloquea) -- no persiste ningun resumen, e informa el
    fallo por consola sin lanzar la excepcion hacia el llamador."""
    store = _RecordingStore()
    provider = _ProviderThatFailsOnSummary(
        Response(content=[Block(type="text", text="hola")], stop_reason="end_turn")
    )
    console = _DummyConsole()
    inputs = iter(["hola agente", "salir"])

    run_chat_session(
        provider=provider,
        tools=ToolRegistry(),
        console=console,
        system_context="",
        read_line=lambda prompt: next(inputs),
        store=store,
    )

    assert store.saved == []
    assert any("resumen" in printed.lower() for printed in console.printed)
