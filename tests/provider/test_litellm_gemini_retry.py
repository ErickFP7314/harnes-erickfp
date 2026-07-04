"""tests/provider/test_litellm_gemini_retry.py -- retry configurable con
backoff ante errores transitorios (Lote 2, tareas 2.1-2.4, design.md
Decision 10, specs/provider-layer/spec.md Requirement 'Retry configurable
con backoff ante errores transitorios').

Reemplaza las constantes de modulo `_MAX_ATTEMPTS`/`_BACKOFF_SECONDS` (Fase
11 del ciclo 1) por `LiteLLMGeminiProvider.__init__(max_attempts,
backoff_seconds)`: mismo comportamiento, ahora configurable por instancia.
El default (`max_attempts=2, backoff_seconds=2.0`) preserva bit-a-bit el
comportamiento del ciclo 1 (rollback seguro).

`sleep_fn` sigue siendo inyectable (default `time.sleep`) para que el test
no espere el backoff real.
"""

from __future__ import annotations

from typing import Any

import pytest

from erickfp.api.types import Block, Message
from erickfp.provider.base import ProviderError
from erickfp.provider.litellm_gemini import LiteLLMGeminiProvider


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content
        self.tool_calls = None
        self.provider_specific_fields = None


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)
        self.finish_reason = "stop"


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


def _messages() -> list[Message]:
    return [Message(role="user", content=[Block(type="text", text="hola")])]


def test_retries_on_5xx_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario 'Reintento exitoso tras 5xx transitorio': GIVEN
    attempts=3, WHEN la primera llamada falla con 5xx y la segunda tiene
    exito, THEN retorna la respuesta exitosa sin propagar error."""
    calls = {"count": 0}

    def fake_completion(**kwargs: Any) -> _FakeResponse:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("litellm.APIError: 500 INTERNAL server error")
        return _FakeResponse("ok tras reintento")

    import erickfp.provider.litellm_gemini as adapter_module

    monkeypatch.setattr(adapter_module.litellm, "completion", fake_completion)
    sleeps: list[float] = []
    provider = LiteLLMGeminiProvider(max_attempts=3, sleep_fn=sleeps.append)

    response = provider.send(_messages(), [])

    assert calls["count"] == 2
    assert response.content[0].text == "ok tras reintento"
    assert len(sleeps) == 1


def test_exhausts_attempts_raises_clean_provider_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario 'Agotar intentos produce ProviderError limpio': GIVEN
    attempts=3 donde las 3 llamadas fallan con timeout, WHEN se agotan,
    THEN se lanza `ProviderError` con la causa registrada y ningun tipo de
    excepcion nativa del SDK cruza la frontera."""
    calls = {"count": 0}

    def fake_completion(**kwargs: Any) -> _FakeResponse:
        calls["count"] += 1
        raise RuntimeError("timeout: 500 INTERNAL")

    import erickfp.provider.litellm_gemini as adapter_module

    monkeypatch.setattr(adapter_module.litellm, "completion", fake_completion)
    provider = LiteLLMGeminiProvider(max_attempts=3, sleep_fn=lambda _seconds: None)

    with pytest.raises(ProviderError, match="timeout") as excinfo:
        provider.send(_messages(), [])

    assert calls["count"] == 3
    assert not isinstance(excinfo.value, RuntimeError)  # ProviderError, nunca la nativa
    assert excinfo.value.__cause__ is not None  # causa registrada (from exc)


def test_non_transient_4xx_does_not_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scenario 'Errores no transitorios no se reintentan': GIVEN un error
    de autenticacion (4xx no reintentable), WHEN ocurre en la primera
    llamada, THEN el adapter NO reintenta y propaga `ProviderError` de
    inmediato."""
    calls = {"count": 0}

    def fake_completion(**kwargs: Any) -> _FakeResponse:
        calls["count"] += 1
        raise RuntimeError("401 Unauthorized: invalid API key")

    import erickfp.provider.litellm_gemini as adapter_module

    monkeypatch.setattr(adapter_module.litellm, "completion", fake_completion)
    provider = LiteLLMGeminiProvider(max_attempts=3, sleep_fn=lambda _seconds: None)

    with pytest.raises(ProviderError, match="401 Unauthorized"):
        provider.send(_messages(), [])

    assert calls["count"] == 1  # sin reintento


def test_default_constructor_preserves_cycle1_two_attempt_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """El default (`max_attempts=2, backoff_seconds=2.0`) preserva
    bit-a-bit el comportamiento del ciclo 1: un segundo 500 consecutivo
    agota los intentos y se propaga como `ProviderError`."""

    def fake_completion(**kwargs: Any) -> _FakeResponse:
        raise RuntimeError("500 INTERNAL")

    import erickfp.provider.litellm_gemini as adapter_module

    monkeypatch.setattr(adapter_module.litellm, "completion", fake_completion)
    provider = LiteLLMGeminiProvider(sleep_fn=lambda _seconds: None)  # sin overrides

    with pytest.raises(ProviderError, match="500 INTERNAL"):
        provider.send(_messages(), [])
