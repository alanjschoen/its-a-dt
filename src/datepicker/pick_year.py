"""Year picker screen."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings

from datepicker.bounds import Bounds, allowed_years
from datepicker.screen import (
    Cancelled,
    GoBack,
    ScreenState,
    append_input_line,
    append_palette,
    bind_quit,
    bind_text_input,
    list_focus_index,
    run_screen,
    visible_indices,
)


def pick_year(
    *,
    bounds: Optional[Bounds] = None,
    default: Optional[int] = None,
    title: str = "Select year",
    allow_back: bool = True,
) -> Union[int, type[GoBack]]:
    """Pick a year. Returns the selected year or GoBack."""
    effective_bounds = bounds or Bounds()
    default_year = default if default is not None else datetime.now().year
    years = allowed_years(effective_bounds)
    if not years:
        raise RuntimeError("no years available within bounds")

    selected: list[int] = [default_year]
    state = ScreenState(focus_index=list_focus_index(years, default_year))

    def render() -> FormattedText:
        lines: list[tuple[str, str]] = [("class:title", f"{title}\n\n"), ("", "Year\n\n")]
        start, end = visible_indices(len(years), state.focus_index)
        if start > 0:
            lines.append(("class:hint", "  …\n"))
        for index in range(start, end):
            year = years[index]
            marker = "› " if index == state.focus_index else "  "
            style = "class:focus" if index == state.focus_index else ""
            lines.append((style, f"{marker}{year}\n"))
        if end < len(years):
            lines.append(("class:hint", "  …\n"))
        append_input_line(lines, "Type year: ", state.text_input)
        back_hint = "← back · " if allow_back else ""
        append_palette(lines, f"{back_hint}↑↓ navigate · Enter select · type year · q quit")
        return FormattedText(lines)

    def bind_keys(kb: KeyBindings, screen: ScreenState) -> None:
        bind_text_input(kb, screen, digits_only=True, max_length=4)
        bind_quit(kb, screen)

        if allow_back:

            @kb.add("left", eager=True)
            def _back(event) -> None:
                screen.go_back = True
                event.app.exit()

        @kb.add("up", eager=True)
        def _up(event) -> None:
            screen.focus_index = (screen.focus_index - 1) % len(years)
            event.app.invalidate()

        @kb.add("down", eager=True)
        def _down(event) -> None:
            screen.focus_index = (screen.focus_index + 1) % len(years)
            event.app.invalidate()

        @kb.add("enter", eager=True)
        def _enter(event) -> None:
            if screen.text_input.strip():
                parsed = _parse_year_text(screen.text_input, years)
                if parsed is None:
                    screen.text_input = ""
                    event.app.invalidate()
                    return
                selected[0] = parsed
            else:
                selected[0] = years[screen.focus_index]
            screen.done = True
            event.app.exit()

    state = run_screen(state=state, render=render, bind_keys=bind_keys)
    if state.cancelled:
        raise Cancelled
    if state.go_back:
        return GoBack
    return selected[0]


def _parse_year_text(text: str, years: list[int]) -> Optional[int]:
    cleaned = text.strip()
    if not cleaned.isdigit():
        return None
    year = int(cleaned)
    if year not in years:
        return None
    return year
