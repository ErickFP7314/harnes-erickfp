"""tests/provider/test_thought_signature_roundtrip.py -- aplica el hallazgo del spike 2.1.

Round-trip esperado (analisis estatico de litellm==1.83.7, documentado en
docs/spikes/thought-signature.md -- validacion empirica pendiente de key
nueva, la actual esta revocada):

1. Turno 1 con tool_use: litellm devuelve el `tool_call.id` con la firma
   embebida (separador `__thought__`). El adapter la guarda en
   `Block.provider_metadata["raw_tool_call_id"]`.
2. Turno 2: al reenviar ese Block (mas el tool_result correspondiente), el
   adapter debe reusar el id CRUDO (con la firma) como `tool_calls[0].id` en
   el payload saliente -- no un id nuevo ni el id "limpio".

Tambien cubre el caso solo-texto: la firma viaja en
`message.provider_specific_fields["thought_signatures"]` y debe reinyectarse
en el mismo campo del payload saliente del turno siguiente.
"""

from types import SimpleNamespace
from typing import Any

import pytest

from erickfp.api.types import Block, Message
from erickfp.provider.litellm_gemini import THOUGHT_SIGNATURE_SEPARATOR, LiteLLMGeminiProvider

RAW_ID_WITH_SIGNATURE = f"call_abc123{THOUGHT_SIGNATURE_SEPARATOR}QkFTRTY0U0lHTg=="


def _raw_tool_call_response() -> SimpleNamespace:
    function = SimpleNamespace(name="bash", arguments='{"command": "echo hola"}')
    tool_call = SimpleNamespace(id=RAW_ID_WITH_SIGNATURE, function=function)
    message = SimpleNamespace(
        content=None, tool_calls=[tool_call], provider_specific_fields=None
    )
    choice = SimpleNamespace(message=message, finish_reason="tool_calls")
    return SimpleNamespace(choices=[choice])


def _raw_text_response_with_signature(signatures: list[str]) -> SimpleNamespace:
    message = SimpleNamespace(
        content="ok, continuo",
        tool_calls=None,
        provider_specific_fields={"thought_signatures": signatures},
    )
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice])


def _raw_text_response(text: str = "listo") -> SimpleNamespace:
    message = SimpleNamespace(content=text, tool_calls=None, provider_specific_fields=None)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice])


def test_tool_use_raw_id_with_thought_signature_is_reinjected_on_next_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_payloads: list[dict[str, Any]] = []

    def fake_completion(**kwargs: Any) -> SimpleNamespace:
        captured_payloads.append(kwargs)
        if len(captured_payloads) == 1:
            return _raw_tool_call_response()
        return _raw_text_response("turno 2 ok")

    import erickfp.provider.litellm_gemini as adapter_module

    monkeypatch.setattr(adapter_module.litellm, "completion", fake_completion)

    provider = LiteLLMGeminiProvider()

    # Turno 1: el usuario pide algo que dispara tool_use.
    turn1_messages = [Message(role="user", content=[Block(type="text", text="corre echo hola")])]
    response1 = provider.send(turn1_messages, [])

    tool_use_block = response1.content[0]
    assert tool_use_block.type == "tool_use"
    assert tool_use_block.provider_metadata["raw_tool_call_id"] == RAW_ID_WITH_SIGNATURE
    assert THOUGHT_SIGNATURE_SEPARATOR in tool_use_block.provider_metadata["raw_tool_call_id"]

    # Turno 2: el harness reenvia el Block del assistant + el tool_result,
    # exactamente como lo haria el agent loop real.
    tool_result_block = Block(
        type="tool_result",
        tool_use_id=tool_use_block.tool_use_id,
        tool_result="hola\n",
        is_error=False,
    )
    turn2_messages = [
        *turn1_messages,
        Message(role="assistant", content=[tool_use_block]),
        Message(role="user", content=[tool_result_block]),
    ]
    provider.send(turn2_messages, [])

    # El segundo payload enviado a litellm debe contener el tool_call con el
    # id CRUDO (firma incluida) intacto -- eso es lo que permite a litellm
    # reconstruir `thoughtSignature` en el request saliente a Gemini.
    second_payload = captured_payloads[1]
    assistant_entries = [m for m in second_payload["messages"] if m["role"] == "assistant"]
    assert len(assistant_entries) == 1
    assert assistant_entries[0]["tool_calls"][0]["id"] == RAW_ID_WITH_SIGNATURE

    # Y el tool_result se tradujo a un mensaje role=tool con el id limpio del bloque.
    tool_entries = [m for m in second_payload["messages"] if m["role"] == "tool"]
    assert tool_entries[0]["tool_call_id"] == tool_use_block.tool_use_id
    assert tool_entries[0]["content"] == "hola\n"


def test_text_only_thought_signature_is_reinjected_on_next_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_payloads: list[dict[str, Any]] = []
    signatures = ["QkFTRTY0U0lHTg=="]

    def fake_completion(**kwargs: Any) -> SimpleNamespace:
        captured_payloads.append(kwargs)
        if len(captured_payloads) == 1:
            return _raw_text_response_with_signature(signatures)
        return _raw_text_response("turno 2 ok")

    import erickfp.provider.litellm_gemini as adapter_module

    monkeypatch.setattr(adapter_module.litellm, "completion", fake_completion)

    provider = LiteLLMGeminiProvider()

    turn1_messages = [Message(role="user", content=[Block(type="text", text="piensa en voz alta")])]
    response1 = provider.send(turn1_messages, [])

    text_block = response1.content[0]
    assert text_block.provider_metadata["thought_signatures"] == signatures

    turn2_messages = [
        *turn1_messages,
        Message(role="assistant", content=[text_block]),
        Message(role="user", content=[Block(type="text", text="continua")]),
    ]
    provider.send(turn2_messages, [])

    second_payload = captured_payloads[1]
    assistant_entries = [m for m in second_payload["messages"] if m["role"] == "assistant"]
    assert assistant_entries[0]["provider_specific_fields"] == {
        "thought_signatures": signatures
    }
