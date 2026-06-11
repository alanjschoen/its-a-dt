"""Compose multiple picker screens into date and datetime flows."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional, Union

from datepicker.bounds import Bounds, date_allowed, datetime_allowed
from datepicker.pick_day import pick_day
from datepicker.pick_month import pick_month
from datepicker.pick_time import pick_time
from datepicker.pick_year import pick_year
from datepicker.screen import GoBack


def pick_date(
    *,
    bounds: Optional[Bounds] = None,
    default: Optional[date] = None,
    title: str = "Select date",
) -> Union[date, type[GoBack]]:
    """Pick a date (year, month, day)."""
    effective_bounds = bounds or Bounds()
    default_dt = datetime.combine(default, time.min) if default else datetime.now()

    year_result = pick_year(
        bounds=effective_bounds,
        default=default_dt.year,
        title=title,
        allow_back=True,
    )
    if year_result is GoBack:
        return GoBack

    month_result = pick_month(
        year=year_result,
        bounds=effective_bounds,
        default=default_dt.month,
        title=title,
        allow_back=True,
    )
    if month_result is GoBack:
        return GoBack

    day_result = pick_day(
        year=year_result,
        month=month_result,
        bounds=effective_bounds,
        default=default_dt.day,
        title=title,
        allow_back=True,
    )
    if day_result is GoBack:
        return GoBack

    selected = date(year_result, month_result, day_result)
    if not date_allowed(selected, effective_bounds):
        raise RuntimeError("picker produced a value outside bounds")
    return selected


def pick_datetime(
    *,
    bounds: Optional[Bounds] = None,
    default: Optional[datetime] = None,
    title: str = "Select date and time",
) -> Union[datetime, type[GoBack]]:
    """Pick a datetime (year, month, day, hour, minute)."""
    effective_bounds = bounds or Bounds()
    default_dt = default if default is not None else datetime.now()

    year_result = pick_year(
        bounds=effective_bounds,
        default=default_dt.year,
        title=title,
        allow_back=True,
    )
    if year_result is GoBack:
        return GoBack

    month_result = pick_month(
        year=year_result,
        bounds=effective_bounds,
        default=default_dt.month,
        title=title,
        allow_back=True,
    )
    if month_result is GoBack:
        return GoBack

    day_result = pick_day(
        year=year_result,
        month=month_result,
        bounds=effective_bounds,
        default=default_dt.day,
        title=title,
        allow_back=True,
    )
    if day_result is GoBack:
        return GoBack

    selected_date = date(year_result, month_result, day_result)
    time_result = pick_time(
        bounds=effective_bounds,
        on_date=selected_date,
        default=default_dt.time(),
        title=title,
        allow_back=True,
    )
    if time_result is GoBack:
        return GoBack

    result = datetime.combine(selected_date, time_result)
    if not datetime_allowed(result, effective_bounds):
        raise RuntimeError("picker produced a value outside bounds")
    return result
