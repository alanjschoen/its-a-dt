"""Composable bounds for date and time selection."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Literal, Optional

WeekdayName = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

_WEEKDAY_NAMES: dict[WeekdayName, int] = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

_MONTH_NAMES: dict[str, int] = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


@dataclass(frozen=True)
class Bounds:
    """Limits which dates, datetimes, and times the user may select."""

    min: Optional[datetime] = None
    max: Optional[datetime] = None
    days_of_week: Optional[frozenset[int]] = None
    days_of_month: Optional[frozenset[int]] = None
    hours: Optional[frozenset[int]] = None
    minute_step: Optional[int] = None
    hour_step_minutes: Optional[int] = None

    @classmethod
    def from_dates(
        cls,
        *,
        min: Optional[date] = None,
        max: Optional[date] = None,
        days_of_week: Optional[frozenset[int]] = None,
        days_of_month: Optional[frozenset[int]] = None,
    ) -> Bounds:
        min_dt = datetime.combine(min, time.min) if min else None
        max_dt = datetime.combine(max, time.max) if max else None
        return cls(
            min=min_dt,
            max=max_dt,
            days_of_week=days_of_week,
            days_of_month=days_of_month,
        )

    @classmethod
    def days_of_week_only(cls, *names: WeekdayName) -> Bounds:
        return cls(days_of_week=frozenset(_WEEKDAY_NAMES[name] for name in names))

    @classmethod
    def days_of_month_only(cls, *days: int) -> Bounds:
        return cls(days_of_month=frozenset(days))

    @classmethod
    def hours_only(cls, *hours: int) -> Bounds:
        return cls(hours=frozenset(hours))

    @classmethod
    def hour_range(cls, start: int, end: int) -> Bounds:
        if start > end:
            raise ValueError("hour_range start must be <= end")
        return cls(hours=frozenset(range(start, end + 1)))

    @classmethod
    def minute_interval(cls, step: int) -> Bounds:
        if step <= 0 or step > 60 or 60 % step != 0:
            raise ValueError("minute_step must divide 60 evenly")
        return cls(minute_step=step)

    @classmethod
    def hour_interval(cls, hours: int) -> Bounds:
        if hours <= 0:
            raise ValueError("hour interval must be positive")
        return cls(hour_step_minutes=hours * 60)


def parse_days_of_week(text: str) -> frozenset[int]:
    names = [part.strip().lower() for part in text.split(",") if part.strip()]
    if not names:
        raise ValueError("expected at least one day-of-week name")
    unknown = [name for name in names if name not in _WEEKDAY_NAMES]
    if unknown:
        raise ValueError(f"unknown days of week: {', '.join(unknown)}")
    return frozenset(_WEEKDAY_NAMES[name] for name in names)


def parse_days_of_month(text: str) -> frozenset[int]:
    days: set[int] = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text.strip())
            end = int(end_text.strip())
            if start > end:
                raise ValueError(f"invalid day range: {part}")
            days.update(range(start, end + 1))
        else:
            days.add(int(part))
    if not days:
        raise ValueError("expected at least one day of month")
    invalid = [day for day in days if day < 1 or day > 31]
    if invalid:
        raise ValueError(f"days of month must be 1-31: {invalid}")
    return frozenset(days)


def parse_hour_list(text: str) -> frozenset[int]:
    hours: set[int] = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text.strip())
            end = int(end_text.strip())
            if start > end:
                raise ValueError(f"invalid hour range: {part}")
            hours.update(range(start, end + 1))
        else:
            hours.add(int(part))
    if not hours:
        raise ValueError("expected at least one hour")
    invalid = [hour for hour in hours if hour < 0 or hour > 23]
    if invalid:
        raise ValueError(f"hours must be 0-23: {invalid}")
    return frozenset(hours)


def parse_interval(text: str) -> Bounds:
    """Parse interval strings like 15min, 30min, 1hr, 2hr."""
    cleaned = text.strip().lower().replace(" ", "")
    if cleaned.endswith("min"):
        step = int(cleaned[:-3])
        return Bounds.minute_interval(step)
    if cleaned.endswith("hr"):
        hours = int(cleaned[:-2])
        return Bounds.hour_interval(hours)
    raise ValueError(f"unknown interval: {text!r} (use 15min, 30min, 1hr, 2hr, ...)")


def parse_month_text(text: str) -> Optional[int]:
    cleaned = text.strip().lower()
    if not cleaned:
        return None
    if cleaned.isdigit():
        month = int(cleaned)
        return month if 1 <= month <= 12 else None
    return _MONTH_NAMES.get(cleaned)


def unique_month_prefix(
    text: str,
    enabled: Optional[frozenset[int]] = None,
) -> Optional[int]:
    """Return the month when text uniquely identifies one month by prefix."""
    cleaned = text.strip().lower()
    if not cleaned:
        return None
    months = range(1, 13) if enabled is None else sorted(enabled)
    matches = [
        month for month in months if _month_matches_prefix(month, cleaned)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _month_matches_prefix(month: int, prefix: str) -> bool:
    if prefix.isdigit():
        return str(month).startswith(prefix)
    return any(
        name.startswith(prefix)
        for name, mapped_month in _MONTH_NAMES.items()
        if mapped_month == month
    )


def minutes_locked(bounds: Bounds) -> bool:
    return bounds.hour_step_minutes is not None and bounds.hour_step_minutes >= 60


def min_year(bounds: Bounds) -> int:
    if bounds.min is not None:
        return bounds.min.year
    return date.today().year - 50


def max_year(bounds: Bounds) -> int:
    if bounds.max is not None:
        return bounds.max.year
    return date.today().year + 10


def allowed_years(bounds: Bounds) -> list[int]:
    return list(range(min_year(bounds), max_year(bounds) + 1))


def date_allowed(value: date, bounds: Bounds) -> bool:
    if bounds.min is not None and value < bounds.min.date():
        return False
    if bounds.max is not None and value > bounds.max.date():
        return False
    if bounds.days_of_week is not None and value.weekday() not in bounds.days_of_week:
        return False
    if bounds.days_of_month is not None and value.day not in bounds.days_of_month:
        return False
    return True


def month_allowed(year: int, month: int, bounds: Bounds) -> bool:
    _, days_in_month = calendar.monthrange(year, month)
    return any(date_allowed(date(year, month, day), bounds) for day in range(1, days_in_month + 1))


def allowed_months(year: int, bounds: Bounds) -> list[int]:
    return [month for month in range(1, 13) if month_allowed(year, month, bounds)]


def allowed_days(year: int, month: int, bounds: Bounds) -> list[int]:
    _, days_in_month = calendar.monthrange(year, month)
    return [
        day
        for day in range(1, days_in_month + 1)
        if date_allowed(date(year, month, day), bounds)
    ]


def allowed_hours(bounds: Bounds) -> list[int]:
    if bounds.hours is not None:
        hours = sorted(bounds.hours)
    else:
        hours = list(range(24))
    if bounds.hour_step_minutes is not None and bounds.hour_step_minutes >= 60:
        step_hours = bounds.hour_step_minutes // 60
        hours = [hour for hour in hours if hour % step_hours == 0]
    return hours


def time_allowed(value: time, bounds: Bounds, *, on_date: date) -> bool:
    if bounds.hours is not None and value.hour not in bounds.hours:
        return False
    if bounds.hour_step_minutes is not None and bounds.hour_step_minutes >= 60:
        step_hours = bounds.hour_step_minutes // 60
        if value.hour % step_hours != 0:
            return False
        if value.minute != 0:
            return False
    if bounds.minute_step is not None and bounds.minute_step > 0:
        if value.minute % bounds.minute_step != 0:
            return False
    if bounds.min is not None:
        min_date = bounds.min.date()
        if on_date < min_date:
            return False
        if on_date == min_date and value < bounds.min.time():
            return False
    if bounds.max is not None:
        max_date = bounds.max.date()
        if on_date > max_date:
            return False
        if on_date == max_date and value > bounds.max.time():
            return False
    return True


def allowed_minutes(hour: int, bounds: Bounds, *, on_date: date) -> list[int]:
    if minutes_locked(bounds):
        return [0]
    if bounds.minute_step is not None and bounds.minute_step > 0:
        candidates = list(range(0, 60, bounds.minute_step))
    else:
        candidates = list(range(60))
    return [
        minute
        for minute in candidates
        if time_allowed(time(hour, minute), bounds, on_date=on_date)
    ]


def datetime_allowed(value: datetime, bounds: Bounds) -> bool:
    return date_allowed(value.date(), bounds) and time_allowed(
        value.time(), bounds, on_date=value.date()
    )
