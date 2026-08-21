"""Command-line interface."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from .pipeline import run_pipeline

app = typer.Typer(help="Aurelia Bank AML Intelligence Control Tower")


@app.command()
def run(
    root: Annotated[Path, typer.Option(help="Repository root")] = Path("."),
    seed: Annotated[int, typer.Option(help="Deterministic demo seed")] = 20260821,
) -> None:
    """Generate data, execute monitoring and write all analytical outputs."""
    typer.echo(json.dumps(run_pipeline(root, seed=seed), indent=2, ensure_ascii=False))


@app.command()
def show(root: Annotated[Path, typer.Option(help="Repository root")] = Path(".")) -> None:
    """Print the current executive summary without rerunning the pipeline."""
    path = root / "artifacts" / "results" / "executive_summary.json"
    if not path.exists():
        raise typer.BadParameter("No executive summary found; run the pipeline first")
    typer.echo(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    app()
