"""Month picker screen."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings

from datepicker.bounds import Bounds, allowed_months, month_allowed, parse_month_text
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


def pick_month(
    *,
    year: Optional[int] = None,
    bounds: Optional[Bounds] = None,
    default: Optional[int] = None,
    title: str = "Select month",
    allow_back: bool = True,
) -> Union[int, type[GoBack]]:
    """Pick a month (1-12). Year is only used when applying date-range bounds."""
    effective_bounds = bounds or Bounds()
    default_month = default if default is not None else datetime.now().month
    if year is None:
        enabled = list(range(1, 13))
    else:
        enabled = allowed_months(year, effective_bounds)
        if not enabled:
            raise RuntimeError(f"no months available in {year} within bounds")

    selected: list[int] = [default_month]
    state = ScreenState(focus_index=list_focus_index(enabled, default_month))

    def render() -> FormattedText:
        lines: list[tuple[str, str]] = [("class:title", f"{title}\n\n")]
        if year is not None:
            lines.append(("", f"{year}\n\n"))
        else:
            lines.append(("", "\n"))
        focus = enabled[state.focus_index]
        for row in range(3):
            row_cells: list[tuple[str, str]] = []
            for col in range(4):
                month = row * 4 + col + 1
                label = _MONTH_LABELS[month - 1].center(5)
                if month not in enabled:
                    row_cells.append(("class:disabled", label))
                elif month == focus:
                    row_cells.append(("class:focus", label))
                else:
                    row_cells.append(("", label))
            append_grid_row(lines, row_cells)
        append_input_line(lines, "Type month: ", state.text_input)
        back_hint = "⌫ back · " if allow_back else ""
        append_palette(
            lines,
            f"{back_hint}arrows navigate · Enter select · type month · q quit",
        )
        return FormattedText(lines)

    def bind_keys(kb: KeyBindings, screen: ScreenState) -> None:
        bind_text_input(kb, screen, back_on_empty=allow_back)
        bind_quit(kb, screen)

        @kb.add("up", eager=True)
        def _up(event) -> None:
            _move_grid_focus(screen, enabled, dx=0, dy=-1, width=4)
            event.app.invalidate()

        @kb.add("down", eager=True)
        def _down(event) -> None:
            _move_grid_focus(screen, enabled, dx=0, dy=1, width=4)
            event.app.invalidate()

        @kb.add("left", eager=True)
        def _left(event) -> None:
            _move_grid_focus(screen, enabled, dx=-1, dy=0, width=4)
            event.app.invalidate()

        @kb.add("right", eager=True)
        def _right(event) -> None:
            _move_grid_focus(screen, enabled, dx=1, dy=0, width=4)
            event.app.invalidate()

        @kb.add("enter", eager=True)
        def _enter(event) -> None:
            cleaned = screen.text_input.strip()
            if cleaned:
                month = parse_month_text(cleaned)
                if month is None or month not in enabled:
                    screen.text_input = ""
                    event.app.invalidate()
                    return
                if year is not None and not month_allowed(year, month, effective_bounds):
                    screen.text_input = ""
                    event.app.invalidate()
                    return
                selected[0] = month
            else:
                selected[0] = enabled[screen.focus_index]
            event.app.exit()

    state = run_screen(state=state, render=render, bind_keys=bind_keys)
    if state.cancelled:
        raise Cancelled
    if state.go_back:
        return GoBack
    return selected[0]


def _move_grid_focus(
    screen: ScreenState,
    enabled: list[int],
    *,
    dx: int,
    dy: int,
    width: int,
) -> None:
    current = enabled[screen.focus_index]
    row = (current - 1) // width
    col = (current - 1) % width
    target_row = row + dy
    target_col = col + dx
    if target_row < 0 or target_row >= 3 or target_col < 0 or target_col >= width:
        return
    target_month = target_row * width + target_col + 1
    if target_month not in enabled:
        return
    screen.focus_index = enabled.index(target_month)
