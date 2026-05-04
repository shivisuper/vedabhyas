from __future__ import annotations

from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static
from textual.containers import ScrollableContainer

from vedabhyas.search.fts import SearchResult


class ReadScreen(Screen):
    BINDINGS = [
        Binding("escape", "go_back", "Back", show=True),
        Binding("n", "next_entry", "Next", show=True),
        Binding("p", "prev_entry", "Prev", show=True),
        Binding("y", "yank", "Copy headword", show=True),
        Binding("j,down", "scroll_down", "Down", show=False),
        Binding("k,up", "scroll_up", "Up", show=False),
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
        hw = entry.get("headword_iast") or ""
        deva = entry.get("headword_devanagari") or ""
        source = (entry.get("source_dict") or "").upper()
        gender = entry.get("grammar_gender") or ""
        pos = entry.get("grammar_pos") or ""
        cls = entry.get("grammar_class") or ""
        root = entry.get("root_dhatu_iast") or ""
        meaning = entry.get("meaning_full") or ""
        etymology = entry.get("etymology") or ""
        cross_refs = entry.get("cross_refs") or []

        lines: list[str] = []

        # Header: headword + optional Devanagari + source badge
        header = f"[bold white]{hw}[/bold white]"
        if self._show_devanagari and deva:
            header += f"  [bold yellow]{deva}[/bold yellow]"
        header += f"  [bold cyan on $surface-darken-1] {source} [/bold cyan on $surface-darken-1]"
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

        # Meaning body
        if meaning:
            lines.append(meaning)
        else:
            lines.append("[dim](no definition)[/dim]")

        # Etymology
        if etymology:
            lines.append("")
            lines.append(f"[italic dim]Etymology: {etymology}[/italic dim]")

        # Cross-references
        if cross_refs:
            refs_text = ", ".join(
                r.get("to_headword_iast", "") for r in cross_refs if r.get("to_headword_iast")
            )
            if refs_text:
                lines.append(f"[italic dim]See also: {refs_text}[/italic dim]")

        # Nav hint
        pos_info = f"{self._current_index + 1}/{len(self._results)}"
        lines.append("")
        lines.append(f"[dim]── {pos_info} ──[/dim]")

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

    def action_scroll_down(self) -> None:
        self.query_one("#entry-scroll", ScrollableContainer).scroll_down()

    def action_scroll_up(self) -> None:
        self.query_one("#entry-scroll", ScrollableContainer).scroll_up()

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

    # ── Keyboard passthrough for j/k ─────────────────────────────────

    def on_key(self, event: events.Key) -> None:
        if event.key in ("j", "down"):
            self.action_scroll_down()
            event.stop()
        elif event.key in ("k", "up"):
            self.action_scroll_up()
            event.stop()
