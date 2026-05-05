from __future__ import annotations

from rich.markup import escape
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from vedabhyas.search.fts import SearchResult


class ReadScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back", show=True),
        Binding("n", "next_entry", "Next", show=True),
        Binding("p", "prev_entry", "Prev", show=True),
        Binding("y", "yank", "Copy headword", show=True),
    ]

    CSS = """
    ReadScreen {
        layout: vertical;
    }

    #entry-scroll {
        height: 1fr;
        padding: 1 2;
    }

    #entry-content {
        width: 100%;
    }
    """

    def __init__(
        self,
        entry_id: int,
        results: list[SearchResult],
        current_index: int,
        show_devanagari: bool = False,
    ) -> None:
        super().__init__()
        self._entry_id = entry_id
        self._results = results
        self._current_index = current_index
        self._show_devanagari = show_devanagari

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield ScrollableContainer(Static("", id="entry-content"), id="entry-scroll")
        yield Footer()

    def on_mount(self) -> None:
        self._load_entry(self._entry_id)

    def _load_entry(self, entry_id: int) -> None:
        from vedabhyas.data.db import get_entry
        entry = get_entry(self.app._db, entry_id)
        if entry:
            self.query_one("#entry-content", Static).update(self._format_entry(entry))

    def _format_entry(self, entry: dict) -> str:
        # All dynamic content is escape()d before insertion into Rich markup
        # to prevent CDSL source citations like [BhP.] from being parsed as tags
        hw     = escape(entry.get("headword_iast") or "")
        deva   = escape(entry.get("headword_devanagari") or "")
        source = (entry.get("source_dict") or "").upper()
        gender = escape(entry.get("grammar_gender") or "")
        pos    = escape(entry.get("grammar_pos") or "")
        cls    = escape(entry.get("grammar_class") or "")
        root   = escape(entry.get("root_dhatu_iast") or "")
        meaning    = escape(entry.get("meaning_full") or "")
        etymology  = escape(entry.get("etymology") or "")
        cross_refs = entry.get("cross_refs") or []

        lines: list[str] = []

        # Header
        header = f"[bold white]{hw}[/bold white]"
        if self._show_devanagari and deva:
            header += f"  [bold yellow]{deva}[/bold yellow]"
        header += f"  [bold cyan] {source} [/bold cyan]"
        lines.append(header)

        # Grammar line
        grammar_parts = []
        if root:
            grammar_parts.append(f"from √{root}")
        if gender:
            grammar_parts.append(f"{gender}.")
        if pos:
            grammar_parts.append(pos)
        if cls:
            grammar_parts.append(f"cl. {cls}")
        if grammar_parts:
            lines.append("[dim]" + " · ".join(grammar_parts) + "[/dim]")

        lines.append("[dim]" + "─" * 60 + "[/dim]")

        lines.append(meaning if meaning else "[dim](no definition)[/dim]")

        if etymology:
            lines.append("")
            lines.append(f"[italic dim]Etymology: {etymology}[/italic dim]")

        if cross_refs:
            refs_text = ", ".join(
                escape(r.get("to_headword_iast", ""))
                for r in cross_refs
                if r.get("to_headword_iast")
            )
            if refs_text:
                lines.append(f"[italic dim]See also: {refs_text}[/italic dim]")

        lines.append("")
        lines.append(f"[dim]── {self._current_index + 1}/{len(self._results)} ──[/dim]")

        return "\n".join(lines)

    # ── Actions ───────────────────────────────────────────────────────

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_next_entry(self) -> None:
        if self._current_index < len(self._results) - 1:
            self._current_index += 1
            r = self._results[self._current_index]
            self._entry_id = r.id
            self._load_entry(r.id)

    def action_prev_entry(self) -> None:
        if self._current_index > 0:
            self._current_index -= 1
            r = self._results[self._current_index]
            self._entry_id = r.id
            self._load_entry(r.id)

    def action_yank(self) -> None:
        try:
            import pyperclip
            from vedabhyas.data.db import get_entry
            entry = get_entry(self.app._db, self._entry_id)
            if entry:
                pyperclip.copy(entry.get("headword_iast", ""))
                self.notify("Headword copied to clipboard")
        except Exception as exc:
            self.notify(f"Copy failed: {exc}", severity="error")

    # j/k and arrow keys for scrolling
    def on_key(self, event: events.Key) -> None:
        scroll = self.query_one("#entry-scroll", ScrollableContainer)
        if event.key in ("j", "down"):
            scroll.scroll_down()
            event.stop()
        elif event.key in ("k", "up"):
            scroll.scroll_up()
            event.stop()
