from __future__ import annotations

import sqlite3

from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Footer, Input, Label, ListItem, ListView

from vedabhyas.search.fts import SearchResult, search
from vedabhyas.search.fuzzy import search_fuzzy


class SearchScreen(Screen):
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("q", "quit", "Quit", show=False),
        Binding("tab", "toggle_dict", "Toggle dict", show=True),
        Binding("enter", "select_result", "Open", show=True),
    ]

    CSS = """
    SearchScreen {
        layout: vertical;
    }

    #search-input {
        dock: top;
        height: 3;
        border: tall $accent;
    }

    #dict-badge {
        dock: top;
        height: 1;
        color: $text-muted;
        padding: 0 1;
    }

    #results-list {
        height: 1fr;
    }

    ListItem {
        padding: 0 1;
    }

    ListItem.--highlight {
        background: $accent 20%;
    }
    """

    def __init__(
        self,
        db: sqlite3.Connection,
        source_dict: str | None = None,
        show_devanagari: bool = False,
    ) -> None:
        super().__init__()
        self._db = db
        self._source_dict = source_dict
        self._show_devanagari = show_devanagari
        self._results: list[SearchResult] = []
        self._search_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        badge = self._dict_badge()
        yield Input(placeholder="Search: IAST, Harvard-Kyoto, ASCII, or Devanagari…", id="search-input")
        yield Label(badge, id="dict-badge")
        yield ListView(id="results-list")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    # ── Search input handling ──────────────────────────────────────────

    @on(Input.Changed, "#search-input")
    def _on_input_changed(self, event: Input.Changed) -> None:
        if self._search_timer is not None:
            self._search_timer.stop()
        query = event.value
        if not query.strip():
            self._update_results([])
            return
        self._search_timer = self.set_timer(0.15, lambda: self._run_search(query))

    def _run_search(self, query: str) -> None:
        results = search(self._db, query, self._source_dict)
        if not results:
            results = search_fuzzy(self._db, query, self._source_dict)
        self._results = results
        self._update_results(results)

    def _update_results(self, results: list[SearchResult]) -> None:
        lv = self.query_one("#results-list", ListView)
        lv.clear()
        for r in results:
            lv.append(ListItem(Label(self._format_result(r)), id=f"entry-{r.id}"))

    @staticmethod
    def _format_result(r: SearchResult) -> str:
        source_badge = f"[bold cyan]{r.source_dict.upper()}[/bold cyan]"
        grammar = " · ".join(p for p in [r.grammar_gender, r.grammar_pos] if p)
        line1 = f"[bold]{r.headword_iast}[/bold]  {source_badge}"
        if grammar:
            line1 += f"  [dim]{grammar}[/dim]"
        if r.meaning_short:
            snippet = r.meaning_short[:90]
            if len(r.meaning_short) > 90:
                snippet += "…"
            return f"{line1}\n  [italic dim]{snippet}[/italic dim]"
        return line1

    # ── Key navigation (vim-style when input not focused) ─────────────

    def on_key(self, event: events.Key) -> None:
        inp = self.query_one(Input)
        lv = self.query_one(ListView)
        if inp.has_focus:
            return
        if event.key in ("j", "down"):
            lv.action_cursor_down()
            event.stop()
        elif event.key in ("k", "up"):
            lv.action_cursor_up()
            event.stop()

    # ── Result selection ──────────────────────────────────────────────

    @on(ListView.Selected, "#results-list")
    def _on_result_selected(self, event: ListView.Selected) -> None:
        self._open_entry(event.item)

    def action_select_result(self) -> None:
        lv = self.query_one(ListView)
        if lv.highlighted_child is not None:
            self._open_entry(lv.highlighted_child)

    def _open_entry(self, item: ListItem) -> None:
        if item.id and item.id.startswith("entry-"):
            entry_id = int(item.id[6:])
            idx = next((i for i, r in enumerate(self._results) if r.id == entry_id), 0)
            from vedabhyas.tui.read_view import ReadScreen
            self.app.push_screen(
                ReadScreen(entry_id, self._results, idx, self._show_devanagari)
            )

    # ── Dict cycling ──────────────────────────────────────────────────

    def action_toggle_dict(self) -> None:
        cycle = [None, "mw", "apte"]
        try:
            idx = cycle.index(self._source_dict)
        except ValueError:
            idx = 0
        self._source_dict = cycle[(idx + 1) % len(cycle)]
        self.query_one("#dict-badge", Label).update(self._dict_badge())
        query = self.query_one(Input).value
        if query.strip():
            self._run_search(query)

    def _dict_badge(self) -> str:
        label = {None: "MW + Apte", "mw": "Monier-Williams only", "apte": "Apte only"}
        return f"[dim]Dict:[/dim] {label.get(self._source_dict, 'MW + Apte')}"

    def action_quit(self) -> None:
        self.app.exit()
