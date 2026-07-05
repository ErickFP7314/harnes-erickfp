"""compaction/summarize.py -- `Summarize` (Lote 6 harness-v0-2, tarea 6.11,
design.md Decision 5: "Impls: NoCompaction (default), SlidingWindow(max),
Summarize(provider)").

Condensa la porcion antigua del historial en un unico mensaje sintetico,
pidiendole al mismo `Provider` una sintesis one-shot (sin tools) del
segmento descartado. El corte SIEMPRE pasa por `safe_split_point` -- si el
corte seguro resultante es 0 (imposible sin partir un par pendiente), no
compacta. Si la llamada de sintesis falla (`ProviderError`), degrada a "no
compactar" -- la compactacion nunca debe romper el turno en curso (Puntos
criticos del Lote 6).

Thought signatures (design.md D5): la firma viaja DENTRO de
`Block.provider_metadata` del mensaje que la origino. Al reemplazar los
turnos colapsados por un mensaje sintetico NUEVO (`Block` recien creado, sin
`provider_metadata` copiado), las firmas de esos turnos se descartan a
proposito -- ya no son round-trips vivos una vez resumidos. Los mensajes
`recent` se conservan tal cual, con cualquier firma que tuvieran intacta.
"""

from __future__ import annotations

from erickfp.api.types import Block, Message
from erickfp.compaction.safe_split import safe_split_point
from erickfp.provider.base import Provider, ProviderError

_INSTRUCTIONS = (
    "Resume de forma concisa la siguiente porcion antigua de la conversacion. "
    "Preserva decisiones tomadas, nombres de archivos/funciones/comandos y "
    "cualquier dato que sea necesario para continuar el trabajo. No inventes "
    "informacion que no este presente en la transcripcion."
)

_SUMMARY_PREFIX = "[resumen de la conversacion anterior] "


class Summarize:
    """Compacta condensando turnos antiguos via el `Provider` inyectado."""

    def __init__(self, provider: Provider, threshold: int, keep_recent: int) -> None:
        self._provider = provider
        self._threshold = threshold
        self._keep_recent = keep_recent

    def compact(self, messages: list[Message]) -> list[Message]:
        if len(messages) < self._threshold:
            return messages

        desired = len(messages) - self._keep_recent
        split = safe_split_point(messages, desired)
        if split <= 0:
            return messages

        old, recent = messages[:split], messages[split:]

        try:
            response = self._provider.send(
                [Message(role="user", content=[Block(type="text", text=self._render(old))])],
                [],
            )
        except ProviderError:
            return messages

        summary_text = "".join(
            block.text for block in response.content if block.type == "text" and block.text
        )
        if not summary_text:
            return messages

        summary_message = Message(
            role="user",
            content=[Block(type="text", text=f"{_SUMMARY_PREFIX}{summary_text}")],
        )
        return [summary_message, *recent]

    def _render(self, messages: list[Message]) -> str:
        """Transcripcion legible de `messages`, usada como input de la
        llamada de sintesis. No es un formato consumido por otra capa --
        solo debe ser legible para el modelo que resume."""
        lines = [_INSTRUCTIONS, ""]
        for message in messages:
            for block in message.content:
                if block.type == "text" and block.text:
                    lines.append(f"{message.role}: {block.text}")
                elif block.type == "tool_use":
                    lines.append(
                        f"{message.role} tool_use {block.tool_name}: {block.tool_input}"
                    )
                elif block.type == "tool_result":
                    lines.append(f"{message.role} tool_result: {block.tool_result}")
        return "\n".join(lines)
