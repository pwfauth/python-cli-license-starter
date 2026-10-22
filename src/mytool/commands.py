"""Your tool's own commands. Replace ``run`` with the work people pay for

Wrap paid work in ``get_licensing().session()``. Inside the block the license is
valid and a heartbeat keeps checking it: revoke the key in the panel and the work
stops within one heartbeat, with exit code 3
"""

from __future__ import annotations

import time

import typer
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn

from . import config, ui
from .cli import app, friendly, get_licensing

TOOL = "Commands"


@app.command(rich_help_panel=TOOL)
@friendly
def run(steps: int = typer.Option(20, min=1, max=100_000, help="How many work steps to run")) -> None:
    """Do the tool's work. Needs an active license"""
    with get_licensing().session() as session:
        # Remote texts: change what the tool says without shipping a new version
        motd = session.text("motd")
        if motd:
            ui.notice(motd)

        # A user variable: a value kept on the server for this customer
        runs = session.bump_counter("runs")

        with Progress(SpinnerColumn(style=ui.ACCENT), TextColumn("[progress.description]{task.description}"),
                      BarColumn(complete_style=ui.ACCENT), TextColumn("{task.completed}/{task.total}"),
                      TimeRemainingColumn(), console=ui.console, transient=False) as progress:
            task = progress.add_task("Working", total=steps)
            for _ in range(steps):
                time.sleep(0.25)           # ← your real work goes here
                session.ensure_active()    # optional: stop between steps once the license ended
                progress.advance(task)

        done = f"Finished {steps} step{'s' if steps != 1 else ''}"
        if runs:
            done += f". This license has run {config.APP_NAME} {runs} time{'s' if runs != 1 else ''}"
        ui.ok(done)
