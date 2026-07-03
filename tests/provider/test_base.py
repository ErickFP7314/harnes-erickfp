"""tests/provider/test_base.py -- MockProvider satisface el Protocol Provider.

Protocol estructural (Decision 5 del design): MockProvider no hereda de
`Provider`, solo implementa `send`/`model`/`set_model` con las firmas
esperadas. runtime_checkable no es necesario aqui porque no se hace
isinstance en produccion contra Provider (solo contra Tool, en el registry).
"""

from erickfp.api.types import Block, Message, Response, ToolDef
from erickfp.provider.base import Provider
from tests.support import MockProvider


def test_mock_provider_satisfies_provider_protocol_statically(
    provider: Provider | None = None,
) -> None:
    # Asignacion estatica: si MockProvider no cumpliera la forma de Provider,
    # mypy fallaria aqui (verificado en el paso de mypy de Fase 11, ver 4.7/11.2).
    provider = MockProvider()
    assert provider.model() == "mock-model"


def test_mock_provider_set_model_changes_model() -> None:
    provider = MockProvider()
    provider.set_model("gemini/gemini-3-flash-preview")
    assert provider.model() == "gemini/gemini-3-flash-preview"


def test_mock_provider_send_returns_queued_response_in_order() -> None:
    first = Response(content=[Block(type="text", text="uno")], stop_reason="end_turn")
    second = Response(content=[Block(type="text", text="dos")], stop_reason="end_turn")
    provider = MockProvider(responses=[first, second])

    messages = [Message(role="user", content=[Block(type="text", text="hola")])]
    tools: list[ToolDef] = []

    assert provider.send(messages, tools) is first
    assert provider.send(messages, tools) is second


def test_mock_provider_send_records_sent_messages() -> None:
    provider = MockProvider()
    messages = [Message(role="user", content=[Block(type="text", text="hola")])]
    provider.send(messages, [])
    assert provider.sent_messages == [messages]


def test_mock_provider_send_without_queued_responses_returns_end_turn() -> None:
    provider = MockProvider()
    response = provider.send([], [])
    assert response.stop_reason == "end_turn"
    assert response.content == []
