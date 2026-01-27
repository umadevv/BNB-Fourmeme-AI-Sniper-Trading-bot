from __future__ import annotations

import asyncio

import typer

from .bot import run_bot
from .logging_utils import setup_logging
from .settings import load_settings

app = typer.Typer(add_completion=False, help="Polymarket copybot (paper by default).")


@app.command()
def run() -> None:
    """Run the copybot headless (CLI)."""
    settings = load_settings()
    setup_logging(settings.log_level)
    asyncio.run(run_bot(settings))


@app.command()
def gui() -> None:
    """Launch the PyQt GUI."""
    from .gui import run_gui

    run_gui()

