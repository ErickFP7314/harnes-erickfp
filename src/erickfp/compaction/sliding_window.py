"""compaction/sliding_window.py -- `SlidingWindow` (Lote 6 harness-v0-2,
tarea 6.4, design.md Decision 5: "Impls: NoCompaction (default),
SlidingWindow(max), Summarize(provider)").

Descarta turnos antiguos cuando el historial supera `max_messages`,
conservando la cola mas reciente. El corte SIEMPRE pasa por
`safe_split_point` -- nunca trunca `messages` por indice crudo (Requirement
'SafeSplitPoint nunca parte un par tool_use/tool_result'); si el corte
seguro resultante es 0 (imposible sin partir un par), retorna el historial
sin cambios en vez de romper la conversacion.
"""

from __future__ import annotations

from erickfp.api.types import Message
from erickfp.compaction.safe_split import safe_split_point


class SlidingWindow:
    """Conserva como maximo `max_messages` mensajes recientes."""

    def __init__(self, max_messages: int) -> None:
        self._max_messages = max_messages

    def compact(self, messages: list[Message]) -> list[Message]:
        if len(messages) <= self._max_messages:
            return messages

        desired = len(messages) - self._max_messages
        split = safe_split_point(messages, desired)
        if split <= 0:
            return messages

        return messages[split:]
