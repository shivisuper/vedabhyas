from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from vedabhyas.search.transliterate import to_slp1


@dataclass
class SearchResult:
    id: int
    headword_iast: str
    headword_devanagari: str | None
    grammar_gender: str | None
    grammar_pos: str | None
    grammar_class: str | None
    root_dhatu_iast: str | None
    meaning_short: str | None
    source_dict: str
    rank: float = 0.0


def _escape_fts5(text: str) -> str:
    """Wrap text as an FTS5 phrase query, escaping internal quotes."""
    return '"' + text.replace('"', '""') + '"'


def _row_to_result(row: sqlite3.Row, rank: float) -> SearchResult:
    return SearchResult(
        id=row["id"],
        headword_iast=row["headword_iast"],
        headword_devanagari=row["headword_devanagari"],
        grammar_gender=row["grammar_gender"],
        grammar_pos=row["grammar_pos"],
        grammar_class=row["grammar_class"],
        root_dhatu_iast=row["root_dhatu_iast"],
        meaning_short=row["meaning_short"],
        source_dict=row["source_dict"],
        rank=rank,
    )


def search(
    conn: sqlite3.Connection,
    query: str,
    source_dict: str | None = None,
    limit: int = 50,
) -> list[SearchResult]:
    """FTS5 search with three-tier ranking: exact → prefix → full-text."""
    if not query.strip():
        return []

    slp1 = to_slp1(query)
    results: list[SearchResult] = []
    seen: set[int] = set()

    src_filter = "AND source_dict = ?" if source_dict else ""
    src_params: list = [source_dict] if source_dict else []

    # 1. Exact headword match
    exact_sql = f"""
        SELECT id, headword_iast, headword_devanagari, grammar_gender, grammar_pos,
               grammar_class, root_dhatu_iast, meaning_short, source_dict
        FROM entries
        WHERE (LOWER(headword_iast) = LOWER(?) OR headword_slp1 = ?)
        {src_filter}
        LIMIT ?
    """
    for row in conn.execute(exact_sql, [query, slp1] + src_params + [limit]):
        if row["id"] not in seen:
            seen.add(row["id"])
            results.append(_row_to_result(row, 0.0))

    # 2. Prefix match on headword
    if len(results) < limit:
        prefix_sql = f"""
            SELECT id, headword_iast, headword_devanagari, grammar_gender, grammar_pos,
                   grammar_class, root_dhatu_iast, meaning_short, source_dict
            FROM entries
            WHERE (headword_iast LIKE ? OR headword_slp1 LIKE ?)
            {src_filter}
            ORDER BY LENGTH(headword_iast)
            LIMIT ?
        """
        for row in conn.execute(
            prefix_sql,
            [query + "%", slp1 + "%"] + src_params + [limit - len(results)],
        ):
            if row["id"] not in seen:
                seen.add(row["id"])
                results.append(_row_to_result(row, 1.0))

    # 3. FTS5 full-text match (searches meaning text too)
    if len(results) < limit:
        fts_sql = f"""
            SELECT e.id, e.headword_iast, e.headword_devanagari, e.grammar_gender,
                   e.grammar_pos, e.grammar_class, e.root_dhatu_iast, e.meaning_short,
                   e.source_dict
            FROM entries_fts
            JOIN entries e ON entries_fts.rowid = e.id
            WHERE entries_fts MATCH ?
            {"AND e.source_dict = ?" if source_dict else ""}
            ORDER BY rank
            LIMIT ?
        """
        fts_params: list = [_escape_fts5(slp1)]
        if source_dict:
            fts_params.append(source_dict)
        fts_params.append(limit - len(results))

        try:
            for row in conn.execute(fts_sql, fts_params):
                if row["id"] not in seen:
                    seen.add(row["id"])
                    results.append(_row_to_result(row, 2.0))
        except sqlite3.OperationalError:
            pass

    return results
