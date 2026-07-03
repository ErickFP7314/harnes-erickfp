"""Test doubles compartidos entre las suites de tests (NO es codigo de produccion).

Viven aqui (y no en `src/erickfp/`) porque son implementaciones de prueba de
los Protocols estructurales de Decision 5 del design: no heredan de nada,
simplemente satisfacen la forma esperada. Reutilizados por Fases 4-6 (Provider,
Tool, agent loop).
"""

from __future__ import annotations

from erickfp.api.types import Message, Response, ToolDef


class MockProvider:
    """Provider de prueba: satisface el Protocol `Provider` sin heredar de el.

    Responde con una cola de `Response` predefinidas, una por cada llamada a
    `send()`, para simular turnos sucesivos de un agent loop sin red.
    """

    def __init__(
        self, responses: list[Response] | None = None, model_name: str = "mock-model"
    ) -> None:
        self._responses = list(responses or [])
        self._model_name = model_name
        self.sent_messages: list[list[Message]] = []
        self.sent_tools: list[list[ToolDef]] = []

    def send(self, messages: list[Message], tools: list[ToolDef]) -> Response:
        self.sent_messages.append(messages)
        self.sent_tools.append(tools)
        if not self._responses:
            return Response(content=[], stop_reason="end_turn")
        return self._responses.pop(0)

    def model(self) -> str:
        return self._model_name

    def set_model(self, name: str) -> None:
        self._model_name = name


class FakeTool:
    """Tool de prueba minima: satisface el Protocol `Tool` (Decision 5)."""

    def __init__(self, name: str = "fake_tool") -> None:
        self._name = name
        self.executed_with: list[str] = []

    def definition(self) -> ToolDef:
        return ToolDef(
            name=self._name,
            description="tool de prueba",
            input_schema={"type": "object", "properties": {}},
            required=[],
        )

    def execute(self, input: str) -> tuple[str, bool]:
        self.executed_with.append(input)
        return (f"executed:{input}", False)
