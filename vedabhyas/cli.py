from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    name="vedabhyas",
    add_completion=False,
    help="Sanskrit CLI dictionary — interactive TUI for MW and Apte.",
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    dict_filter: Optional[str] = typer.Option(
        None, "--dict", metavar="DICT",
        help="Restrict to 'mw' (Monier-Williams) or 'apte'.",
    ),
    script: Optional[str] = typer.Option(
        None, "--script", metavar="SCRIPT",
        help="Pass 'devanagari' to display Devanagari script.",
    ),
) -> None:
    """Launch the interactive TUI."""
    if ctx.invoked_subcommand is not None:
        return

    from vedabhyas.data.db import connect, db_exists

    if not db_exists():
        typer.echo(
            "No database found. Download dictionary data and run:\n\n"
            "  bash scripts/download_dicts.sh\n"
            "  vedabhyas ingest\n",
            err=True,
        )
        raise typer.Exit(1)

    if dict_filter and dict_filter not in ("mw", "apte"):
        typer.echo(f"Unknown dict '{dict_filter}'. Use 'mw' or 'apte'.", err=True)
        raise typer.Exit(1)

    conn = connect()
    show_devanagari = script == "devanagari"

    from vedabhyas.tui.app import VedabhyasApp
    VedabhyasApp(conn, source_dict=dict_filter, show_devanagari=show_devanagari).run()
    conn.close()


@app.command("ingest")
def ingest_cmd(
    mw: Optional[str] = typer.Option(
        None, "--mw", metavar="PATH",
        help="Path to Monier-Williams XML file.",
    ),
    apte: Optional[str] = typer.Option(
        None, "--apte", metavar="PATH",
        help="Path to Apte XML file.",
    ),
    verbose: bool = typer.Option(True, "--verbose/--quiet"),
) -> None:
    """Ingest dictionary XML files into the local SQLite database.

    If no paths are given, looks for mw.xml and apte.xml in
    ~/.local/share/vedabhyas/ (the default download location).
    """
    from vedabhyas.data.db import connect
    from vedabhyas.data.ingest import ingest

    data_dir = Path.home() / ".local" / "share" / "vedabhyas"

    mw_path: Optional[Path] = None
    if mw:
        mw_path = Path(mw)
    elif (data_dir / "mw.xml").exists():
        mw_path = data_dir / "mw.xml"

    apte_path: Optional[Path] = None
    if apte:
        apte_path = Path(apte)
    elif (data_dir / "apte.xml").exists():
        apte_path = data_dir / "apte.xml"

    if not mw_path and not apte_path:
        typer.echo(
            "No XML files found. Run  bash scripts/download_dicts.sh  first,\n"
            "or pass --mw / --apte with explicit paths.",
            err=True,
        )
        raise typer.Exit(1)

    for p in filter(None, [mw_path, apte_path]):
        if not p.exists():
            typer.echo(f"File not found: {p}", err=True)
            raise typer.Exit(1)

    conn = connect()
    try:
        ingest(conn, mw_path=mw_path, apte_path=apte_path, verbose=verbose)
    finally:
        conn.close()

    typer.echo("Ingestion complete.")
