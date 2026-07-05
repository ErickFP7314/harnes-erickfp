"""tests/cli/test_slash_commands.py -- comandos slash del REPL (`/help`,
`/tools`, `/clear`, `/model`, `/tokens`) y el token-viewer (specs
slash-commands + token-viewer, Lote 3 harness-v0-2, tareas 3.1-3.19).

Ejercita `run_chat_session` directamente (igual patron que
`tests/cli/test_chat.py`), con `MockProvider`/`ToolRegistry` reales y un
`_DummyConsole` que solo acumula lo impreso -- ninguna llamada real a la API
(GEMINI_API_KEY nunca se toca aqui).
"""

from __future__ import annotations

from erickfp.agent.tokens import TokenTracker
from erickfp.api.types import Block, Response, Usage
from erickfp.cli import run_chat_session
from erickfp.provider.litellm_gemini import DEFAULT_MODEL
from erickfp.tools.registry import ToolRegistry
from tests.support import FakeTool, MockProvider


class _DummyConsole:
    def __init__(self) -> None:
        self.printed: list[str] = []

    def print(self, *args: object, **kwargs: object) -> None:
        self.printed.append(" ".join(str(a) for a in args))

    def joined(self) -> str:
        return "\n".join(self.printed)


def _make_inputs(*turns: str):
    values = iter(turns)
    return lambda _prompt: next(values)


# -- Requirement: Comandos reconocidos /help /model /tools /clear -----------


def test_help_lists_available_commands() -> None:
    """Scenario '/help lista comandos'."""
    console = _DummyConsole()
    provider = MockProvider()

    run_chat_session(
        provider,
        ToolRegistry(),
        console,
        "",
        read_line=_make_inputs("/help", "salir"),
    )

    printed = console.joined()
    for name in ("/help", "/model", "/tools", "/clear", "/tokens"):
        assert name in printed
    assert provider.sent_messages == []  # /help nunca llega al Provider


def test_tools_lists_registry_in_stable_order() -> None:
    """Scenario '/tools lista tools registradas': orden estable del
    registry (orden de insercion), no alfabetico."""
    console = _DummyConsole()
    tools = ToolRegistry()
    tools.register(FakeTool(name="zeta"))
    tools.register(FakeTool(name="alpha"))
    provider = MockProvider()

    run_chat_session(
        provider,
        tools,
        console,
        "",
        read_line=_make_inputs("/tools", "salir"),
    )

    printed = console.joined()
    assert "zeta" in printed
    assert "alpha" in printed
    assert printed.index("zeta") < printed.index("alpha")


def test_clear_resets_history_and_reinjects_context() -> None:
    """Scenario '/clear limpia el historial': el siguiente turno real
    vuelve a anteponer el contexto raiz (design.md D4: `first_turn=True`),
    y el turno previo (anterior al `/clear`) no viaja en el historial."""
    console = _DummyConsole()
    provider = MockProvider(
        responses=[
            Response(content=[Block(type="text", text="r1")], stop_reason="end_turn"),
            Response(content=[Block(type="text", text="r2")], stop_reason="end_turn"),
        ]
    )

    run_chat_session(
        provider,
        ToolRegistry(),
        console,
        "CONTEXTO-RAIZ",
        read_line=_make_inputs("primer mensaje", "/clear", "segundo mensaje", "salir"),
    )

    assert len(provider.sent_messages) == 2  # /clear jamas llega al Provider
    first_call_text = " ".join(
        block.text for message in provider.sent_messages[0] for block in message.content
    )
    second_call_text = " ".join(
        block.text for message in provider.sent_messages[1] for block in message.content
    )
    assert "CONTEXTO-RAIZ" in first_call_text
    assert "CONTEXTO-RAIZ" in second_call_text  # re-inyectado tras /clear
    assert "primer mensaje" not in second_call_text  # historial vacio tras /clear


def test_model_shows_and_sets_active_model() -> None:
    """Requirement 'Comandos reconocidos...': `/model` muestra el modelo
    activo sin argumento, y lo cambia via `provider.set_model()` con uno."""
    console = _DummyConsole()
    provider = MockProvider(model_name="modelo-inicial")

    run_chat_session(
        provider,
        ToolRegistry(),
        console,
        "",
        read_line=_make_inputs("/model", "/model modelo-nuevo", "salir"),
    )

    printed = console.joined()
    assert "modelo-inicial" in printed
    assert provider.model() == "modelo-nuevo"
    assert "modelo-nuevo" in printed
    assert provider.sent_messages == []  # /model nunca llega al Provider


# -- Requirement: Entradas con "/" nunca se envian al modelo -----------------


def test_slash_input_never_reaches_provider() -> None:
    """Scenario 'Comando valido interceptado' (GIVEN `/model`)."""
    provider = MockProvider()

    run_chat_session(
        provider,
        ToolRegistry(),
        _DummyConsole(),
        "",
        read_line=_make_inputs("/model", "salir"),
    )

    assert provider.sent_messages == []


def test_unknown_slash_command_reports_local_error() -> None:
    """Scenario 'Comando desconocido': `/foo` reporta un error LOCAL, sin
    tocar el Provider."""
    console = _DummyConsole()
    provider = MockProvider()

    run_chat_session(
        provider,
        ToolRegistry(),
        console,
        "",
        read_line=_make_inputs("/foo", "salir"),
    )

    assert provider.sent_messages == []
    assert "desconocido" in console.joined().lower()
    assert "/foo" in console.joined()


# -- Requirement: /tokens reporta uso y costo por sesion ---------------------


def test_tokens_reports_usage_and_cost_known_pricing() -> None:
    """Scenario 'Reporte con modelo de pricing conocido': tokens de entrada
    y salida mas un costo numerico real (no '—/gratis' ni 'desconocido')."""
    console = _DummyConsole()
    tracker = TokenTracker()
    provider = MockProvider(
        responses=[
            Response(
                content=[Block(type="text", text="ok")],
                stop_reason="end_turn",
                usage=Usage(prompt=1000, completion=500, total=1500),
            )
        ],
        model_name="gemini/gemini-3.5-flash",
    )

    run_chat_session(
        provider,
        ToolRegistry(),
        console,
        "",
        read_line=_make_inputs("hola", "/tokens", "salir"),
        tracker=tracker,
    )

    printed = console.joined()
    assert "1000" in printed
    assert "500" in printed
    assert "1500" in printed
    assert "$" in printed
    assert "desconocido" not in printed.lower()
    assert "gratis" not in printed.lower()


def test_tokens_unknown_pricing_reports_unknown_cost() -> None:
    """Scenario 'Modelo sin pricing conocido': tokens acumulados
    normalmente, costo '"desconocido/0"', sin error."""
    console = _DummyConsole()
    tracker = TokenTracker()
    provider = MockProvider(
        responses=[
            Response(
                content=[Block(type="text", text="ok")],
                stop_reason="end_turn",
                usage=Usage(prompt=10, completion=5, total=15),
            )
        ],
        model_name="proveedor/modelo-sin-pricing-registrado",
    )

    run_chat_session(
        provider,
        ToolRegistry(),
        console,
        "",
        read_line=_make_inputs("hola", "/tokens", "salir"),
        tracker=tracker,
    )

    printed = console.joined()
    assert "10" in printed
    assert "5" in printed
    assert "15" in printed
    assert "desconocido/0" in printed


def test_tokens_before_first_turn_reports_zero() -> None:
    """Scenario '/tokens antes del primer turno': 0 tokens, costo 0, sin
    error (modelo default de Gemma free-tier -> '—/gratis', design.md D6)."""
    console = _DummyConsole()
    tracker = TokenTracker()
    provider = MockProvider(model_name=DEFAULT_MODEL)

    run_chat_session(
        provider,
        ToolRegistry(),
        console,
        "",
        read_line=_make_inputs("/tokens", "salir"),
        tracker=tracker,
    )

    printed = console.joined()
    assert "entrada=0" in printed
    assert "salida=0" in printed
    assert "total=0" in printed
    assert "gratis" in printed.lower()
    assert provider.sent_messages == []
