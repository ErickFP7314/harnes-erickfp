"""tests/cogito/test_orchestrator.py -- cadena completa del Ciclo Cogito
(Fase 10, tarea 10.5; spec ciclo-cogito, Requirements 'Fases secuenciales
bloqueantes' y 'Modos y roles por fase').

Usa `MockProvider` (sin red) y `.ErickFP/` sobre `tmp_path`. Cubre: cadena
`duda -> divide -> ordena -> enumera` completa, modo automatico (nunca pausa),
modo interactivo (pausa y puede detenerse), `duda` ambigua (detiene la
cadena sin escribir nada), y el cableado real de `HookManager` en
`PhaseStart` (Decision 3 del design: `adr_traceability` bloquea `ordena` si
`divide.md` no referencia un ADR trazable).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from erickfp.api.types import Block, Response
from erickfp.cogito.orchestrator import CicloCogitoOrchestrator, PhaseBlockedError
from erickfp.hooks.adr_traceability import AdrTraceabilityHook
from erickfp.hooks.core_guard import CoreGuardHook
from erickfp.hooks.manager import HookManager
from erickfp.tools.registry import ToolRegistry
from tests.support import MockProvider

_ROLE_PROMPTS = {"planner": "Rol Planner.", "coder": "Rol Coder.", "reviewer": "Rol Reviewer."}


def _accepted_duda_response() -> Response:
    return Response(
        content=[Block(type="text", text="ACEPTADO: # duda.md\n\nObjetivo validado.")],
        stop_reason="end_turn",
    )


def _artifact_response(text: str) -> Response:
    return Response(content=[Block(type="text", text=text)], stop_reason="end_turn")


def _orchestrator(root: Path, provider: MockProvider, hook_manager: HookManager | None = None):
    return CicloCogitoOrchestrator(
        root=root,
        provider=provider,
        tools=ToolRegistry(),
        hook_manager=hook_manager if hook_manager is not None else HookManager(),
        role_prompts=_ROLE_PROMPTS,
    )


def test_full_chain_produces_all_four_artifacts(tmp_path: Path) -> None:
    root = tmp_path / ".ErickFP"
    provider = MockProvider(
        responses=[
            _accepted_duda_response(),
            _artifact_response("# divide.md\n\nPartes."),
            _artifact_response("# ordena.md\n\nSintesis."),
            _artifact_response("# enumera.md\n\nRevision."),
        ]
    )
    orchestrator = _orchestrator(root, provider)

    outcomes = orchestrator.run_chain("mi-slug", "objetivo claro", mode="automatico")

    assert [o.phase for o in outcomes] == ["duda", "divide", "ordena", "enumera"]
    assert all(o.status == "artifact" for o in outcomes)
    for phase in ("duda", "divide", "ordena", "enumera"):
        assert (root / "cogito" / "mi-slug" / f"{phase}.md").is_file()


def test_automatic_mode_never_calls_confirm(tmp_path: Path) -> None:
    root = tmp_path / ".ErickFP"
    provider = MockProvider(
        responses=[
            _accepted_duda_response(),
            _artifact_response("# divide.md\n\nPartes."),
            _artifact_response("# ordena.md\n\nSintesis."),
            _artifact_response("# enumera.md\n\nRevision."),
        ]
    )
    orchestrator = _orchestrator(root, provider)
    calls: list[str] = []

    orchestrator.run_chain(
        "mi-slug",
        "objetivo claro",
        mode="automatico",
        confirm=lambda phase: (calls.append(phase), True)[1],
    )

    assert calls == []


def test_interactive_mode_pauses_between_phases_and_stops_if_declined(tmp_path: Path) -> None:
    root = tmp_path / ".ErickFP"
    provider = MockProvider(
        responses=[
            _accepted_duda_response(),
            _artifact_response("# divide.md\n\nPartes."),
        ]
    )
    orchestrator = _orchestrator(root, provider)
    prompted_phases: list[str] = []

    def confirm(next_phase: str) -> bool:
        prompted_phases.append(next_phase)
        return next_phase != "ordena"  # el humano decide detenerse antes de 'ordena'

    outcomes = orchestrator.run_chain(
        "mi-slug", "objetivo claro", mode="interactivo", confirm=confirm
    )

    assert [o.phase for o in outcomes] == ["duda", "divide"]
    assert prompted_phases == ["divide", "ordena"]
    assert not (root / "cogito" / "mi-slug" / "ordena.md").exists()


def test_ambiguous_duda_halts_chain_without_writing_any_artifact(tmp_path: Path) -> None:
    root = tmp_path / ".ErickFP"
    provider = MockProvider(
        responses=[
            Response(
                content=[Block(type="text", text="AMBIGUO: falta contexto.")],
                stop_reason="end_turn",
            )
        ]
    )
    orchestrator = _orchestrator(root, provider)

    outcomes = orchestrator.run_chain("mi-slug", "objetivo confuso", mode="automatico")

    assert len(outcomes) == 1
    assert outcomes[0].status == "clarification"
    assert not (root / "cogito").exists()


def test_divide_blocked_cleanly_when_duda_artifact_missing(tmp_path: Path) -> None:
    from erickfp.cogito.artifacts import ArtifactMissingError
    from erickfp.hooks.manager import PhaseContext

    root = tmp_path / ".ErickFP"
    provider = MockProvider(responses=[])
    orchestrator = _orchestrator(root, provider)

    with pytest.raises(ArtifactMissingError) as exc_info:
        orchestrator.run_phase("divide", "mi-slug", PhaseContext(phase="divide"))

    assert exc_info.value.phase == "divide"


def test_ordena_blocked_by_adr_traceability_hook_when_divide_lacks_adr_ref(tmp_path: Path) -> None:
    root = tmp_path / ".ErickFP"
    (root / "adr").mkdir(parents=True)
    provider = MockProvider(
        responses=[
            _accepted_duda_response(),
            _artifact_response("# divide.md\n\nPartes sin adr_ref."),
        ]
    )
    hook_manager = HookManager([CoreGuardHook(root), AdrTraceabilityHook(root)])
    orchestrator = _orchestrator(root, provider, hook_manager)

    with pytest.raises(PhaseBlockedError) as exc_info:
        orchestrator.run_chain("mi-slug", "objetivo claro", mode="automatico")

    assert exc_info.value.phase == "ordena"
