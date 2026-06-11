"""Time picker screen."""

from __future__ import annotations

import re
from datetime import date, datetime, time
from typing import Optional, Union

from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

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
    list_focus_index,
    reject_input,
    run_screen,
)

_MAX_HOUR = 23


def pick_time(
    *,
    bounds: Optional[Bounds] = None,
    on_date: Optional[date] = None,
    default: Optional[time] = None,
    title: str = "Select time",
    allow_back: bool = True,
    eager: bool = False,
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
        field_error = state.input_error and bool(state.field_input)
        hour_style = "class:focus" if state.time_field == "hour" else ""
        if lock_minutes:
            minute_style = "class:disabled"
        else:
            minute_style = "class:focus" if state.time_field == "minute" else ""
        if field_error:
            if state.time_field == "hour":
                hour_style = "class:input-error"
            elif not lock_minutes:
                minute_style = "class:input-error"

        hour_text, minute_text = _display_time(
            selected[0], state, minutes_locked=lock_minutes
        )
        lines.append(("", "  Hour     Minute\n"))
        lines.append((hour_style, f"  {hour_text}  "))
        lines.append((minute_style, f"{minute_text}\n"))

        append_input_line(
            lines, "Type HH:MM: ", state.text_input, error=state.input_error
        )
        back_hint = "⌫ back · " if allow_back else ""
        field_hint = "" if lock_minutes else "←→ field · "
        enter_hint = "Enter select" if lock_minutes else "Enter next/select"
        append_palette(
            lines,
            f"{back_hint}{field_hint}↑↓ adjust · {enter_hint} · type digits · q quit",
        )
        return FormattedText(lines)

    def bind_keys(kb: KeyBindings, screen: ScreenState) -> None:
        bind_quit(kb, screen)
        _bind_time_typing(
            kb,
            screen,
            selected=selected,
            bounds=effective_bounds,
            on_date=ref_date,
            allow_back=allow_back,
            eager=eager,
        )

        if not minutes_locked(effective_bounds):

            @kb.add("left", eager=True)
            def _hour_field(event) -> None:
                if screen.time_field == "minute":
                    if not _commit_field(
                        screen,
                        selected,
                        bounds=effective_bounds,
                        on_date=ref_date,
                        force=True,
                    ):
                        _reject_time(screen, event, eager, field=True)
                        return
                    screen.time_field = "hour"
                    event.app.invalidate()

            @kb.add("right", eager=True)
            def _minute_field(event) -> None:
                if screen.time_field == "hour":
                    if not _commit_field(
                        screen,
                        selected,
                        bounds=effective_bounds,
                        on_date=ref_date,
                        force=True,
                    ):
                        _reject_time(screen, event, eager, field=True)
                        return
                    screen.time_field = "minute"
                    event.app.invalidate()

            @kb.add("tab", eager=True)
            def _tab(event) -> None:
                if screen.time_field == "hour":
                    if not _commit_field(
                        screen,
                        selected,
                        bounds=effective_bounds,
                        on_date=ref_date,
                        force=True,
                    ):
                        _reject_time(screen, event, eager, field=True)
                        return
                    screen.time_field = "minute"
                else:
                    if not _commit_field(
                        screen,
                        selected,
                        bounds=effective_bounds,
                        on_date=ref_date,
                        force=True,
                    ):
                        _reject_time(screen, event, eager, field=True)
                        return
                    screen.time_field = "hour"
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
                parsed = _parse_time_text(
                    screen.text_input, effective_bounds, ref_date
                )
                if parsed is None:
                    _reject_time(screen, event, eager, field=False)
                    return
                selected[0] = parsed
                screen.text_input = ""
            elif screen.field_input:
                if not _commit_field(
                    screen,
                    selected,
                    bounds=effective_bounds,
                    on_date=ref_date,
                    force=True,
                ):
                    _reject_time(screen, event, eager, field=True)
                    return
                if screen.time_field == "hour" and not minutes_locked(effective_bounds):
                    screen.time_field = "minute"
                    event.app.invalidate()
                    return
            elif screen.time_field == "hour" and not minutes_locked(effective_bounds):
                screen.time_field = "minute"
                event.app.invalidate()
                return
            hour_value, minute_value = selected[0]
            candidate = datetime.combine(ref_date, time(hour_value, minute_value))
            if not datetime_allowed(candidate, effective_bounds):
                if screen.text_input.strip() or screen.field_input:
                    _reject_time(
                        screen,
                        event,
                        eager,
                        field=bool(screen.field_input),
                    )
                else:
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


def _display_time(
    selected: tuple[int, int],
    screen: ScreenState,
    *,
    minutes_locked: bool,
) -> tuple[str, str]:
    hour, minute = selected
    partial = screen.field_input
    in_field_entry = bool(partial)
    if in_field_entry and screen.time_field == "hour":
        hour_text = partial.rjust(2)
    else:
        hour_text = f"{hour:02d}"
    if minutes_locked:
        return hour_text, "  --"
    if in_field_entry and screen.time_field == "minute":
        minute_text = f" {partial.rjust(2)}"
    else:
        minute_text = f"   {minute:02d}"
    return hour_text, minute_text


def _reject_time(screen: ScreenState, event, eager: bool, *, field: bool) -> None:
    reject_input(screen, event, eager=eager, field=field)


def _bind_time_typing(
    kb: KeyBindings,
    screen: ScreenState,
    *,
    selected: list[tuple[int, int]],
    bounds: Bounds,
    on_date: date,
    allow_back: bool,
    eager: bool,
) -> None:
    lock_minutes = minutes_locked(bounds)

    @kb.add("backspace", eager=True)
    def _backspace(event) -> None:
        if screen.field_input:
            screen.field_input = screen.field_input[:-1]
            screen.input_error = False
            event.app.invalidate()
            return
        if screen.text_input:
            screen.text_input = screen.text_input[:-1]
            screen.input_error = False
            event.app.invalidate()
            return
        if allow_back:
            screen.go_back = True
            event.app.exit()

    @kb.add(Keys.Any, eager=True)
    def _type(event) -> object:
        char = event.data
        if len(char) != 1 or not char.isprintable():
            return NotImplemented
        if char in "qQ":
            return NotImplemented

        screen.input_error = False
        if char == ":" or screen.text_input:
            if char not in "0123456789:":
                return NotImplemented
            screen.text_input += char
            event.app.invalidate()
            return None

        if not char.isdigit():
            return NotImplemented

        if screen.time_field == "hour" or lock_minutes:
            if len(screen.field_input) >= 2:
                return None
            screen.field_input += char
            if eager:
                if screen.field_input[0] not in "01":
                    if _commit_field(
                        screen, selected, bounds=bounds, on_date=on_date
                    ):
                        if not lock_minutes:
                            screen.time_field = "minute"
                    else:
                        _reject_time(screen, event, eager, field=True)
                elif len(screen.field_input) == 2:
                    if _commit_field(
                        screen, selected, bounds=bounds, on_date=on_date
                    ):
                        if not lock_minutes:
                            screen.time_field = "minute"
                    else:
                        _reject_time(screen, event, eager, field=True)
            event.app.invalidate()
            return None

        if len(screen.field_input) >= 2:
            return None
        screen.field_input += char
        if eager and len(screen.field_input) == 2:
            if not _commit_field(
                screen, selected, bounds=bounds, on_date=on_date
            ):
                _reject_time(screen, event, eager, field=True)
        event.app.invalidate()
        return None


def _commit_field(
    screen: ScreenState,
    selected: list[tuple[int, int]],
    *,
    bounds: Bounds,
    on_date: date,
    force: bool = False,
) -> bool:
    partial = screen.field_input
    if not partial:
        return True
    if not partial.isdigit():
        return False

    lock_minutes = minutes_locked(bounds)
    if screen.time_field == "hour" or lock_minutes:
        if len(partial) == 1 and partial[0] in "01" and not force:
            return True
        value = int(partial)
        if not _hour_valid(value, bounds):
            return False
        hour, minute = selected[0]
        selected[0] = (
            value,
            _minute_after_hour_change(value, minute, bounds, on_date),
        )
        screen.field_input = ""
        return True

    if len(partial) == 1 and not force:
        return True
    value = int(partial)
    hour, _minute = selected[0]
    minutes = allowed_minutes(hour, bounds, on_date=on_date)
    if value not in minutes:
        return False
    selected[0] = (hour, value)
    screen.field_input = ""
    return True


def _minute_after_hour_change(
    hour: int,
    minute: int,
    bounds: Bounds,
    on_date: date,
) -> int:
    minutes = allowed_minutes(hour, bounds, on_date=on_date)
    if minute in minutes:
        return minute
    if minutes:
        return minutes[0]
    return minute


def _hour_valid(value: int, bounds: Bounds) -> bool:
    if value < 0 or value > _MAX_HOUR:
        return False
    return value in allowed_hours(bounds)


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
    screen.field_input = ""
    hour_value, minute_value = selected[0]
    hours = allowed_hours(bounds)
    if screen.time_field == "hour" or minutes_locked(bounds):
        if hour_value not in hours:
            hour_value = hours[0]
        index = hours.index(hour_value)
        hour_value = hours[(index + delta) % len(hours)]
        minute_value = _minute_after_hour_change(
            hour_value, minute_value, bounds, on_date
        )
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
