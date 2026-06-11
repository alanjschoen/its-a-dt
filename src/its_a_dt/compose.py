"""Compose multiple picker screens into date and datetime flows."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional, Union

from its_a_dt.bounds import Bounds, date_allowed, datetime_allowed
from its_a_dt.pick_day import pick_day
from its_a_dt.pick_month import pick_month
from its_a_dt.pick_time import pick_time
from its_a_dt.pick_year import pick_year
from its_a_dt.screen import GoBack


def pick_date(
    *,
    bounds: Optional[Bounds] = None,
    default: Optional[date] = None,
    title: str = "Select date",
    eager: bool = False,
) -> Union[date, type[GoBack]]:
    """Pick a date (year, month, day)."""
    effective_bounds = bounds or Bounds()
    default_dt = datetime.combine(default, time.min) if default else datetime.now()

    while True:
        year_result = pick_year(
            bounds=effective_bounds,
            default=default_dt.year,
            title=title,
            allow_back=True,
            eager=eager,
        )
        if year_result is GoBack:
            return GoBack

        while True:
            month_result = pick_month(
                year=year_result,
                bounds=effective_bounds,
                default=default_dt.month,
                title=title,
                allow_back=True,
                eager=eager,
            )
            if month_result is GoBack:
                break

            while True:
                day_result = pick_day(
                    year=year_result,
                    month=month_result,
                    bounds=effective_bounds,
                    default=default_dt.day,
                    title=title,
                    allow_back=True,
                    eager=eager,
                )
                if day_result is GoBack:
                    break

                selected = date(year_result, month_result, day_result)
                if not date_allowed(selected, effective_bounds):
                    raise RuntimeError("picker produced a value outside bounds")
                return selected


def pick_datetime(
    *,
    bounds: Optional[Bounds] = None,
    default: Optional[datetime] = None,
    title: str = "Select date and time",
    eager: bool = False,
) -> Union[datetime, type[GoBack]]:
    """Pick a datetime (year, month, day, hour, minute)."""
    effective_bounds = bounds or Bounds()
    default_dt = default if default is not None else datetime.now()

    while True:
        year_result = pick_year(
            bounds=effective_bounds,
            default=default_dt.year,
            title=title,
            allow_back=True,
            eager=eager,
        )
        if year_result is GoBack:
            return GoBack

        while True:
            month_result = pick_month(
                year=year_result,
                bounds=effective_bounds,
                default=default_dt.month,
                title=title,
                allow_back=True,
                eager=eager,
            )
            if month_result is GoBack:
                break

            while True:
                day_result = pick_day(
                    year=year_result,
                    month=month_result,
                    bounds=effective_bounds,
                    default=default_dt.day,
                    title=title,
                    allow_back=True,
                    eager=eager,
                )
                if day_result is GoBack:
                    break

                selected_date = date(year_result, month_result, day_result)
                while True:
                    time_result = pick_time(
                        bounds=effective_bounds,
                        on_date=selected_date,
                        default=default_dt.time(),
                        title=title,
                        allow_back=True,
                        eager=eager,
                    )
                    if time_result is GoBack:
                        break

                    result = datetime.combine(selected_date, time_result)
                    if not datetime_allowed(result, effective_bounds):
                        raise RuntimeError("picker produced a value outside bounds")
                    return result
