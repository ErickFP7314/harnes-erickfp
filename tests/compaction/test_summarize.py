"""tests/compaction/test_summarize.py -- `Summarize` (Lote 6 harness-v0-2,
tareas 6.10-6.11, design.md Decision 5, specs/compaction/spec.md Requirement
'CompactionStrategy con sliding window y summarize').

`Summarize(provider, threshold, keep_recent)` condensa los turnos antiguos
en un unico mensaje sintetico (via una llamada one-shot sin tools al mismo
`provider`) cuando el historial alcanza `threshold`, conservando los ultimos
`keep_recent` mensajes intactos. El corte SIEMPRE pasa por
`safe_split_point` (nunca parte un par pendiente) y descarta a proposito
las thought signatures (`provider_metadata`) de los turnos colapsados --
design.md D5: "ya no son round-trips vivos". Si el `Provider` de resumen
falla (`ProviderError`), degrada a "no compactar" sin romper el turno
(Puntos criticos del Lote 6).
"""

from __future__ import annotations

from erickfp.api.types import Block, Message, Response
from erickfp.compaction.summarize import Summarize
from erickfp.provider.base import ProviderError
from tests.support import MockProvider


def _text(role: str, text: str, provider_metadata: dict | None = None) -> Message:
    block = Block(type="text", text=text, provider_metadata=provider_metadata or {})
    return Message(role=role, content=[block])  # type: ignore[arg-type]


class _FailingProvider:
    """Doble que siempre falla en `send()` -- para el path de degradacion."""

    def send(self, messages, tools):  # type: ignore[no-untyped-def]
        raise ProviderError("simulado: el resumen fallo")

    def model(self) -> str:
        return "failing-model"

    def set_model(self, name: str) -> None:
        pass


def test_summarize_condenses_old_turns_and_drops_stale_signatures() -> None:
    """Scenario 'Historial excede el umbral configurado' aplicado a
    `Summarize`: GIVEN un historial de 8 mensajes con `threshold=8` y
    `keep_recent=2` (turnos antiguos llevan una thought signature), WHEN se
    compacta, THEN el resultado es mas corto, los 2 mensajes mas recientes
    se preservan intactos (con su propia signature, si la tuvieran), y NINGUN
    mensaje del resultado que provenga de los turnos colapsados conserva la
    signature vieja -- fue reemplazada por un mensaje sintetico de resumen."""
    old_messages = [
        _text("user", f"turno viejo {i}", provider_metadata={"thought_signatures": f"sig-{i}"})
        for i in range(6)
    ]
    recent_messages = [_text("user", "turno reciente 1"), _text("assistant", "turno reciente 2")]
    messages = [*old_messages, *recent_messages]

    summary_response = Response(
        content=[Block(type="text", text="resumen: se discutieron 6 turnos antiguos")],
        stop_reason="end_turn",
    )
    provider = MockProvider(responses=[summary_response])
    strategy = Summarize(provider, threshold=8, keep_recent=2)

    result = strategy.compact(messages)

    assert len(result) < len(messages)
    # los 2 turnos recientes sobreviven intactos, en el mismo orden.
    assert result[-2:] == recent_messages
    # el resumen viaja como el/los primeros mensajes -- ninguno conserva las
    # signatures viejas de los turnos colapsados.
    collapsed_part = result[:-2]
    assert collapsed_part  # existe un mensaje sintetico de resumen
    for message in collapsed_part:
        for block in message.content:
            assert "thought_signatures" not in block.provider_metadata
    summary_text = " ".join(
        block.text for message in collapsed_part for block in message.content if block.text
    )
    assert "se discutieron 6 turnos antiguos" in summary_text
    # el provider de resumen recibio una unica llamada one-shot SIN tools.
    assert len(provider.sent_messages) == 1
    assert provider.sent_tools == [[]]


def test_summarize_below_threshold_returns_unchanged() -> None:
    """Triangulacion: por debajo del umbral, no se invoca al provider ni se
    modifica el historial."""
    messages = [_text("user", "hola"), _text("assistant", "hola, en que ayudo?")]
    provider = MockProvider(responses=[])
    strategy = Summarize(provider, threshold=10, keep_recent=2)

    result = strategy.compact(messages)

    assert result is messages
    assert provider.sent_messages == []


def test_summarize_degrades_to_no_compaction_on_provider_error() -> None:
    """Puntos criticos del Lote 6: si el `Provider` inyectado falla al
    intentar sintetizar el resumen (`ProviderError`), `Summarize` degrada a
    "no compactar" -- retorna el historial original sin romper el turno."""
    messages = [_text("user", f"turno {i}") for i in range(8)]
    strategy = Summarize(_FailingProvider(), threshold=8, keep_recent=2)

    result = strategy.compact(messages)

    assert result == messages


def test_summarize_with_no_safe_split_point_returns_unchanged() -> None:
    """Riesgo transversal (c): si el corte deseado por `keep_recent` cae
    dentro de un par pendiente pegado al inicio (imposible de resolver sin
    romperlo), `Summarize` no compacta -- nunca invoca al provider."""
    messages = [
        Message(
            role="assistant",
            content=[
                Block(type="tool_use", tool_use_id="call-1", tool_name="bash", tool_input="{}")
            ],
        ),
        Message(
            role="user",
            content=[Block(type="tool_result", tool_use_id="call-1", tool_result="ok")],
        ),
        _text("assistant", "listo"),
        _text("user", "otra pregunta"),
        _text("assistant", "respuesta"),
        _text("user", "una mas"),
        _text("assistant", "otra respuesta"),
        _text("user", "final"),
    ]
    provider = MockProvider(responses=[])
    # keep_recent = len(messages) - 1 fuerza el corte deseado justo en el
    # tool_result inicial (indice 1) -- retrocede a 0 (imposible, ver
    # safe_split.py).
    strategy = Summarize(provider, threshold=1, keep_recent=len(messages) - 1)

    result = strategy.compact(messages)

    assert result == messages
    assert provider.sent_messages == []
