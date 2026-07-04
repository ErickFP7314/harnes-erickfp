"""tests/provider/test_litellm_gemini_retry.py -- retry con backoff acotado
ante `500 INTERNAL` transitorios (Fase 11, tarea 11.5).

Hallazgo del spike 2.2 (docs/spikes/free-tier-limits.md): con el modelo del
ADR-001 (Gemma 4), 1 de 11 llamadas reales consecutivas fallo con un `500
INTERNAL` esporadico del servidor (no de cuota). Extiende el patron de
`scripts/spike_thought_signature.py::_call_with_backoff` (ya usado para
429/rate-limit en el spike) a `500`/`INTERNAL` dentro del adapter real.

`sleep_fn` es inyectable (default `time.sleep`) para que el test no espere
el backoff real -- mismo patron de inyeccion de dependencias que
`read_line`/`Provider`/`Store` en el resto del proyecto.
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


def test_send_retries_once_on_transient_500_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"count": 0}

    def fake_completion(**kwargs: Any) -> _FakeResponse:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("litellm.APIError: 500 INTERNAL server error")
        return _FakeResponse("ok tras reintento")

    import erickfp.provider.litellm_gemini as adapter_module

    monkeypatch.setattr(adapter_module.litellm, "completion", fake_completion)
    sleeps: list[float] = []
    provider = LiteLLMGeminiProvider(sleep_fn=sleeps.append)

    response = provider.send(_messages(), [])

    assert calls["count"] == 2
    assert response.content[0].text == "ok tras reintento"
    assert len(sleeps) == 1  # exactamente un backoff antes del reintento


def test_send_does_not_retry_non_transient_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_completion(**kwargs: Any) -> _FakeResponse:
        raise RuntimeError("401 Unauthorized: invalid API key")

    import erickfp.provider.litellm_gemini as adapter_module

    monkeypatch.setattr(adapter_module.litellm, "completion", fake_completion)
    provider = LiteLLMGeminiProvider(sleep_fn=lambda _seconds: None)

    # Hotfix 2026-07-04: el adapter traduce CUALQUIER fallo definitivo a
    # ProviderError (dominio) para que la CLI pueda fallar limpio sin conocer
    # los tipos de excepcion de litellm.
    with pytest.raises(ProviderError, match="401 Unauthorized"):
        provider.send(_messages(), [])


def test_send_raises_after_second_transient_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """El reintento es ACOTADO (una sola vez) -- un segundo 500 se propaga,
    nunca se silencia un fallo real."""

    def fake_completion(**kwargs: Any) -> _FakeResponse:
        raise RuntimeError("500 INTERNAL")

    import erickfp.provider.litellm_gemini as adapter_module

    monkeypatch.setattr(adapter_module.litellm, "completion", fake_completion)
    provider = LiteLLMGeminiProvider(sleep_fn=lambda _seconds: None)

    with pytest.raises(ProviderError, match="500 INTERNAL"):
        provider.send(_messages(), [])
