"""tests/cogito/test_phases.py -- ejecucion de una fase individual del Ciclo
Cogito (Fase 10, tarea 10.3; spec ciclo-cogito, Requirement 'duda exige
claridad antes de avanzar').

`duda` es la unica fase que puede negarse a producir artefacto: usa un
protocolo de marcadores explicitos (`AMBIGUO:`/`ACEPTADO:`) para que el
Provider declare si el objetivo es claro o ambiguo. Las demas fases siempre
producen artefacto a partir del texto de entrada (el artefacto previo).
"""

from __future__ import annotations

from erickfp.api.types import Block, Response
from erickfp.cogito.phases import run_phase
from erickfp.tools.registry import ToolRegistry
from tests.support import MockProvider


def test_duda_detects_ambiguity_and_returns_clarification_without_artifact() -> None:
    provider = MockProvider(
        responses=[
            Response(
                content=[Block(type="text", text="AMBIGUO: falta saber que backend usar.")],
                stop_reason="end_turn",
            )
        ]
    )

    result = run_phase(provider, ToolRegistry(), "duda", "Rol Planner.", "objetivo confuso")

    assert result.status == "clarification"
    assert "falta saber que backend usar" in result.content


def test_duda_with_clear_objective_produces_accepted_artifact() -> None:
    provider = MockProvider(
        responses=[
            Response(
                content=[Block(type="text", text="ACEPTADO: # duda.md\n\nObjetivo validado.")],
                stop_reason="end_turn",
            )
        ]
    )

    result = run_phase(provider, ToolRegistry(), "duda", "Rol Planner.", "objetivo claro")

    assert result.status == "artifact"
    assert result.content.startswith("# duda.md")


def test_duda_without_recognized_marker_fails_safe_as_clarification() -> None:
    """Ausencia de marcador reconocido: nunca se genera un artefacto no
    marcado explicitamente como aceptado (fail-safe)."""
    provider = MockProvider(
        responses=[
            Response(
                content=[Block(type="text", text="no entendi la pregunta")],
                stop_reason="end_turn",
            )
        ]
    )

    result = run_phase(provider, ToolRegistry(), "duda", "Rol Planner.", "objetivo raro")

    assert result.status == "clarification"


def test_divide_always_produces_artifact_from_previous_content() -> None:
    provider = MockProvider(
        responses=[
            Response(
                content=[Block(type="text", text="# divide.md\n\nPartes minimas.")],
                stop_reason="end_turn",
            )
        ]
    )

    result = run_phase(
        provider, ToolRegistry(), "divide", "Rol Planner.", "# duda.md\n\nObjetivo validado."
    )

    assert result.status == "artifact"
    assert "Partes minimas" in result.content


def test_role_prompt_and_input_reach_the_provider() -> None:
    provider = MockProvider(
        responses=[
            Response(content=[Block(type="text", text="# ordena.md")], stop_reason="end_turn")
        ]
    )

    run_phase(provider, ToolRegistry(), "ordena", "Rol Coder.", "# divide.md\n\nPlan.")

    sent_text = " ".join(
        block.text
        for message in provider.sent_messages[0]
        for block in message.content
        if block.type == "text"
    )
    assert "Rol Coder." in sent_text
    assert "# divide.md" in sent_text
