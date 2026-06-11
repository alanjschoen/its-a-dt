"""Demo CLI for exercising its-a-dt interactively."""

from __future__ import annotations

import sys
from datetime import date, datetime, time
from typing import Optional, Union

import typer

from its_a_dt.bounds import (
    Bounds,
    parse_days_of_month,
    parse_hour_list,
    parse_interval,
    parse_days_of_week,
)
from its_a_dt.compose import pick_date, pick_datetime
from its_a_dt.pick_day import pick_day
from its_a_dt.pick_month import pick_month
from its_a_dt.pick_time import pick_time
from its_a_dt.pick_year import pick_year
from its_a_dt.screen import Cancelled, GoBack

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    help="Interactive date and time picker demo.",
)


def _require_tty() -> None:
    if not sys.stdin.isatty():
        typer.echo("its-a-dt requires an interactive terminal.", err=True)
        raise typer.Exit(code=1)


def _parse_bound(value: Optional[str], *, end_of_day: bool = False) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        parsed = date.fromisoformat(value)
        return datetime.combine(parsed, time.max if end_of_day else time.min)


def _parse_date(value: Optional[str]) -> Optional[date]:
    if value is None:
        return None
    return date.fromisoformat(value)


def _parse_time(value: Optional[str]) -> Optional[time]:
    if value is None:
        return None
    return time.fromisoformat(value)


def _range_bounds(
    min_value: Optional[str],
    max_value: Optional[str],
) -> Bounds:
    return Bounds(
        min=_parse_bound(min_value),
        max=_parse_bound(max_value, end_of_day=True),
    )


def _day_bounds(
    min_value: Optional[str],
    max_value: Optional[str],
    days_of_week: Optional[str],
    days_of_month: Optional[str],
) -> Bounds:
    base = _range_bounds(min_value, max_value)
    return Bounds(
        min=base.min,
        max=base.max,
        days_of_week=parse_days_of_week(days_of_week) if days_of_week else None,
        days_of_month=parse_days_of_month(days_of_month) if days_of_month else None,
    )


def _time_bounds(
    min_value: Optional[str],
    max_value: Optional[str],
    hours: Optional[str],
    interval: Optional[str],
) -> Bounds:
    base = _range_bounds(min_value, max_value)
    interval_bounds = parse_interval(interval) if interval else Bounds()
    return Bounds(
        min=base.min,
        max=base.max,
        hours=parse_hour_list(hours) if hours else interval_bounds.hours,
        minute_step=interval_bounds.minute_step,
        hour_step_minutes=interval_bounds.hour_step_minutes,
    )


def _datetime_bounds(
    min_value: Optional[str],
    max_value: Optional[str],
    days_of_week: Optional[str],
    days_of_month: Optional[str],
    hours: Optional[str],
    interval: Optional[str],
) -> Bounds:
    day = _day_bounds(min_value, max_value, days_of_week, days_of_month)
    time_part = _time_bounds(min_value, max_value, hours, interval)
    return Bounds(
        min=day.min,
        max=day.max,
        days_of_week=day.days_of_week,
        days_of_month=day.days_of_month,
        hours=time_part.hours,
        minute_step=time_part.minute_step,
        hour_step_minutes=time_part.hour_step_minutes,
    )


def _run(result: Union[date, time, datetime, int, type[GoBack]]) -> None:
    if result is GoBack:
        typer.echo("Cancelled.", err=True)
        raise typer.Exit(code=1)
    if isinstance(result, datetime):
        typer.echo(result.isoformat(sep=" ", timespec="minutes"))
    elif isinstance(result, time):
        typer.echo(result.isoformat(timespec="minutes"))
    elif isinstance(result, int):
        typer.echo(str(result))
    else:
        typer.echo(result.isoformat())


def _handle_cancelled(fn) -> None:
    try:
        _run(fn())
    except Cancelled:
        raise typer.Exit(code=1) from None


def _run_datetime(
    *,
    min_value: Optional[str],
    max_value: Optional[str],
    days_of_week: Optional[str],
    days_of_month: Optional[str],
    hours: Optional[str],
    interval: Optional[str],
    default: Optional[str],
) -> None:
    bounds = _datetime_bounds(
        min_value, max_value, days_of_week, days_of_month, hours, interval
    )
    _handle_cancelled(lambda: pick_datetime(bounds=bounds, default=_parse_bound(default)))


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    min_value: Optional[str] = typer.Option(None, "--min"),
    max_value: Optional[str] = typer.Option(None, "--max"),
    days_of_week: Optional[str] = typer.Option(None, "--days-of-week"),
    days_of_month: Optional[str] = typer.Option(None, "--days-of-month"),
    hours: Optional[str] = typer.Option(None, "--hours"),
    interval: Optional[str] = typer.Option(None, "--interval"),
    default: Optional[str] = typer.Option(None, "--default", "-d"),
) -> None:
    """Run the full datetime picker when no subcommand is given."""
    if ctx.invoked_subcommand is not None:
        return
    _require_tty()
    _run_datetime(
        min_value=min_value,
        max_value=max_value,
        days_of_week=days_of_week,
        days_of_month=days_of_month,
        hours=hours,
        interval=interval,
        default=default,
    )


@app.command()
def year(
    min_value: Optional[str] = typer.Option(None, "--min"),
    max_value: Optional[str] = typer.Option(None, "--max"),
    default: Optional[str] = typer.Option(None, "--default", "-d"),
) -> None:
    """Pick a year."""
    _require_tty()
    bounds = _range_bounds(min_value, max_value)
    default_year = int(default) if default else None
    _handle_cancelled(
        lambda: pick_year(bounds=bounds, default=default_year, allow_back=False)
    )


@app.command()
def month(
    year: Optional[int] = typer.Option(None, "--year", "-y"),
    min_value: Optional[str] = typer.Option(None, "--min"),
    max_value: Optional[str] = typer.Option(None, "--max"),
    default: Optional[str] = typer.Option(None, "--default", "-d"),
) -> None:
    """Pick a month."""
    _require_tty()
    bounds = _range_bounds(min_value, max_value)
    default_month = int(default) if default else None
    _handle_cancelled(
        lambda: pick_month(
            year=year,
            bounds=bounds if year is not None else None,
            default=default_month,
            allow_back=False,
        )
    )


@app.command()
def day(
    year: int = typer.Option(..., "--year", "-y"),
    month: int = typer.Option(..., "--month", "-m"),
    min_value: Optional[str] = typer.Option(None, "--min"),
    max_value: Optional[str] = typer.Option(None, "--max"),
    days_of_week: Optional[str] = typer.Option(None, "--days-of-week"),
    days_of_month: Optional[str] = typer.Option(None, "--days-of-month"),
    default: Optional[str] = typer.Option(None, "--default", "-d"),
) -> None:
    """Pick a day."""
    _require_tty()
    bounds = _day_bounds(min_value, max_value, days_of_week, days_of_month)
    default_day = int(default) if default else None
    _handle_cancelled(
        lambda: pick_day(
            year=year,
            month=month,
            bounds=bounds,
            default=default_day,
            allow_back=False,
        )
    )


@app.command("time")
def time_cmd(
    on_date: Optional[str] = typer.Option(None, "--date"),
    min_value: Optional[str] = typer.Option(None, "--min"),
    max_value: Optional[str] = typer.Option(None, "--max"),
    hours: Optional[str] = typer.Option(None, "--hours"),
    interval: Optional[str] = typer.Option(
        None,
        "--interval",
        help="Minute/hour step: 15min, 30min, 1hr, 2hr, ...",
    ),
    default: Optional[str] = typer.Option(None, "--default", "-d"),
) -> None:
    """Pick a time."""
    _require_tty()
    bounds = _time_bounds(min_value, max_value, hours, interval)
    _handle_cancelled(
        lambda: pick_time(
            bounds=bounds,
            on_date=_parse_date(on_date),
            default=_parse_time(default),
            allow_back=False,
        )
    )


@app.command("date")
def date_cmd(
    min_value: Optional[str] = typer.Option(None, "--min"),
    max_value: Optional[str] = typer.Option(None, "--max"),
    days_of_week: Optional[str] = typer.Option(None, "--days-of-week"),
    days_of_month: Optional[str] = typer.Option(None, "--days-of-month"),
    default: Optional[str] = typer.Option(None, "--default", "-d"),
) -> None:
    """Pick a full date (year, month, day)."""
    _require_tty()
    bounds = _day_bounds(min_value, max_value, days_of_week, days_of_month)
    _handle_cancelled(lambda: pick_date(bounds=bounds, default=_parse_date(default)))


@app.command("datetime")
def datetime_picker(
    min_value: Optional[str] = typer.Option(None, "--min"),
    max_value: Optional[str] = typer.Option(None, "--max"),
    days_of_week: Optional[str] = typer.Option(None, "--days-of-week"),
    days_of_month: Optional[str] = typer.Option(None, "--days-of-month"),
    hours: Optional[str] = typer.Option(None, "--hours"),
    interval: Optional[str] = typer.Option(None, "--interval"),
    default: Optional[str] = typer.Option(None, "--default", "-d"),
) -> None:
    """Pick a full datetime."""
    _require_tty()
    _run_datetime(
        min_value=min_value,
        max_value=max_value,
        days_of_week=days_of_week,
        days_of_month=days_of_month,
        hours=hours,
        interval=interval,
        default=default,
    )


def main_entry() -> None:
    app()


if __name__ == "__main__":
    main_entry()
