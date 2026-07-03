"""tests/memory/test_sqlite_store.py -- SqliteStore (Fase 9, tareas 9.3-9.4).
Spec memory-store: `save` persiste en `.ErickFP/memory/erickfp.db`,
`recall(query, limit)` retorna coincidencias por `LIKE`, `preamble()`
concatena `fact`/`preference` + ultimas `session-summary`.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from erickfp.api.types import Entry
from erickfp.memory.sqlite_store import SqliteStore


def test_save_persists_entry_in_sqlite_file(tmp_path: Path) -> None:
    """Scenario 'Guardar una decision de sesion'."""
    root = tmp_path / ".ErickFP"
    store = SqliteStore(root=root)

    store.save(Entry(kind="fact", content="el usuario prefiere Python"))

    db_path = root / "memory" / "erickfp.db"
    assert db_path.is_file()

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT kind, content FROM entries").fetchall()
    finally:
        conn.close()
    assert rows == [("fact", "el usuario prefiere Python")]


def test_recall_matches_by_like_on_content_and_tags(tmp_path: Path) -> None:
    """Scenario 'Recall exitoso'."""
    store = SqliteStore(root=tmp_path / ".ErickFP")
    store.save(Entry(kind="decision", content="usar LiteLLM como adapter"))
    store.save(Entry(kind="decision", content="usar Typer para la CLI"))
    store.save(Entry(kind="fact", content="sin relacion textual", tags=["litellm"]))

    results = store.recall("LiteLLM", limit=10)

    contents = {entry.content for entry in results}
    assert "usar LiteLLM como adapter" in contents
    assert "sin relacion textual" in contents  # coincide por tag
    assert "usar Typer para la CLI" not in contents


def test_recall_respects_limit(tmp_path: Path) -> None:
    store = SqliteStore(root=tmp_path / ".ErickFP")
    for i in range(5):
        store.save(Entry(kind="fact", content=f"dato comun {i}"))

    results = store.recall("comun", limit=2)

    assert len(results) == 2


def test_preamble_concatenates_facts_preferences_and_latest_summaries(
    tmp_path: Path,
) -> None:
    """Scenario 'Preamble presente al iniciar sesion'."""
    store = SqliteStore(root=tmp_path / ".ErickFP")
    store.save(Entry(kind="fact", content="axioma: legibilidad primero"))
    store.save(Entry(kind="preference", content="tema cyan/verde"))
    store.save(Entry(kind="decision", content="decision irrelevante para el preamble"))
    store.save(Entry(kind="session-summary", content="resumen sesion 1"))
    store.save(Entry(kind="session-summary", content="resumen sesion 2"))

    preamble = store.preamble()

    assert "axioma: legibilidad primero" in preamble
    assert "tema cyan/verde" in preamble
    assert "resumen sesion 1" in preamble
    assert "resumen sesion 2" in preamble
    assert "decision irrelevante" not in preamble


def test_preamble_empty_when_no_entries(tmp_path: Path) -> None:
    store = SqliteStore(root=tmp_path / ".ErickFP")

    assert store.preamble() == ""


def test_schema_created_with_create_table_if_not_exists_is_idempotent(tmp_path: Path) -> None:
    """Instanciar `SqliteStore` dos veces sobre el mismo directorio no falla
    ni pierde datos previos (`CREATE TABLE IF NOT EXISTS`, Decision 6)."""
    root = tmp_path / ".ErickFP"
    SqliteStore(root=root).save(Entry(kind="fact", content="persistente"))

    second_store = SqliteStore(root=root)

    assert any(entry.content == "persistente" for entry in second_store.recall("persistente", 10))
