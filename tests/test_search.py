"""Tests for FTS5 search and fuzzy fallback."""
import sqlite3
import textwrap
from pathlib import Path

import pytest

from vedabhyas.data.db import connect
from vedabhyas.data.ingest import ingest
from vedabhyas.search.fts import search
from vedabhyas.search.fuzzy import search_fuzzy


_SAMPLE_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <MW>
    <H1><h><key1>Darma</key1><key2>dharma</key2></h>
    <body><s>dharma</s> ¦ <ab>m.</ab> duty, law, virtue, right.</body>
    <tail><pc>1,1</pc></tail></H1>
    <H1><h><key1>arTa</key1><key2>artha</key2></h>
    <body><s>artha</s> ¦ <ab>m.</ab> aim, purpose, wealth, meaning.</body>
    <tail><pc>2,1</pc></tail></H1>
    <H1><h><key1>kAma</key1><key2>kāma</key2></h>
    <body><s>kāma</s> ¦ <ab>m.</ab> desire, wish, love.</body>
    <tail><pc>3,1</pc></tail></H1>
    <H1><h><key1>mOkza</key1><key2>mokṣa</key2></h>
    <body><s>mokṣa</s> ¦ <ab>m.</ab> liberation, release from saṃsāra.</body>
    <tail><pc>4,1</pc></tail></H1>
    </MW>
""")


@pytest.fixture(scope="module")
def db(tmp_path_factory: pytest.TempPathFactory) -> sqlite3.Connection:
    tmp = tmp_path_factory.mktemp("db")
    xml = tmp / "mw.xml"
    xml.write_text(_SAMPLE_XML, encoding="utf-8")
    conn = connect(tmp / "test.db")
    ingest(conn, mw_path=xml)
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


def test_empty_query(db: sqlite3.Connection) -> None:
    assert search(db, "") == []
    assert search(db, "   ") == []


def test_fuzzy_finds_approximate(db: sqlite3.Connection) -> None:
    # "dharm" should fuzzy-match "dharma"
    results = search_fuzzy(db, "dharm")
    headwords = [r.headword_iast for r in results]
    assert "dharma" in headwords


def test_result_has_required_fields(db: sqlite3.Connection) -> None:
    results = search(db, "artha")
    assert results
    r = results[0]
    assert r.id > 0
    assert r.headword_iast
    assert r.source_dict == "mw"
