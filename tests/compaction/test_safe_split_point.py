"""tests/compaction/test_safe_split_point.py -- `safe_split_point` (Lote 6
harness-v0-2, tareas 6.5-6.7, design.md Decision 5, specs/compaction/spec.md
Requirement 'SafeSplitPoint nunca parte un par tool_use/tool_result').

Riesgo transversal (c) del Lote 6: invariante formal parametrizado con
MULTIPLES conversaciones sinteticas (pares consecutivos, al inicio, al
final, sin pares) y TODOS los cortes candidatos posibles para cada una --
en ningun caso el corte deja un `tool_result` sin su `tool_use` precedente
(ni viceversa). Un corte imposible (ej. el par esta pegado al inicio de la
conversacion) se resuelve NO compactando (retorna 0 -- "mejor que romper la
conversacion"), nunca partiendo el par.
"""

from __future__ import annotations

import pytest

from erickfp.api.types import Block, Message
from erickfp.compaction.safe_split import has_tool_result, safe_split_point


def _user_text(text: str = "hola") -> Message:
    return Message(role="user", content=[Block(type="text", text=text)])


def _assistant_text(text: str = "ok") -> Message:
    return Message(role="assistant", content=[Block(type="text", text=text)])


def _tool_use(call_id: str, name: str = "bash") -> Message:
    return Message(
        role="assistant",
        content=[Block(type="tool_use", tool_use_id=call_id, tool_name=name, tool_input="{}")],
    )


def _tool_result(call_id: str, result: str = "ok") -> Message:
    return Message(
        role="user", content=[Block(type="tool_result", tool_use_id=call_id, tool_result=result)]
    )


def _tool_use_ids(messages: list[Message]) -> set[str]:
    return {
        block.tool_use_id for message in messages for block in message.content
        if block.type == "tool_use"
    }


def _tool_result_ids(messages: list[Message]) -> set[str]:
    return {
        block.tool_use_id for message in messages for block in message.content
        if block.type == "tool_result"
    }


# -- conversaciones sinteticas (Riesgo transversal (c)) ----------------------

_PAIR_IN_THE_MIDDLE = [
    _user_text("raiz"),
    _tool_use("call-1"),
    _tool_result("call-1"),
    _assistant_text("listo"),
    _user_text("otra pregunta"),
]

_CONSECUTIVE_PAIRS = [
    _user_text("raiz"),
    _tool_use("call-1"),
    _tool_result("call-1"),
    _tool_use("call-2"),
    _tool_result("call-2"),
    _assistant_text("listo"),
]

_PAIR_AT_THE_START = [
    _tool_use("call-1"),
    _tool_result("call-1"),
    _assistant_text("listo"),
    _user_text("otra pregunta"),
]

_PAIR_AT_THE_END = [
    _user_text("raiz"),
    _assistant_text("ok"),
    _user_text("otra pregunta"),
    _tool_use("call-1"),
    _tool_result("call-1"),
]

_NO_PENDING_PAIRS = [
    _user_text("uno"),
    _assistant_text("dos"),
    _user_text("tres"),
    _assistant_text("cuatro"),
]

_CONVERSATIONS = {
    "pair_in_the_middle": _PAIR_IN_THE_MIDDLE,
    "consecutive_pairs": _CONSECUTIVE_PAIRS,
    "pair_at_the_start": _PAIR_AT_THE_START,
    "pair_at_the_end": _PAIR_AT_THE_END,
    "no_pending_pairs": _NO_PENDING_PAIRS,
}


@pytest.mark.parametrize("conversation", _CONVERSATIONS.values(), ids=_CONVERSATIONS.keys())
def test_never_splits_a_tool_use_tool_result_pair(conversation: list[Message]) -> None:
    """Scenario 'Ningun par roto tras compactar (invariante parametrizado)':
    para CADA corte candidato posible (0..len(messages)) sobre CADA
    conversacion sintetica, el corte real que produce `safe_split_point`
    nunca separa un `tool_use` de su `tool_result` en segmentos distintos."""
    for desired in range(len(conversation) + 1):
        split = safe_split_point(conversation, desired)

        assert 0 <= split <= len(conversation)

        dropped, kept = conversation[:split], conversation[split:]
        dropped_use, dropped_result = _tool_use_ids(dropped), _tool_result_ids(dropped)
        kept_use, kept_result = _tool_use_ids(kept), _tool_result_ids(kept)

        # ningun tool_use en un segmento con su tool_result en el otro.
        assert not (dropped_use & kept_result), (conversation, desired, split)
        assert not (kept_use & dropped_result), (conversation, desired, split)


def test_no_pending_pairs_applies_threshold_cut_directly() -> None:
    """Scenario 'Sin bloques tool_use pendientes': GIVEN un historial sin
    ningun par abierto, WHEN se aplica compactacion, THEN el corte se
    aplica EXACTAMENTE en el punto calculado por umbral, sin ajustes."""
    conversation = _NO_PENDING_PAIRS
    desired = 2

    split = safe_split_point(conversation, desired)

    assert split == desired  # sin ajuste: ningun mensaje en `desired` es tool_result


def test_split_candidate_falls_inside_a_pair_adjusts_backward() -> None:
    """Scenario 'Corte candidato cae dentro de un par tool_use/tool_result':
    GIVEN un corte candidato que cae justo en el `tool_result` (dejando su
    `tool_use` en el segmento descartado), WHEN se calcula el corte real,
    THEN el sistema retrocede hasta el limite del turno completo (el propio
    `tool_use`), manteniendo el par intacto en el mismo segmento."""
    conversation = _PAIR_IN_THE_MIDDLE
    # indice 2 es el mensaje "user tool_result" -- justo despues del tool_use.
    desired = 2

    split = safe_split_point(conversation, desired)

    assert split == 1  # retrocede al "assistant tool_use" (indice 1)
    assert not has_tool_result(conversation[split - 1]) if split > 0 else True


def test_desired_at_or_below_zero_returns_zero() -> None:
    assert safe_split_point(_PAIR_IN_THE_MIDDLE, 0) == 0
    assert safe_split_point(_PAIR_IN_THE_MIDDLE, -3) == 0


def test_desired_beyond_length_returns_full_length() -> None:
    conversation = _NO_PENDING_PAIRS
    assert safe_split_point(conversation, len(conversation) + 5) == len(conversation)


def test_pair_glued_to_the_start_yields_impossible_split_falls_back_to_zero() -> None:
    """Corte imposible (el unico par esta pegado al inicio de la
    conversacion, Riesgo transversal (c)): `safe_split_point` retrocede
    hasta 0 -- "no compactar" es la unica salida segura, nunca parte el
    par."""
    conversation = _PAIR_AT_THE_START
    desired = 1  # cae justo en el tool_result inicial

    split = safe_split_point(conversation, desired)

    assert split == 0  # imposible cortar sin partir el par -- no se compacta
