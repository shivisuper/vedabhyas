"""Tests for FTS5 search and fuzzy fallback."""
import sqlite3
import textwrap
from pathlib import Path

import pytest

from vedabhyas.data.db import connect
from vedabhyas.data.ingest import ingest
from vedabhyas.search.fts import search
from vedabhyas.search.fuzzy import search_fuzzy


_SAMPLE_TXT = textwrap.dedent("""\
    <L>1<pc>1,1<k1>Darma<k2>Darma<h>1<e>1
    <s>Darma</s> ¦ <lex>m.</lex> duty, law, virtue, right.
    <LEND>
    <L>2<pc>2,1<k1>arTa<k2>arTa<h>1<e>1
    <s>arTa</s> ¦ <lex>m.</lex> aim, purpose, wealth, meaning.
    <LEND>
    <L>3<pc>3,1<k1>kAma<k2>kAma<h>1<e>1
    <s>kAma</s> ¦ <lex>m.</lex> desire, wish, love.
    <LEND>
    <L>4<pc>4,1<k1>mokza<k2>mokza<h>1<e>1
    <s>mokza</s> ¦ <lex>m.</lex> liberation, release from saMsAra.
    <LEND>
""")


@pytest.fixture(scope="module")
def db(tmp_path_factory: pytest.TempPathFactory) -> sqlite3.Connection:
    tmp = tmp_path_factory.mktemp("db")
    txt = tmp / "mw.txt"
    txt.write_text(_SAMPLE_TXT, encoding="utf-8")
    conn = connect(tmp / "test.db")
    ingest(conn, mw_path=txt)
    return conn


def test_exact_match(db: sqlite3.Connection) -> None:
    results = search(db, "dharma")
    assert results
    assert results[0].headword_iast == "dharma"


def test_prefix_match(db: sqlite3.Connection) -> None:
    results = search(db, "dhar")
    assert any(r.headword_iast.startswith("dh") for r in results)


def test_source_dict_filter(db: sqlite3.Connection) -> None:
    results = search(db, "dharma", source_dict="mw")
    assert all(r.source_dict == "mw" for r in results)

    results_apte = search(db, "dharma", source_dict="apte")
    assert results_apte == []


def test_empty_query(db: sqlite3.Connection) -> None:
    assert search(db, "") == []
    assert search(db, "   ") == []


def test_fuzzy_finds_approximate(db: sqlite3.Connection) -> None:
    results = search_fuzzy(db, "dharm")
    headwords = [r.headword_iast for r in results]
    assert "dharma" in headwords


def test_result_has_required_fields(db: sqlite3.Connection) -> None:
    results = search(db, "artha")
    assert results
    r = results[0]
    assert r.id > 0
    assert r.headword_iast == "artha"
    assert r.source_dict == "mw"
