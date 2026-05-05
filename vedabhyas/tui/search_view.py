from __future__ import annotations

import sqlite3

from rich.markup import escape
from textual import events, on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Footer, Input, Label, ListItem, ListView
from textual.worker import get_current_worker

from vedabhyas.search.fts import SearchResult, search
from vedabhyas.search.fuzzy import search_fuzzy


class SearchScreen(Screen):
    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
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
        yield Input(placeholder="Search: IAST, Harvard-Kyoto, ASCII, or Devanagari…", id="search-input")
        yield Label(self._dict_badge(), id="dict-badge")
        yield ListView(id="results-list")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_unmount(self) -> None:
        if self._search_timer is not None:
            self._search_timer.stop()
            self._search_timer = None
        self.workers.cancel_all()

    # ── Search input handling ──────────────────────────────────────────

    @on(Input.Changed, "#search-input")
    def _on_input_changed(self, event: Input.Changed) -> None:
        if self._search_timer is not None:
            self._search_timer.stop()
        query = event.value
        if not query.strip():
            self._update_results([])
            return
        self._search_timer = self.set_timer(
            0.15, lambda: self._run_search(query))

    @work(thread=True)
    def _run_search(self, query: str) -> None:
        worker = get_current_worker()
        from vedabhyas.data.db import connect
        conn = connect()
        try:
            results = search(conn, query, self._source_dict)
            if not results:
                results = search_fuzzy(conn, query, self._source_dict)
        finally:
            conn.close()
        if not worker.is_cancelled:
            self.app.call_from_thread(self._update_results, results)

    def _update_results(self, results: list[SearchResult]) -> None:
        self._results = results
        lv = self.query_one("#results-list", ListView)
        lv.clear()
        for r in results:
            lv.append(ListItem(Label(self._format_result(r))))

    @staticmethod
    def _format_result(r: SearchResult) -> str:
        # escape() prevents CDSL source citations like [BhP.] from being
        # misread as Rich markup tags
        source_badge = f"[bold cyan]{r.source_dict.upper()}[/bold cyan]"
        grammar = " · ".join(p for p in [r.grammar_gender, r.grammar_pos] if p)
        line1 = f"[bold]{escape(r.headword_iast)}[/bold]  {source_badge}"
        if grammar:
            line1 += f"  [dim]{escape(grammar)}[/dim]"
        if r.meaning_short:
            snippet = escape(r.meaning_short[:90])
            if len(r.meaning_short) > 90:
                snippet += "…"
            return f"{line1}\n  [italic dim]{snippet}[/italic dim]"
        return line1

    # ── Key navigation ────────────────────────────────────────────────
    # down/up: Input does not consume these, so they bubble to Screen.
    #          Handle them here only when Input has focus (ListView handles
    #          them natively via its own BINDINGS when it has focus, so they
    #          never reach Screen in that case).
    # j/k:     Input DOES consume j/k (types the char), so Screen only sees
    #          them when Input is NOT focused — no guard needed beyond that.

    def on_key(self, event: events.Key) -> None:
        lv = self.query_one(ListView)
        inp = self.query_one(Input)

        if event.key == "down" and inp.has_focus:
            lv.action_cursor_down()
            event.stop()
        elif event.key == "up" and inp.has_focus:
            lv.action_cursor_up()
            event.stop()
        elif event.key == "j" and not inp.has_focus:
            lv.action_cursor_down()
            event.stop()
        elif event.key == "k" and not inp.has_focus:
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
        lv = self.query_one(ListView)
        idx = lv.index
        if idx is not None and 0 <= idx < len(self._results):
            r = self._results[idx]
            from vedabhyas.tui.read_view import ReadScreen
            self.app.push_screen(
                ReadScreen(r.id, self._results, idx, self._show_devanagari)
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
        label = {None: "MW + Apte",
                 "mw": "Monier-Williams only", "apte": "Apte only"}
        return f"[dim]Dict:[/dim] {label.get(self._source_dict, 'MW + Apte')}"

    def action_quit(self) -> None:
        self.app.exit()
