"""tests/cli/test_chat.py -- comando `erickfp chat` (spec agent-loop, axioma
idea.md: 'la IA no actua sin consultar la raiz'). Fase 7, tarea 7.4.

Prueba la composicion del contexto de sistema (`core/Claude` + roles de
`core/agents/` + `Store.preamble()`) y que se antepone al primer turno
enviado al Provider. NO ejercita la I/O real de terminal -- eso queda para
el smoke E2E manual (Fase 11.3). `_MockStore` es un doble ad-hoc (duck
typing estructural, Decision 5 del design): satisface la forma de
`Store.preamble()` sin depender de `erickfp.memory` (Fase 9, aun no existe
en este lote).
"""

from __future__ import annotations

from pathlib import Path

from erickfp.api.types import Block, Response
from erickfp.cli import build_system_context, run_chat_session
from erickfp.tools.registry import ToolRegistry
from tests.support import MockProvider


class _MockStore:
    def preamble(self) -> str:
        return "PREAMBLE-DE-PRUEBA: el usuario prefiere Python."


class _DummyConsole:
    def __init__(self) -> None:
        self.printed: list[str] = []

    def print(self, *args: object, **kwargs: object) -> None:
        self.printed.append(" ".join(str(a) for a in args))


def _make_root(tmp_path: Path) -> Path:
    root = tmp_path / ".ErickFP"
    (root / "core" / "agents").mkdir(parents=True)
    (root / "core" / "Claude").write_text("AXIOMA: legibilidad ante todo.")
    (root / "core" / "agents" / "planner.md").write_text("Rol: Planner.")
    return root


def test_preamble_loaded_before_first_turn(tmp_path: Path) -> None:
    root = _make_root(tmp_path)

    context = build_system_context(root, _MockStore())

    assert "AXIOMA: legibilidad ante todo." in context
    assert "Rol: Planner." in context
    assert "PREAMBLE-DE-PRUEBA" in context

    provider = MockProvider(
        responses=[Response(content=[Block(type="text", text="hola")], stop_reason="end_turn")]
    )
    inputs = iter(["hola agente", "salir"])

    run_chat_session(
        provider=provider,
        tools=ToolRegistry(),
        console=_DummyConsole(),
        system_context=context,
        read_line=lambda prompt: next(inputs),
    )

    assert len(provider.sent_messages) == 1  # un solo turno antes de "salir"
    first_call_messages = provider.sent_messages[0]
    combined_text = " ".join(
        block.text for message in first_call_messages for block in message.content
    )
    assert "PREAMBLE-DE-PRUEBA" in combined_text
    assert "hola agente" in combined_text


def test_system_context_not_repeated_on_second_turn(tmp_path: Path) -> None:
    """El contexto de sistema se antepone SOLO al primer mensaje de usuario
    -- el mensaje NUEVO que agrega el segundo turno no lo vuelve a incluir
    (si reaparece en el historial completo es porque el primer mensaje sigue
    ahi, lo cual es correcto para una API stateless; lo que NO debe pasar es
    que se inyecte un bloque de contexto adicional en cada turno nuevo)."""
    root = _make_root(tmp_path)
    context = build_system_context(root, _MockStore())

    provider = MockProvider(
        responses=[
            Response(content=[Block(type="text", text="uno")], stop_reason="end_turn"),
            Response(content=[Block(type="text", text="dos")], stop_reason="end_turn"),
        ]
    )
    inputs = iter(["primer turno", "segundo turno", "salir"])

    run_chat_session(
        provider=provider,
        tools=ToolRegistry(),
        console=_DummyConsole(),
        system_context=context,
        read_line=lambda prompt: next(inputs),
    )

    assert len(provider.sent_messages) == 2
    newest_message = provider.sent_messages[1][-1]  # el mensaje agregado en este turno
    newest_text = " ".join(block.text for block in newest_message.content)
    assert "PREAMBLE-DE-PRUEBA" not in newest_text
    assert "segundo turno" in newest_text
