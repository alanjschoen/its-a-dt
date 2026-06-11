from __future__ import annotations

from datetime import date, datetime

from datepicker.bounds import Bounds
from datepicker.screen import list_focus_index


def test_list_focus_index_defaults_to_nearest() -> None:
    years = [2020, 2022, 2025, 2030]
    assert list_focus_index(years, 2024) == 2
    assert list_focus_index(years, 2025) == 2


def test_bounds_days_of_week_filter() -> None:
    bounds = Bounds.days_of_week_only("mon", "wed", "fri")
    assert bounds.days_of_week == frozenset({0, 2, 4})
