from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY,
    headword_iast TEXT NOT NULL,
    headword_devanagari TEXT,
    headword_slp1 TEXT,
    grammar_gender TEXT,
    grammar_pos TEXT,
    grammar_class TEXT,
    root_dhatu TEXT,
    root_dhatu_iast TEXT,
    meaning_short TEXT,
    meaning_full TEXT,
    etymology TEXT,
    compound_indicator INTEGER DEFAULT 0,
    source_dict TEXT NOT NULL,
    source_entry_id TEXT
);

CREATE TABLE IF NOT EXISTS cross_refs (
    id INTEGER PRIMARY KEY,
    from_entry_id INTEGER REFERENCES entries(id),
    to_headword_iast TEXT,
    ref_type TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
    headword_iast,
    headword_slp1,
    meaning_short,
    meaning_full,
    root_dhatu_iast,
    content='entries',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts(rowid, headword_iast, headword_slp1, meaning_short, meaning_full, root_dhatu_iast)
    VALUES (new.id, new.headword_iast, new.headword_slp1, new.meaning_short, new.meaning_full, new.root_dhatu_iast);
END;
"""


def _db_path() -> Path:
    env = os.environ.get("VEDABHYAS_DB")
    if env:
        return Path(env)
    return Path.home() / ".local" / "share" / "vedabhyas" / "vedabhyas.db"


def db_exists() -> bool:
    return _db_path().exists()


def connect(path: Path | None = None) -> sqlite3.Connection:
    if path is None:
        path = _db_path()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_SCHEMA)
    return conn
