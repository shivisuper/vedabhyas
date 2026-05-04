"""Tests for XML ingestion and DB schema creation."""
import sqlite3
import textwrap
from pathlib import Path

import pytest

from vedabhyas.data.db import connect
from vedabhyas.data.ingest import ingest, iter_entries


# Minimal well-formed CDSL XML for testing
_SAMPLE_MW_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <MW>
    <H1><h><key1>Darma</key1><key2>dharma</key2></h>
    <body><s>dharma</s> ¦ <ab>m.</ab> that which is established or firm; duty, law, virtue.</body>
    <tail><pc>1,1</pc></tail></H1>
    <H1><h><key1>arTa</key1><key2>artha</key2></h>
    <body><s>artha</s> ¦ <ab>m.</ab> <ab>n.</ab> aim, purpose; meaning; wealth.</body>
    <tail><pc>2,1</pc></tail></H1>
    </MW>
""")


@pytest.fixture
def sample_xml(tmp_path: Path) -> Path:
    p = tmp_path / "mw.xml"
    p.write_text(_SAMPLE_MW_XML, encoding="utf-8")
    return p


@pytest.fixture
def test_db(tmp_path: Path) -> sqlite3.Connection:
    return connect(tmp_path / "test.db")


def test_iter_entries_yields_records(sample_xml: Path) -> None:
    entries = list(iter_entries(sample_xml, "mw"))
    assert len(entries) == 2
    headwords = {e["headword_iast"] for e in entries}
    assert "dharma" in headwords
    assert "artha" in headwords


def test_iter_entries_sets_source_dict(sample_xml: Path) -> None:
    for entry in iter_entries(sample_xml, "mw"):
        assert entry["source_dict"] == "mw"


def test_ingest_creates_tables(sample_xml: Path, test_db: sqlite3.Connection) -> None:
    ingest(test_db, mw_path=sample_xml)
    count = test_db.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    assert count == 2


def test_ingest_gender_parsing(sample_xml: Path, test_db: sqlite3.Connection) -> None:
    ingest(test_db, mw_path=sample_xml)
    row = test_db.execute(
        "SELECT grammar_gender FROM entries WHERE headword_slp1 = 'Darma'"
    ).fetchone()
    assert row is not None
    assert row[0] == "m"


def test_ingest_fts_populated(sample_xml: Path, test_db: sqlite3.Connection) -> None:
    ingest(test_db, mw_path=sample_xml)
    rows = test_db.execute(
        "SELECT rowid FROM entries_fts WHERE entries_fts MATCH 'dharma'"
    ).fetchall()
    assert len(rows) >= 1


def test_ingest_idempotent(sample_xml: Path, test_db: sqlite3.Connection) -> None:
    ingest(test_db, mw_path=sample_xml)
    ingest(test_db, mw_path=sample_xml)
    count = test_db.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    assert count == 2
