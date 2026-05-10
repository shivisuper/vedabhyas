from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Iterator

from indic_transliteration import sanscript

from vedabhyas.data.db import _SCHEMA

_LEX_GENDER: dict[str, str] = {
    "m": "m",
    "f": "f",
    "n": "n",
    "mfn": "m/f/n",
    "mf(a)n": "m/f/n",
    "mf": "m/f",
    "fn": "f/n",
    "mn": "m/n",
}

_TAG_RE = re.compile(r"<[^>]+>")
_K1_RE = re.compile(r"<k1>([^<\s]+)")
_L_RE = re.compile(r"<L>(\S+)")
_LEX_RE = re.compile(r"<lex>([^<]+)</lex>")
_CL_RE = re.compile(r"<ab>cl\.</ab>\s*(\d+)")


def _strip_tags(text: str) -> str:
    return _TAG_RE.sub("", text)


def _slp1_to_iast(slp1: str) -> str:
    return sanscript.transliterate(slp1, sanscript.SLP1, sanscript.IAST)


def _slp1_to_devanagari(slp1: str) -> str:
    return sanscript.transliterate(slp1, sanscript.SLP1, sanscript.DEVANAGARI)


def _parse_entry(header: str, body: str, source_dict: str) -> dict:
    l_match = _L_RE.search(header)
    source_entry_id = l_match.group(1) if l_match else None

    k1_match = _K1_RE.search(header)
    headword_slp1 = k1_match.group(1) if k1_match else None

    grammar_gender: str | None = None
    grammar_pos: str | None = None
    grammar_class: str | None = None

    lex_match = _LEX_RE.search(body)
    if lex_match:
        lex_raw = lex_match.group(1).strip().rstrip(".")
        grammar_gender = _LEX_GENDER.get(lex_raw)
        if grammar_gender is None and lex_raw:
            grammar_pos = lex_raw

    cl_match = _CL_RE.search(body)
    if cl_match:
        grammar_class = cl_match.group(1)
        grammar_pos = "dhātu"
        grammar_gender = None

    meaning_full: str | None = None
    meaning_short: str | None = None
    if "¦" in body:
        after_sep = body.split("¦", 1)[1]
        clean = _strip_tags(after_sep).strip()
        meaning_full = clean
        short = re.split(r"[;.]", clean)[0].strip()
        meaning_short = short if short else clean[:80]

    headword_iast = _slp1_to_iast(headword_slp1) if headword_slp1 else None
    headword_devanagari = _slp1_to_devanagari(headword_slp1) if headword_slp1 else None

    return {
        "headword_iast": headword_iast,
        "headword_devanagari": headword_devanagari,
        "headword_slp1": headword_slp1,
        "grammar_gender": grammar_gender,
        "grammar_pos": grammar_pos,
        "grammar_class": grammar_class,
        "root_dhatu": None,
        "root_dhatu_iast": None,
        "meaning_short": meaning_short,
        "meaning_full": meaning_full,
        "etymology": None,
        "compound_indicator": 0,
        "source_dict": source_dict,
        "source_entry_id": source_entry_id,
    }


def iter_entries(path: Path, source_dict: str) -> Iterator[dict]:
    header: str | None = None
    body_lines: list[str] = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("<L>"):
                header = line
                body_lines = []
            elif line.startswith("<LEND>"):
                if header is not None:
                    yield _parse_entry(header, " ".join(body_lines), source_dict)
                header = None
                body_lines = []
            elif header is not None:
                body_lines.append(line)


def ingest(
    conn: sqlite3.Connection,
    mw_path: Path | None = None,
    apte_path: Path | None = None,
    verbose: bool = True,
) -> None:
    conn.executescript("""
        DROP TABLE IF EXISTS entries_fts;
        DROP TRIGGER IF EXISTS entries_ai;
        DROP TABLE IF EXISTS cross_refs;
        DROP TABLE IF EXISTS entries;
    """)
    conn.executescript(_SCHEMA)

    pairs = []
    if mw_path:
        pairs.append((Path(mw_path), "mw"))
    if apte_path:
        pairs.append((Path(apte_path), "apte"))

    for path, source in pairs:
        if verbose:
            print(f"Ingesting {source} from {path} …")
        conn.executemany(
            """
            INSERT INTO entries (
                headword_iast, headword_devanagari, headword_slp1,
                grammar_gender, grammar_pos, grammar_class,
                root_dhatu, root_dhatu_iast,
                meaning_short, meaning_full, etymology,
                compound_indicator, source_dict, source_entry_id
            ) VALUES (
                :headword_iast, :headword_devanagari, :headword_slp1,
                :grammar_gender, :grammar_pos, :grammar_class,
                :root_dhatu, :root_dhatu_iast,
                :meaning_short, :meaning_full, :etymology,
                :compound_indicator, :source_dict, :source_entry_id
            )
            """,
            iter_entries(path, source),
        )

    conn.commit()
