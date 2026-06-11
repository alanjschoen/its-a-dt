"""Day picker screen."""

from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Optional, Union

from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings

from datepicker.bounds import Bounds, allowed_days, date_allowed
from datepicker.screen import (
    Cancelled,
    GoBack,
    ScreenState,
    append_grid_row,
    append_input_line,
    append_palette,
    bind_quit,
    bind_text_input,
    list_focus_index,
    run_screen,
)

_MONTH_LABELS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)
_WEEKDAY_LABELS = ("Su", "Mo", "Tu", "We", "Th", "Fr", "Sa")


def pick_day(
    *,
    year: int,
    month: int,
    bounds: Optional[Bounds] = None,
    default: Optional[int] = None,
    title: str = "Select day",
    allow_back: bool = True,
) -> Union[int, type[GoBack]]:
    """Pick a day of month within the given year and month."""
    effective_bounds = bounds or Bounds()
    default_day = default if default is not None else datetime.now().day
    enabled = allowed_days(year, month, effective_bounds)
    if not enabled:
        raise RuntimeError(f"no days available in {month}/{year} within bounds")

    weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)
    cells: list[tuple[int, int]] = []
    for week_index, week in enumerate(weeks):
        for weekday_index, day in enumerate(week):
            if day != 0:
                cells.append((week_index, weekday_index))
    enabled_cells = [(w, d) for w, d in cells if weeks[w][d] in enabled]

    selected: list[int] = [default_day]
    state = ScreenState(focus_index=list_focus_index(enabled, default_day))
    month_name = _MONTH_LABELS[month - 1]

    def render() -> FormattedText:
        lines: list[tuple[str, str]] = [
            ("class:title", f"{title}\n\n"),
            ("", f"{month_name} {year}\n\n"),
            ("class:hint", "  ".join(label.center(3) for label in _WEEKDAY_LABELS) + "\n"),
        ]
        selected_day = enabled[state.focus_index]
        for week in weeks:
            row_cells: list[tuple[str, str]] = []
            for day in week:
                if day == 0:
                    row_cells.append(("", "   "))
                elif day not in enabled:
                    row_cells.append(("class:disabled", f"{day:>3}"))
                elif day == selected_day:
                    row_cells.append(("class:focus", f"{day:>3}"))
                else:
                    row_cells.append(("", f"{day:>3}"))
            append_grid_row(lines, row_cells)
        append_input_line(lines, "Type day: ", state.text_input)
        back_hint = "⌫ back · " if allow_back else ""
        append_palette(
            lines,
            f"{back_hint}arrows navigate · Enter select · type day · q quit",
        )
        return FormattedText(lines)

    def bind_keys(kb: KeyBindings, screen: ScreenState) -> None:
        bind_text_input(kb, screen, back_on_empty=allow_back)
        bind_quit(kb, screen)

        @kb.add("up", eager=True)
        def _up(event) -> None:
            _move_day_focus(screen, enabled, enabled_cells, weeks, dy=-1)
            event.app.invalidate()

        @kb.add("down", eager=True)
        def _down(event) -> None:
            _move_day_focus(screen, enabled, enabled_cells, weeks, dy=1)
            event.app.invalidate()

        @kb.add("left", eager=True)
        def _left(event) -> None:
            _move_day_focus(screen, enabled, enabled_cells, weeks, dx=-1)
            event.app.invalidate()

        @kb.add("right", eager=True)
        def _right(event) -> None:
            _move_day_focus(screen, enabled, enabled_cells, weeks, dx=1)
            event.app.invalidate()

        @kb.add("enter", eager=True)
        def _enter(event) -> None:
            cleaned = screen.text_input.strip()
            if cleaned:
                parsed = _parse_day_text(cleaned, year, month, effective_bounds)
                if parsed is None:
                    screen.text_input = ""
                    event.app.invalidate()
                    return
                selected[0] = parsed
            else:
                selected[0] = enabled[screen.focus_index]
            event.app.exit()

    state = run_screen(state=state, render=render, bind_keys=bind_keys)
    if state.cancelled:
        raise Cancelled
    if state.go_back:
        return GoBack
    return selected[0]


def _parse_day_text(text: str, year: int, month: int, bounds: Bounds) -> Optional[int]:
    cleaned = text.strip()
    if not cleaned:
        return None
    if cleaned.isdigit():
        day = int(cleaned)
        candidate = date(year, month, day)
        if date_allowed(candidate, bounds):
            return day
        return None
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
        if parsed.year == year and parsed.month == month and date_allowed(parsed, bounds):
            return parsed.day
    return None


def _move_day_focus(
    screen: ScreenState,
    enabled: list[int],
    enabled_cells: list[tuple[int, int]],
    weeks: list[list[int]],
    *,
    dx: int = 0,
    dy: int = 0,
) -> None:
    if not enabled_cells:
        return
    selected_day = enabled[screen.focus_index]
    current_pos = next(
        cell for cell in enabled_cells if weeks[cell[0]][cell[1]] == selected_day
    )
    if dx:
        target_col = current_pos[1] + dx
        if target_col < 0 or target_col > 6:
            return
        for cell in enabled_cells:
            week_index, weekday_index = cell
            if week_index == current_pos[0] and weekday_index == target_col:
                day = weeks[week_index][weekday_index]
                screen.focus_index = enabled.index(day)
                return
        return
    if dy:
        target_row = current_pos[0] + dy
        if target_row < 0 or target_row >= len(weeks):
            return
        for cell in enabled_cells:
            week_index, weekday_index = cell
            if week_index == target_row and weekday_index == current_pos[1]:
                day = weeks[week_index][weekday_index]
                screen.focus_index = enabled.index(day)
                return
