"""tests/cli/test_chat_memory_wiring.py -- cableado de `SqliteStore` real en
`erickfp chat` (Fase 9, reemplazo de `_NullStore` documentado como TODO en la
Fase 7/Lote 3). Spec memory-store, Requirement 'Preamble de hechos de alto
valor': el preamble debe cargarse automaticamente al iniciar `chat`, ahora
desde el Store PERSISTENTE (no desde un store nulo).
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from erickfp.api.types import Entry
from erickfp.cli import app
from erickfp.memory.sqlite_store import SqliteStore

runner = CliRunner()


def test_chat_wires_sqlite_store_preamble_into_system_context(
    tmp_path: Path, monkeypatch
) -> None:
    """Un hecho guardado ANTES de iniciar la sesion (via `SqliteStore` real,
    no `_NullStore`) aparece en el `system_context` construido por `chat`."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    root = tmp_path / ".ErickFP"
    SqliteStore(root=root).save(
        Entry(kind="fact", content="AXIOMA-PERSISTIDO-DE-PRUEBA: no se pierde entre sesiones")
    )

    captured: dict[str, str] = {}

    def fake_run_chat_session(
        provider, tools, console, system_context, read_line=None, hook_manager=None, store=None
    ):
        # `hook_manager` (Lote 4, spec permission-policy): `chat()` ahora
        # inyecta un HookManager real con CoreGuardHook -- el stub solo
        # necesita aceptar el kwarg, no lo ejercita en este test.
        captured["system_context"] = system_context

    monkeypatch.setattr("erickfp.cli.run_chat_session", fake_run_chat_session)

    result = runner.invoke(app, ["chat"])

    assert result.exit_code == 0, result.output
    assert "AXIOMA-PERSISTIDO-DE-PRUEBA" in captured["system_context"]


def test_chat_reuses_the_same_db_across_two_sessions(tmp_path: Path, monkeypatch) -> None:
    """Lo guardado en una sesion de `chat` sigue disponible en la siguiente
    (persistencia real en `.ErickFP/memory/erickfp.db`, no un store en
    memoria del proceso)."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init"])

    root = tmp_path / ".ErickFP"
    SqliteStore(root=root).save(Entry(kind="preference", content="PREFERENCIA-DE-PRUEBA"))

    captured: list[str] = []

    def fake_run_chat_session(
        provider, tools, console, system_context, read_line=None, hook_manager=None, store=None
    ):
        captured.append(system_context)

    monkeypatch.setattr("erickfp.cli.run_chat_session", fake_run_chat_session)

    runner.invoke(app, ["chat"])
    runner.invoke(app, ["chat"])

    assert len(captured) == 2
    assert all("PREFERENCIA-DE-PRUEBA" in ctx for ctx in captured)
