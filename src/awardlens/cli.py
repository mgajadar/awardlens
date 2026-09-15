"""Command-line interface for repeatable AwardLens workflows."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Annotated

import typer

from awardlens.analytics import summary_metrics
from awardlens.config import Settings
from awardlens.database import AwardRepository
from awardlens.pipeline import ingest_usaspending, load_demo
from awardlens.usaspending import AwardQuery, USAspendingClient

app = typer.Typer(
    no_args_is_help=True,
    help="Analyze federal procurement awards with a reproducible local data pipeline.",
)


def _repository(database: Path | None) -> AwardRepository:
    settings = Settings.from_env()
    return AwardRepository(database or settings.database_path)


def _parse_iso_date(value: str, option_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter("Use YYYY-MM-DD.", param_hint=option_name) from exc


@app.command()
def demo(
    database: Annotated[Path | None, typer.Option(help="DuckDB destination.")] = None,
) -> None:
    """Create a deterministic offline demonstration database."""

    result = load_demo(_repository(database))
    typer.echo(
        f"Loaded {result.received:,} synthetic awards; database now contains "
        f"{result.stored_total:,} records."
    )


@app.command()
def ingest(
    start: Annotated[str, typer.Option(help="Inclusive start date (YYYY-MM-DD).")],
    end: Annotated[str, typer.Option(help="Inclusive end date (YYYY-MM-DD).")],
    agency: Annotated[
        list[str] | None, typer.Option(help="Top-tier awarding agency; repeatable.")
    ] = None,
    max_pages: Annotated[
        int, typer.Option(min=1, max=100, help="Safety cap on API pages.")
    ] = 10,
    database: Annotated[Path | None, typer.Option(help="DuckDB destination.")] = None,
) -> None:
    """Fetch prime contract awards from the public USAspending API."""

    settings = Settings.from_env()
    client = USAspendingClient(
        base_url=settings.api_base_url,
        timeout_seconds=settings.request_timeout_seconds,
        max_retries=settings.max_retries,
    )
    query = AwardQuery(
        _parse_iso_date(start, "--start"),
        _parse_iso_date(end, "--end"),
        tuple(agency or ()),
        max_pages=max_pages,
    )
    result = ingest_usaspending(_repository(database), client, query)
    typer.echo(
        f"Received {result.received:,} API awards; database now contains "
        f"{result.stored_total:,} records."
    )


@app.command()
def summary(
    database: Annotated[Path | None, typer.Option(help="DuckDB source.")] = None,
) -> None:
    """Print headline metrics from the current database."""

    metrics = summary_metrics(_repository(database).load_awards())
    typer.echo(f"Awards: {metrics.award_count:,}")
    typer.echo(f"Total awarded: ${metrics.total_awarded:,.0f}")
    typer.echo(f"Median award: ${metrics.median_award:,.0f}")
    typer.echo(f"Vendors: {metrics.unique_vendors:,}")
    typer.echo(f"Agencies: {metrics.unique_agencies:,}")


@app.command()
def export(
    output: Annotated[Path, typer.Argument(help="CSV output path.")],
    database: Annotated[Path | None, typer.Option(help="DuckDB source.")] = None,
) -> None:
    """Export canonical records for downstream analysis."""

    destination = _repository(database).export_csv(output)
    typer.echo(f"Exported data to {destination}")


if __name__ == "__main__":
    app()
