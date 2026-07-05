"""compaction/safe_split.py -- `safe_split_point` (Lote 6 harness-v0-2,
tareas 6.5-6.7, design.md Decision 5, specs/compaction/spec.md Requirement
'SafeSplitPoint nunca parte un par tool_use/tool_result' -- invariante
formal).

Toda estrategia que recorte el historial (`SlidingWindow`, `Summarize`) DEBE
enrutar su corte a traves de esta funcion -- nunca cortar `messages` a
ciegas por indice. El algoritmo es literal al design.md:

    dado un corte candidato `desired` (todo lo que cae en `messages[:k]` se
    descarta, `messages[k:]` se conserva), mientras `messages[k].role ==
    "user"` contenga algun bloque `tool_result`, retrocede `k -= 1`.

Un mensaje `user` con `tool_result` en la posicion `k` significa que su
`tool_use` correspondiente vive en `messages[k-1]` (mensaje `assistant`
inmediatamente anterior, por la alternancia estricta de turnos que produce
`agent/loop.py::run_turn`); si el corte quedara en `k`, ese `tool_use` caeria
en el segmento descartado mientras su `tool_result` sobrevive en el
conservado -- exactamente el par roto que el invariante prohibe. Retroceder
un paso basta: `messages[k-1]` es `assistant` (no `user`), por lo que el
`while` se detiene ahi, con el par completo ya dentro del segmento
conservado.

Si retroceder no encuentra un limite seguro antes de llegar a 0 (el propio
par esta pegado al inicio de la conversacion sintetica), la funcion retorna
0: ese valor senala a los llamadores "corte imposible, no compactar" -- ver
`sliding_window.py`/`summarize.py`, que tratan `split <= 0` como "devolver el
historial sin cambios". Preferir no comprimir a romper la conversacion.
"""

from __future__ import annotations

from erickfp.api.types import Message


def has_tool_result(message: Message) -> bool:
    """`True` si el mensaje contiene al menos un bloque `tool_result`."""
    return any(block.type == "tool_result" for block in message.content)


def safe_split_point(messages: list[Message], desired: int) -> int:
    """Calcula el indice de corte real mas cercano a `desired` que nunca
    deja un `tool_result` huerfano (sin su `tool_use` en el mismo
    segmento)."""
    if desired <= 0:
        return 0
    if desired >= len(messages):
        return len(messages)

    k = desired
    while k > 0 and messages[k].role == "user" and has_tool_result(messages[k]):
        k -= 1
    return k
