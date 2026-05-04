from __future__ import annotations

import sqlite3

from textual.app import App, ComposeResult


class VedabhyasApp(App):
    TITLE = "vedabhyas — Sanskrit Dictionary"
    CSS = """
    Screen {
        background: $surface;
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

    def on_mount(self) -> None:
        from vedabhyas.tui.search_view import SearchScreen
        self.push_screen(SearchScreen(self._db, self._source_dict, self._show_devanagari))
