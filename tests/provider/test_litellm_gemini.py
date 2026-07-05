"""tests/provider/test_litellm_gemini.py -- adapter traduce litellm crudo -> tipos propios.

Nunca se llama a la API real (la GEMINI_API_KEY vigente esta revocada, ver
docs/spikes/thought-signature.md). Todo se prueba mockeando
`litellm.completion` a nivel de modulo -- ningun tipo nativo de litellm debe
cruzar hacia el llamador (Decision 2 del design).
"""

from types import SimpleNamespace
from typing import Any

import pytest

from erickfp.api.types import Block, Message, Response, ToolDef, Usage
from erickfp.provider.litellm_gemini import DEFAULT_MODEL, LiteLLMGeminiProvider


def _raw_text_response(text: str = "hola desde gemini") -> SimpleNamespace:
    message = SimpleNamespace(content=text, tool_calls=None, provider_specific_fields=None)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice])


def _raw_tool_call_response(call_id: str = "call_abc123") -> SimpleNamespace:
    function = SimpleNamespace(name="bash", arguments='{"command": "echo hola"}')
    tool_call = SimpleNamespace(id=call_id, function=function)
    message = SimpleNamespace(content=None, tool_calls=[tool_call], provider_specific_fields=None)
    choice = SimpleNamespace(message=message, finish_reason="tool_calls")
    return SimpleNamespace(choices=[choice])


def test_default_model_is_a_configurable_constant() -> None:
    # ADR-001 (2026-07-03): Gemma 4 elegido por el usuario con evidencia del
    # spike 2.1 (tools + thought signatures round-trip verificados en vivo).
    assert DEFAULT_MODEL == "gemini/gemma-4-26b-a4b-it"


def test_provider_model_defaults_to_default_model_constant() -> None:
    provider = LiteLLMGeminiProvider()
    assert provider.model() == DEFAULT_MODEL


def test_send_translates_text_response_to_response_and_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_completion(**kwargs: Any) -> SimpleNamespace:
        calls.append(kwargs)
        return _raw_text_response("hola desde gemini")

    import erickfp.provider.litellm_gemini as adapter_module

    monkeypatch.setattr(adapter_module.litellm, "completion", fake_completion)

    provider = LiteLLMGeminiProvider()
    messages = [Message(role="user", content=[Block(type="text", text="hola")])]

    response = provider.send(messages, [])

    assert isinstance(response, Response)
    assert response.stop_reason == "stop"
    assert len(response.content) == 1
    assert isinstance(response.content[0], Block)
    assert response.content[0].type == "text"
    assert response.content[0].text == "hola desde gemini"

    # El adapter debe haber llamado a litellm con el modelo configurado.
    assert calls[0]["model"] == DEFAULT_MODEL


def test_send_translates_tool_call_response_to_tool_use_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_completion(**kwargs: Any) -> SimpleNamespace:
        return _raw_tool_call_response("call_abc123")

    import erickfp.provider.litellm_gemini as adapter_module

    monkeypatch.setattr(adapter_module.litellm, "completion", fake_completion)

    provider = LiteLLMGeminiProvider()
    messages = [Message(role="user", content=[Block(type="text", text="corre echo hola")])]
    tools = [
        ToolDef(
            name="bash",
            description="ejecuta un comando",
            input_schema={"type": "object", "properties": {"command": {"type": "string"}}},
            required=["command"],
        )
    ]

    response = provider.send(messages, tools)

    assert response.stop_reason == "tool_calls"
    block = response.content[0]
    assert block.type == "tool_use"
    assert block.tool_name == "bash"
    assert block.tool_input == '{"command": "echo hola"}'
    assert block.tool_use_id == "call_abc123"
    # No es una excepcion de diseno: el id crudo se guarda para el round-trip
    # de thought signature (spike 2.1), ver test_thought_signature_roundtrip.py.
    assert block.provider_metadata["raw_tool_call_id"] == "call_abc123"


def test_send_passes_tools_translated_to_litellm_function_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_completion(**kwargs: Any) -> SimpleNamespace:
        captured.update(kwargs)
        return _raw_text_response()

    import erickfp.provider.litellm_gemini as adapter_module

    monkeypatch.setattr(adapter_module.litellm, "completion", fake_completion)

    provider = LiteLLMGeminiProvider()
    tools = [
        ToolDef(
            name="bash",
            description="ejecuta un comando",
            input_schema={"type": "object", "properties": {"command": {"type": "string"}}},
            required=["command"],
        )
    ]
    provider.send([Message(role="user", content=[Block(type="text", text="hola")])], tools)

    assert captured["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "bash",
                "description": "ejecuta un comando",
                "parameters": {"type": "object", "properties": {"command": {"type": "string"}}},
            },
        }
    ]


def test_response_usage_is_domain_type_no_litellm_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Lote 3, tarea 3.12 (design.md Decision 6): el adapter traduce
    `raw.usage` (forma nativa de litellm) al tipo de dominio `Usage` --
    ningun objeto propio de litellm cruza hacia el llamador, igual que
    `Block.provider_metadata` (Decision 2)."""
    raw_usage = SimpleNamespace(prompt_tokens=12, completion_tokens=8, total_tokens=20)
    message = SimpleNamespace(
        content="hola desde gemini", tool_calls=None, provider_specific_fields=None
    )
    choice = SimpleNamespace(message=message, finish_reason="stop")
    raw = SimpleNamespace(choices=[choice], usage=raw_usage)

    def fake_completion(**kwargs: Any) -> SimpleNamespace:
        return raw

    import erickfp.provider.litellm_gemini as adapter_module

    monkeypatch.setattr(adapter_module.litellm, "completion", fake_completion)

    provider = LiteLLMGeminiProvider()
    messages = [Message(role="user", content=[Block(type="text", text="hola")])]

    response = provider.send(messages, [])

    assert type(response.usage) is Usage  # nunca el SimpleNamespace/tipo nativo de litellm
    assert response.usage == Usage(prompt=12, completion=8, total=20)


def test_response_usage_is_none_when_raw_has_no_usage_attribute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Complemento del RED anterior: si `raw` no trae `usage` (algunos mocks
    de prueba no lo modelan), el adapter no lanza -- retorna `usage=None`."""

    def fake_completion(**kwargs: Any) -> SimpleNamespace:
        return _raw_text_response("sin usage")

    import erickfp.provider.litellm_gemini as adapter_module

    monkeypatch.setattr(adapter_module.litellm, "completion", fake_completion)

    provider = LiteLLMGeminiProvider()
    messages = [Message(role="user", content=[Block(type="text", text="hola")])]

    response = provider.send(messages, [])

    assert response.usage is None


def test_send_with_no_tools_passes_none_to_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_completion(**kwargs: Any) -> SimpleNamespace:
        captured.update(kwargs)
        return _raw_text_response()

    import erickfp.provider.litellm_gemini as adapter_module

    monkeypatch.setattr(adapter_module.litellm, "completion", fake_completion)

    provider = LiteLLMGeminiProvider()
    provider.send([Message(role="user", content=[Block(type="text", text="hola")])], [])

    assert captured["tools"] is None
