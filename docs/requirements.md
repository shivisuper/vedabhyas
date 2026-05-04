# वेदाभ्यास (vedabhyas) — Requirements Brief

> A Sanskrit CLI dictionary and study tool. The name combines *veda* (knowledge) and *abhyāsa* (practice/repetition). This document captures all decisions made during brainstorming and serves as the implementation specification for Claude Code.

---

## 1. Project Overview

`vedabhyas` is an interactive terminal TUI for looking up Sanskrit words and phrases. MVP delivers fast, fuzzy, offline-first Sanskrit word lookup with rich definitions. Future iterations will expand toward contextual understanding, sandhi splitting, and corpus integration.

CLI command: `vedabhyas`

---

## 2. Language & Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python | Fast prototyping, `indic-transliteration` library available, `textual` TUI ecosystem |
| TUI framework | `textual` | Production-grade, actively maintained, supports vim keybindings |
| CLI entrypoint | `typer` | Clean, modern Python CLI library |
| Storage | SQLite with FTS5 | Fast offline full-text search, single file, no server |
| Transliteration | `indic-transliteration` | Handles IAST, Devanagari, SLP1, Harvard-Kyoto, Velthuis |
| Packaging | `pipx` | Clean isolated install for Python tools |
| Fuzzy matching | `rapidfuzz` | Fast Levenshtein/trigram matching |

---

## 3. Data Sources

### Primary
- **Monier-Williams Sanskrit-English Dictionary (MW)** from the Cologne Digital Sanskrit Dictionaries (CDSL) project
  - Format: XML (XDXF or native CDSL XML)
  - Source: `https://www.sanskrit-lexicon.uni-koeln.de/`
  - ~186,000 entries
  - License: Open access for research/personal use

### Secondary
- **Apte Sanskrit-English Dictionary** also from CDSL
  - Complementary coverage and style to MW
  - Same XML format pipeline

---

## 4. Data Pipeline

### 4.1 Ingestion Script

A one-time (re-runnable) ingestion script that:
1. Downloads or accepts local path to MW XML and Apte XML
2. Parses XML into structured records
3. Loads into SQLite with full schema (see Section 5)
4. Builds FTS5 virtual table index

The script should be idempotent — safe to re-run, will drop and rebuild tables.

### 4.2 Fields to Extract from MW XML

The MW XML is rich. **Extract all of the following even if MVP display doesn't surface all of them.** Do not discard data at parse time.

| Field | Description | MVP Display |
|---|---|---|
| `headword_iast` | Word in IAST transliteration | Yes |
| `headword_devanagari` | Word in Devanagari script | Stored, not displayed in MVP |
| `headword_slp1` | Word in SLP1 (for internal search normalization) | Internal only |
| `grammar_gender` | Grammatical gender (m./f./n.) | Yes |
| `grammar_pos` | Part of speech (noun, verb, indeclinable, etc.) | Yes |
| `grammar_class` | Verbal class (for dhātus) | Yes |
| `root_dhatu` | Root verb form (dhātu) | Yes |
| `root_dhatu_iast` | Root in IAST | Yes |
| `meaning_short` | Primary/brief meaning | Yes |
| `meaning_full` | Full definition text | Yes |
| `etymology` | Etymology markers/notes from MW | Stored, shown in Standard+ view |
| `cross_refs` | Cross-references to other entries | Stored, shown in Standard+ view |
| `compound_indicator` | Whether entry is a compound word | Stored, MVP2 |
| `source_dict` | Which dictionary (MW / Apte) | Yes |
| `source_entry_id` | Original entry ID from source XML | Internal |

### 4.3 SQLite Schema Design

```sql
-- Core entries table
CREATE TABLE entries (
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
    compound_indicator INTEGER DEFAULT 0,  -- boolean
    source_dict TEXT NOT NULL,             -- 'mw' | 'apte'
    source_entry_id TEXT
);

-- Cross-references (separate table, many-to-many)
CREATE TABLE cross_refs (
    id INTEGER PRIMARY KEY,
    from_entry_id INTEGER REFERENCES entries(id),
    to_headword_iast TEXT,
    ref_type TEXT   -- 'see_also' | 'compare' | 'derived_from'
);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE entries_fts USING fts5(
    headword_iast,
    headword_slp1,
    meaning_short,
    meaning_full,
    root_dhatu_iast,
    content='entries',
    content_rowid='id'
);

-- Trigger to keep FTS in sync
CREATE TRIGGER entries_ai AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts(rowid, headword_iast, headword_slp1, meaning_short, meaning_full, root_dhatu_iast)
    VALUES (new.id, new.headword_iast, new.headword_slp1, new.meaning_short, new.meaning_full, new.root_dhatu_iast);
END;
```

---

## 5. TUI Interaction Model

### 5.1 Modal Design — Two Modes

**Search Mode** (default on launch)
- Fullscreen interactive prompt at top
- Results list below, updating in real-time as user types
- `j` / `k` — move through results
- `Enter` — expand selected result into Read Mode
- `Tab` — cycle between MW and Apte results
- `Ctrl+C` or `q` — quit

**Read Mode** (after selecting a result)
- Full definition view occupying most of the screen
- `j` / `k` or arrow keys — scroll through definition
- `Esc` — return to Search Mode with query preserved
- `n` / `p` — next / previous result without going back to Search Mode
- `y` — yank (copy) headword to clipboard

### 5.2 Search Behaviour

- Real-time fuzzy search as user types (debounced ~150ms)
- Input is normalized via `indic-transliteration` before querying
  - User can type in IAST, Harvard-Kyoto, or simplified ASCII
  - e.g. typing `dharma` or `Dharma` or `dhArma` all resolve correctly
- FTS5 for primary lookup
- `rapidfuzz` trigram/Levenshtein fallback when FTS returns no results
- Results ranked: exact match → prefix match → fuzzy match

### 5.3 Search Flags (CLI launch options)

```
vedabhyas                    # Launch interactive TUI (default)
vedabhyas --dict mw          # Restrict to Monier-Williams only
vedabhyas --dict apte        # Restrict to Apte only
vedabhyas --script devanagari  # Show Devanagari in results (if terminal supports)
vedabhyas ingest             # Run data ingestion pipeline
vedabhyas ingest --mw path/to/mw.xml --apte path/to/apte.xml
```

---

## 6. Definition Display (Read Mode)

### MVP Standard View

```
┌─────────────────────────────────────────────────┐
│  dharma  [धर्म]               MW                │
│   dharman · m. · from √dhṛ                      │
├─────────────────────────────────────────────────┤
│  that which is established or firm, steadfast   │
│  decree, statute, ordinance, law; usage,        │
│  practice, customary observance; duty, right,   │
│  justice, virtue, morality, religion, religious │
│  merit, good works...                           │
│                                                 │
│  Etymology: from √dhṛ (to hold, maintain)      │
│  See also: dharmin, dharmika, adharma           │
└─────────────────────────────────────────────────┘
```

Fields shown in MVP:
- Headword (IAST)
- Devanagari (if `--script devanagari` flag passed)
- Source dictionary badge
- Grammar: root dhātu, gender, part of speech
- Full meaning text
- Etymology (if present in source)
- Cross-references (if present)

Fields stored but not displayed in MVP:
- `compound_indicator` (MVP2 — sandhi splitter)
- `headword_slp1` (internal search only)

---

## 7. Project Structure

```
vedabhyas/
├── vedabhyas/
│   ├── __init__.py
│   ├── cli.py              # typer entrypoint
│   ├── data/
│   │   ├── __init__.py
│   │   ├── ingest.py       # XML parsing + SQLite loading
│   │   ├── schema.sql      # SQL schema definitions
│   │   └── db.py           # DB connection + query helpers
│   ├── search/
│   │   ├── __init__.py
│   │   ├── fts.py          # FTS5 query logic
│   │   ├── fuzzy.py        # rapidfuzz fallback
│   │   └── transliterate.py # Input normalization via indic-transliteration
│   └── tui/
│       ├── __init__.py
│       ├── app.py          # Textual app root
│       ├── search_view.py  # Search Mode screen
│       └── read_view.py    # Read Mode screen
├── scripts/
│   └── download_dicts.sh   # Helper to fetch MW + Apte XML from CDSL
├── tests/
│   ├── test_ingest.py
│   ├── test_search.py
│   └── test_transliterate.py
├── pyproject.toml
├── README.md
└── .gitignore
```

---

## 8. Dependencies

```toml
[project]
name = "vedabhyas"
requires-python = ">=3.11"

dependencies = [
    "textual>=0.47.0",
    "typer>=0.9.0",
    "indic-transliteration>=2.3.0",
    "rapidfuzz>=3.0.0",
    "lxml>=4.9.0",          # XML parsing
    "pyperclip>=1.8.0",     # clipboard yank
]

[project.scripts]
vedabhyas = "vedabhyas.cli:app"
```

---

## 9. MVP Scope (What's In / What's Out)

### In MVP
- MW + Apte XML ingestion into SQLite with full rich schema
- FTS5 search with transliteration normalization
- Fuzzy fallback search
- Interactive TUI: Search Mode + Read Mode
- Vim keybindings (j/k navigation, Esc, q, y)
- Standard definition view (all fields except compound breakdown)
- `--dict` and `--script` launch flags
- `pipx`-installable packaging

### MVP2 (explicitly deferred, schema already supports)
- Sandhi splitter integration (INRIA Sanskrit Heritage or UoH segmenter)
- Compound word decomposition view
- Devanagari input (in addition to romanized)
- Root (dhātu) browser — navigate all words from a given root
- Semantic search via embeddings
- Usage examples from DCS corpus

---

## 10. Key Implementation Notes for Claude Code

1. **Parse richly, display selectively.** The ingestion script should extract every available field from the MW XML. Do not simplify the schema for MVP convenience — it will require full re-ingestion to fix later.

2. **FTS5 content table pattern.** Use the `content=` and `content_rowid=` FTS5 options so the FTS index references the main `entries` table rather than duplicating data. Triggers keep them in sync.

3. **Transliteration normalization happens at search time, not at ingest time.** Store headwords in IAST and SLP1 in the DB. Normalize user input to SLP1 before querying, as SLP1 is ASCII-safe and unambiguous.

4. **Textual app architecture.** Use `textual`'s Screen system — `SearchScreen` and `ReadScreen` as separate screens with `app.push_screen()` / `app.pop_screen()` for navigation. This maps naturally to the two-mode model.

5. **Debounce the search input.** FTS5 is fast but Textual's reactive system should debounce keystrokes (~150ms) before firing queries to avoid thrashing on fast typists.

6. **DB path.** Store the SQLite DB in `~/.local/share/vedabhyas/vedabhyas.db` following XDG conventions. Make the path configurable via env var `VEDABHYAS_DB`.

7. **Ingest is a subcommand, not automatic.** Users run `vedabhyas ingest` explicitly. The main `vedabhyas` command should check for DB existence and print a friendly error with instructions if it hasn't been run yet.
