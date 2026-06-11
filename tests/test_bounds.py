from __future__ import annotations

from datetime import date, datetime, time

from datepicker.bounds import (
    allowed_days,
    allowed_minutes,
    allowed_months,
    Bounds,
    date_allowed,
    minutes_locked,
    parse_days_of_month,
    parse_hour_list,
    parse_interval,
    parse_days_of_week,
    time_allowed,
)


def test_days_of_week_bounds() -> None:
    bounds = Bounds.days_of_week_only("mon", "wed", "fri")
    assert date_allowed(date(2025, 6, 9), bounds)
    assert not date_allowed(date(2025, 6, 10), bounds)


def test_days_of_month_bounds() -> None:
    bounds = Bounds.days_of_month_only(1, 15)
    assert date_allowed(date(2025, 6, 1), bounds)
    assert date_allowed(date(2025, 6, 15), bounds)
    assert not date_allowed(date(2025, 6, 10), bounds)


def test_hour_bounds() -> None:
    bounds = Bounds.hour_range(9, 17)
    on_date = date(2025, 6, 11)
    assert time_allowed(time(9, 0), bounds, on_date=on_date)
    assert not time_allowed(time(8, 59), bounds, on_date=on_date)


def test_minute_interval() -> None:
    bounds = parse_interval("15min")
    on_date = date(2025, 6, 11)
    assert allowed_minutes(10, bounds, on_date=on_date) == [0, 15, 30, 45]


def test_hour_interval_locks_minutes() -> None:
    bounds = parse_interval("2hr")
    assert minutes_locked(bounds)
    on_date = date(2025, 6, 11)
    assert allowed_minutes(10, bounds, on_date=on_date) == [0]


def test_fixed_datetime_bounds() -> None:
    bounds = Bounds(
        min=datetime(2025, 6, 1, 9, 0),
        max=datetime(2025, 6, 30, 17, 0),
    )
    assert allowed_months(2025, bounds) == [6]
    assert 1 in allowed_days(2025, 6, bounds)
    assert 11 in allowed_days(2025, 6, bounds)


def test_parse_helpers() -> None:
    assert parse_days_of_week("mon,wed") == frozenset({0, 2})
    assert parse_hour_list("9-11,15") == frozenset({9, 10, 11, 15})
    assert parse_days_of_month("1,15") == frozenset({1, 15})
