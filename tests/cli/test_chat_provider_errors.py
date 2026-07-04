"""tests/cli/test_chat_provider_errors.py -- la CLI sobrevive a fallos del
proveedor (hotfix post-MVP, 2026-07-04).

Bug real reportado por el usuario: un `500 INTERNAL` persistente de Gemma 4
(tras agotar el retry acotado de la tarea 11.5) subia como traceback crudo y
mataba el REPL de `erickfp chat`. Las specs exigen fallas limpias: el
adapter lanza `ProviderError` (dominio) al agotar reintentos, `chat` la
captura, informa en rojo y el REPL continua; los comandos del Ciclo Cogito
salen con exit 1 y mensaje claro, sin traceback.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

import erickfp.cli as cli_module
from erickfp.api.types import Block, Message, Response, ToolDef
from erickfp.cli import app, run_chat_session
from erickfp.provider.base import ProviderError
from erickfp.tools.registry import ToolRegistry


class _DummyConsole:
    def __init__(self) -> None:
        self.printed: list[str] = []

    def print(self, *args: object, **kwargs: object) -> None:
        self.printed.append(" ".join(str(a) for a in args))


class _FlakyProvider:
    """Falla con ProviderError en la primera llamada, responde en la segunda."""

    def __init__(self) -> None:
        self.sent_messages: list[list[Message]] = []
        self._calls = 0

    def send(self, messages: list[Message], tools: list[ToolDef]) -> Response:
        self._calls += 1
        if self._calls == 1:
            raise ProviderError("GeminiException InternalServerError - 500 INTERNAL")
        self.sent_messages.append(list(messages))
        return Response(content=[Block(type="text", text="recuperado")], stop_reason="end_turn")

    def model(self) -> str:
        return "fake"

    def set_model(self, name: str) -> None: ...


def test_chat_survives_provider_error_and_keeps_repl_alive() -> None:
    provider = _FlakyProvider()
    console = _DummyConsole()
    inputs = iter(["hola", "otra vez", "salir"])

    # No debe lanzar: el error del proveedor se informa y el REPL continua.
    run_chat_session(
        provider=provider,
        tools=ToolRegistry(),
        console=console,
        system_context="CONTEXTO-RAIZ",
        read_line=lambda prompt: next(inputs),
    )

    error_lines = [line for line in console.printed if "500 INTERNAL" in line]
    assert error_lines, "el fallo del proveedor debe informarse al usuario"
    assert len(provider.sent_messages) == 1  # solo el turno exitoso llego a registrarse


def test_chat_rolls_back_failed_turn_so_context_is_not_lost() -> None:
    """El turno fallido se revierte: el mensaje del usuario no queda huerfano
    en el historial, y el contexto de sistema (que solo se antepone al primer
    turno) NO se pierde por un fallo en ese primer intento."""
    provider = _FlakyProvider()
    inputs = iter(["hola", "otra vez", "salir"])

    run_chat_session(
        provider=provider,
        tools=ToolRegistry(),
        console=_DummyConsole(),
        system_context="CONTEXTO-RAIZ",
        read_line=lambda prompt: next(inputs),
    )

    successful_request = provider.sent_messages[0]
    combined_text = " ".join(
        block.text for message in successful_request for block in message.content
    )
    assert "CONTEXTO-RAIZ" in combined_text  # el contexto raiz sobrevivio al fallo
    assert "otra vez" in combined_text
    assert "hola" not in combined_text  # el turno fallido no dejo residuo


class _BrokenOrchestrator:
    def run_phase(self, *args: object, **kwargs: object) -> object:
        raise ProviderError("GeminiException InternalServerError - 500 INTERNAL")


def test_duda_exits_cleanly_on_provider_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".ErickFP" / "core").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli_module, "_build_orchestrator", lambda root: _BrokenOrchestrator())

    result = CliRunner().invoke(app, ["duda", "un objetivo claro"])

    assert result.exit_code == 1
    assert "500 INTERNAL" in result.output
    assert "Traceback" not in result.output


def test_build_provider_passes_configurable_retry_to_constructor() -> None:
    """Lote 2, tarea 2.6 (design.md Decision 10): la composition root
    (`cli.py::_build_provider`) es quien fija `max_attempts`/
    `backoff_seconds` del adapter -- no quedan hardcodeados dentro de
    `provider/litellm_gemini.py`. Los valores preservan el default del
    ciclo 1 (2 intentos, 2.0s de backoff)."""
    provider = cli_module._build_provider()

    assert provider._max_attempts == cli_module._PROVIDER_MAX_ATTEMPTS
    assert provider._backoff_seconds == cli_module._PROVIDER_BACKOFF_SECONDS
    assert cli_module._PROVIDER_MAX_ATTEMPTS == 2
    assert cli_module._PROVIDER_BACKOFF_SECONDS == 2.0
