# vedabhyas

> *veda* (knowledge) + *abhyāsa* (practice) — a Sanskrit dictionary for the terminal.

Interactive TUI for looking up Sanskrit words offline. Searches the Monier-Williams (~186k entries) and Apte dictionaries with real-time fuzzy matching and transliteration support.

---

## Install

```sh
pipx install vedabhyas
```

Or from source:

```sh
git clone https://github.com/ss-labs/vedabhyas
cd vedabhyas
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Setup (one-time)

Download the dictionary XML files and ingest them into a local SQLite database:

```sh
bash scripts/download_dicts.sh
vedabhyas ingest
```

This takes a minute and stores `~/.local/share/vedabhyas/vedabhyas.db` (~200MB).

## Usage

```sh
vedabhyas                      # launch interactive TUI
vedabhyas --dict mw            # Monier-Williams only
vedabhyas --dict apte          # Apte only
vedabhyas --script devanagari  # show Devanagari in results
```

Type in IAST (`dharma`), Harvard-Kyoto (`dhArma`), plain ASCII, or Devanagari (`धर्म`) — all resolve correctly.

### Keybindings

| Key | Action |
|-----|--------|
| Type | Search |
| `j` / `k` | Navigate results |
| `Enter` | Open entry |
| `Tab` | Cycle MW / Apte / both |
| `Esc` | Back to search |
| `n` / `p` | Next / previous entry |
| `y` | Copy headword to clipboard |
| `q` | Quit |

## Data sources

- **Monier-Williams** — [Cologne Digital Sanskrit Dictionaries](https://www.sanskrit-lexicon.uni-koeln.de/) via [csl-orig](https://github.com/sanskrit-lexicon/csl-orig)
- **Apte (AP90)** — same source, complementary coverage

Open access for research and personal use.

## Development

```sh
pip install -e ".[dev]"
pytest
```
