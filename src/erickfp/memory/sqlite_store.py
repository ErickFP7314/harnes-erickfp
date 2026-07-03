"""memory/sqlite_store.py -- implementacion SQLite del Protocol Store
(Decision 6 del design; spec memory-store).

Un unico archivo `.ErickFP/memory/erickfp.db` con una tabla `entries`.
Trade-off documentado en el design: `recall` usa `LIKE` -- no escala a miles
de registros, pero es legible y sin dependencias extra para el MVP;
FTS5/embeddings quedan fuera de alcance (YAGNI).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from erickfp.api.types import Entry

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      TEXT NOT NULL,
    kind    TEXT NOT NULL CHECK(kind IN
              ('fact','decision','session-summary','preference')),
    content TEXT NOT NULL,
    tags    TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_entries_kind ON entries(kind);
"""

_PREAMBLE_SUMMARY_LIMIT = 3

_EntryRow = tuple[int, str, str, str, str]


class SqliteStore:
    """Store persistente en `<root>/memory/erickfp.db`.

    El esquema se crea (`CREATE TABLE IF NOT EXISTS`) al construir la
    instancia -- instanciar dos veces sobre el mismo `root` es idempotente y
    preserva los datos ya guardados.
    """

    def __init__(self, root: Path) -> None:
        db_dir = root / "memory"
        db_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = db_dir / "erickfp.db"
        self._init_schema()

    def _init_schema(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def save(self, entry: Entry) -> None:
        ts = entry.ts or datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                "INSERT INTO entries (ts, kind, content, tags) VALUES (?, ?, ?, ?)",
                (ts, entry.kind, entry.content, json.dumps(entry.tags)),
            )
            conn.commit()
        finally:
            conn.close()

    def recall(self, query: str, limit: int) -> list[Entry]:
        pattern = f"%{query}%"
        conn = sqlite3.connect(self._db_path)
        try:
            rows = conn.execute(
                "SELECT id, ts, kind, content, tags FROM entries "
                "WHERE content LIKE ? OR tags LIKE ? ORDER BY ts DESC LIMIT ?",
                (pattern, pattern, limit),
            ).fetchall()
        finally:
            conn.close()
        return [_row_to_entry(row) for row in rows]

    def preamble(self) -> str:
        """Concatena, como markdown estable: todas las entradas `fact`/
        `preference` (alto valor, bajo volumen) + las ultimas
        `_PREAMBLE_SUMMARY_LIMIT` `session-summary` (Decision 6)."""
        conn = sqlite3.connect(self._db_path)
        try:
            high_value_rows = conn.execute(
                "SELECT id, ts, kind, content, tags FROM entries "
                "WHERE kind IN ('fact', 'preference') ORDER BY ts ASC"
            ).fetchall()
            summary_rows = conn.execute(
                "SELECT id, ts, kind, content, tags FROM entries "
                "WHERE kind = 'session-summary' ORDER BY ts DESC LIMIT ?",
                (_PREAMBLE_SUMMARY_LIMIT,),
            ).fetchall()
        finally:
            conn.close()

        entries = [_row_to_entry(row) for row in high_value_rows]
        entries.extend(_row_to_entry(row) for row in reversed(summary_rows))
        if not entries:
            return ""
        return "\n".join(f"- ({entry.kind}) {entry.content}" for entry in entries)


def _row_to_entry(row: _EntryRow) -> Entry:
    entry_id, ts, kind, content, tags_json = row
    return Entry(
        id=entry_id,
        ts=ts,
        kind=kind,  # type: ignore[arg-type]
        content=content,
        tags=json.loads(tags_json),
    )
