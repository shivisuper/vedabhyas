"""Tests for CDSL .txt ingestion and DB schema creation."""
import sqlite3
import textwrap
from pathlib import Path

import pytest

from vedabhyas.data.db import connect
from vedabhyas.data.ingest import ingest, iter_entries


# Minimal CDSL .txt format entries for testing
_SAMPLE_MW_TXT = textwrap.dedent("""\
    <L>1<pc>1,1<k1>Darma<k2>Darma<h>1<e>1
    <s>Darma</s> ¦ <lex>m.</lex> that which is established or firm; duty, law, virtue.
    <LEND>
    <L>2<pc>2,1<k1>arTa<k2>arTa<h>1<e>1
    <s>arTa</s> ¦ <lex>mfn.</lex> aim, purpose; meaning; wealth.<info lex="m:f:n"/>
    <LEND>
    <L>3<pc>3,1<k1>aMS<k2>aMS<h>1<e>1
    <s>aMS</s> ¦ <ab>cl.</ab> 10. <ab>P.</ab> to divide, distribute.<info verb="genuineroot" cp="10P,10Ā"/>
    <LEND>
""")


@pytest.fixture
def sample_txt(tmp_path: Path) -> Path:
    p = tmp_path / "mw.txt"
    p.write_text(_SAMPLE_MW_TXT, encoding="utf-8")
    return p


@pytest.fixture
def test_db(tmp_path: Path) -> sqlite3.Connection:
    return connect(tmp_path / "test.db")


def test_iter_entries_yields_records(sample_txt: Path) -> None:
    entries = list(iter_entries(sample_txt, "mw"))
    assert len(entries) == 3


def test_iter_entries_sets_source_dict(sample_txt: Path) -> None:
    for entry in iter_entries(sample_txt, "mw"):
        assert entry["source_dict"] == "mw"


def test_iter_entries_converts_slp1_to_iast(sample_txt: Path) -> None:
    entries = {e["headword_slp1"]: e for e in iter_entries(sample_txt, "mw")}
    # SLP1 "Darma" → IAST "dharma"
    assert entries["Darma"]["headword_iast"] == "dharma"
    # SLP1 "arTa" → IAST "artha"
    assert entries["arTa"]["headword_iast"] == "artha"


def test_ingest_creates_tables(sample_txt: Path, test_db: sqlite3.Connection) -> None:
    ingest(test_db, mw_path=sample_txt)
    count = test_db.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    assert count == 3


def test_ingest_gender_parsing(sample_txt: Path, test_db: sqlite3.Connection) -> None:
    ingest(test_db, mw_path=sample_txt)
    row = test_db.execute(
        "SELECT grammar_gender FROM entries WHERE headword_slp1 = 'Darma'"
    ).fetchone()
    assert row is not None
    assert row[0] == "m"


def test_ingest_gender_mfn(sample_txt: Path, test_db: sqlite3.Connection) -> None:
    ingest(test_db, mw_path=sample_txt)
    row = test_db.execute(
        "SELECT grammar_gender FROM entries WHERE headword_slp1 = 'arTa'"
    ).fetchone()
    assert row is not None
    assert row[0] == "m/f/n"


def test_ingest_verbal_class(sample_txt: Path, test_db: sqlite3.Connection) -> None:
    ingest(test_db, mw_path=sample_txt)
    row = test_db.execute(
        "SELECT grammar_class, grammar_pos FROM entries WHERE headword_slp1 = 'aMS'"
    ).fetchone()
    assert row is not None
    assert row[0] == "10"
    assert row[1] == "dhātu"


def test_ingest_fts_populated(sample_txt: Path, test_db: sqlite3.Connection) -> None:
    ingest(test_db, mw_path=sample_txt)
    rows = test_db.execute(
        'SELECT rowid FROM entries_fts WHERE entries_fts MATCH "dharma"'
    ).fetchall()
    assert len(rows) >= 1


def test_ingest_idempotent(sample_txt: Path, test_db: sqlite3.Connection) -> None:
    ingest(test_db, mw_path=sample_txt)
    ingest(test_db, mw_path=sample_txt)
    count = test_db.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
    assert count == 3
