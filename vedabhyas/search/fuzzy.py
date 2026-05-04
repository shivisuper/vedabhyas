from __future__ import annotations

import sqlite3

from rapidfuzz import fuzz, process

from vedabhyas.search.fts import SearchResult
from vedabhyas.search.transliterate import to_slp1

_MIN_SCORE = 60
_CANDIDATE_LIMIT = 2000


def search_fuzzy(
    conn: sqlite3.Connection,
    query: str,
    source_dict: str | None = None,
    limit: int = 20,
) -> list[SearchResult]:
    """Fuzzy fallback using rapidfuzz WRatio on SLP1 headwords.

    Narrows candidates to entries sharing the first two SLP1 characters to keep
    the comparison set manageable (2000 max). Falls back to an unfiltered
    sample when the prefix produces no candidates.
    """
    if not query.strip():
        return []

    slp1 = to_slp1(query)
    prefix = slp1[:2] if len(slp1) >= 2 else slp1[:1]

    src_filter = "AND source_dict = ?" if source_dict else ""
    src_params: list = [source_dict] if source_dict else []

    def _fetch(where_clause: str, params: list) -> list[sqlite3.Row]:
        return conn.execute(
            f"""
            SELECT id, headword_iast, headword_devanagari, grammar_gender, grammar_pos,
                   grammar_class, root_dhatu_iast, meaning_short, source_dict, headword_slp1
            FROM entries
            WHERE {where_clause}
            {src_filter}
            LIMIT {_CANDIDATE_LIMIT}
            """,
            params + src_params,
        ).fetchall()

    rows = _fetch("headword_slp1 LIKE ?", [prefix + "%"])
    if not rows:
        rows = _fetch("1=1", [])

    if not rows:
        return []

    choices = {row["id"]: (row["headword_slp1"] or row["headword_iast"]) for row in rows}
    row_map = {row["id"]: row for row in rows}

    matches = process.extract(
        slp1, choices, scorer=fuzz.WRatio, limit=limit, score_cutoff=_MIN_SCORE
    )

    results = []
    for _val, score, entry_id in matches:
        row = row_map[entry_id]
        results.append(SearchResult(
            id=row["id"],
            headword_iast=row["headword_iast"],
            headword_devanagari=row["headword_devanagari"],
            grammar_gender=row["grammar_gender"],
            grammar_pos=row["grammar_pos"],
            grammar_class=row["grammar_class"],
            root_dhatu_iast=row["root_dhatu_iast"],
            meaning_short=row["meaning_short"],
            source_dict=row["source_dict"],
            rank=float(100 - score),
        ))

    return results
