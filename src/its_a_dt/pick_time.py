"""Time picker screen."""

from __future__ import annotations

import re
from datetime import date, datetime, time
from typing import Optional, Union

from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings

from its_a_dt.bounds import (
    Bounds,
    allowed_hours,
    allowed_minutes,
    datetime_allowed,
    minutes_locked,
    time_allowed,
)
from its_a_dt.screen import (
    Cancelled,
    GoBack,
    ScreenState,
    append_input_line,
    append_palette,
    bind_quit,
    bind_text_input,
    list_focus_index,
    run_screen,
)


def pick_time(
    *,
    bounds: Optional[Bounds] = None,
    on_date: Optional[date] = None,
    default: Optional[time] = None,
    title: str = "Select time",
    allow_back: bool = True,
) -> Union[time, type[GoBack]]:
    """Pick a time of day."""
    effective_bounds = bounds or Bounds()
    ref_date = on_date or date.today()
    now = datetime.now()
    default_time = default if default is not None else now.time()

    hours = allowed_hours(effective_bounds)
    if not hours:
        raise RuntimeError("no hours available within bounds")

    hour = hours[list_focus_index(hours, default_time.hour)]
    minutes = allowed_minutes(hour, effective_bounds, on_date=ref_date)
    if not minutes:
        raise RuntimeError(f"no minutes available for hour {hour} within bounds")
    minute = minutes[list_focus_index(minutes, default_time.minute)]

    selected: list[tuple[int, int]] = [(hour, minute)]
    state = ScreenState()
    if minutes_locked(effective_bounds):
        state.time_field = "hour"

    def render() -> FormattedText:
        lines: list[tuple[str, str]] = [("class:title", f"{title}\n\n"), ("", "Time\n\n")]
        lines.append(("class:hint", f"{ref_date.isoformat()}\n\n"))

        lock_minutes = minutes_locked(effective_bounds)
        hour_style = "class:focus" if state.time_field == "hour" else ""
        if lock_minutes:
            minute_style = "class:disabled"
            minute_label = "  --"
        else:
            minute_style = "class:focus" if state.time_field == "minute" else ""
            minute_label = f"   {selected[0][1]:02d}"

        lines.append(("", "  Hour     Minute\n"))
        lines.append((hour_style, f"  {selected[0][0]:02d}  "))
        lines.append((minute_style, f"{minute_label}\n"))

        append_input_line(lines, "Type HH:MM: ", state.text_input)
        back_hint = "⌫ back · " if allow_back else ""
        field_hint = "" if lock_minutes else "←→ field · "
        enter_hint = "Enter select" if lock_minutes else "Enter next/select"
        append_palette(
            lines,
            f"{back_hint}{field_hint}↑↓ adjust · {enter_hint} · type HH:MM · q quit",
        )
        return FormattedText(lines)

    def bind_keys(kb: KeyBindings, screen: ScreenState) -> None:
        bind_text_input(kb, screen, time_input=True, back_on_empty=allow_back)
        bind_quit(kb, screen)

        if not minutes_locked(effective_bounds):

            @kb.add("left", eager=True)
            def _hour_field(event) -> None:
                if screen.time_field != "hour":
                    screen.time_field = "hour"
                    event.app.invalidate()

            @kb.add("right", eager=True)
            def _minute_field(event) -> None:
                if screen.time_field != "minute":
                    screen.time_field = "minute"
                    event.app.invalidate()

            @kb.add("tab", eager=True)
            def _tab(event) -> None:
                screen.time_field = "minute" if screen.time_field == "hour" else "hour"
                event.app.invalidate()

        @kb.add("up", eager=True)
        def _up(event) -> None:
            _adjust_time(
                screen, selected, delta=1, bounds=effective_bounds, on_date=ref_date
            )
            event.app.invalidate()

        @kb.add("down", eager=True)
        def _down(event) -> None:
            _adjust_time(
                screen, selected, delta=-1, bounds=effective_bounds, on_date=ref_date
            )
            event.app.invalidate()

        @kb.add("enter", eager=True)
        def _enter(event) -> None:
            if screen.text_input.strip():
                parsed = _parse_time_text(screen.text_input, effective_bounds, ref_date)
                if parsed is None:
                    screen.text_input = ""
                    event.app.invalidate()
                    return
                selected[0] = parsed
            elif screen.time_field == "hour" and not minutes_locked(effective_bounds):
                screen.time_field = "minute"
                event.app.invalidate()
                return
            hour_value, minute_value = selected[0]
            candidate = datetime.combine(ref_date, time(hour_value, minute_value))
            if not datetime_allowed(candidate, effective_bounds):
                screen.text_input = ""
                event.app.invalidate()
                return
            screen.done = True
            event.app.exit()

    state = run_screen(state=state, render=render, bind_keys=bind_keys)
    if state.cancelled:
        raise Cancelled
    if state.go_back:
        return GoBack
    hour_value, minute_value = selected[0]
    return time(hour_value, minute_value)


def _parse_time_text(text: str, bounds: Bounds, on_date: date) -> Optional[tuple[int, int]]:
    cleaned = text.strip()
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", cleaned)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    if not time_allowed(time(hour, minute), bounds, on_date=on_date):
        return None
    return hour, minute


def _adjust_time(
    screen: ScreenState,
    selected: list[tuple[int, int]],
    *,
    delta: int,
    bounds: Bounds,
    on_date: date,
) -> None:
    hour_value, minute_value = selected[0]
    hours = allowed_hours(bounds)
    if screen.time_field == "hour" or minutes_locked(bounds):
        if hour_value not in hours:
            hour_value = hours[0]
        index = hours.index(hour_value)
        hour_value = hours[(index + delta) % len(hours)]
        minutes = allowed_minutes(hour_value, bounds, on_date=on_date)
        minute_value = minutes[0] if minutes else 0
        selected[0] = (hour_value, minute_value)
        return

    minutes = allowed_minutes(hour_value, bounds, on_date=on_date)
    if not minutes:
        return
    if minute_value not in minutes:
        minute_value = minutes[0]
    index = minutes.index(minute_value)
    minute_value = minutes[(index + delta) % len(minutes)]
    selected[0] = (hour_value, minute_value)
