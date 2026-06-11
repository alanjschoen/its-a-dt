from __future__ import annotations

import threading
import time
from datetime import date, datetime

from prompt_toolkit.application import Application
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Window
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.patch_stdout import patch_stdout

from its_a_dt.bounds import Bounds
from its_a_dt.pick_day import _day_entry_complete
from its_a_dt.pick_month import _move_grid_focus
from its_a_dt.pick_time import (
    _commit_field,
    _hour_valid,
    _minute_after_hour_change,
)
from its_a_dt.screen import (
    ScreenState,
    append_grid_row,
    append_input_line,
    bind_quit,
    bind_text_input,
    reject_input,
)


def test_append_input_line_error_style() -> None:
    lines: list[tuple[str, str]] = []
    append_input_line(lines, "Type year: ", "abcd", error=True)
    assert ("class:input-error", "Type year: abcd█\n") in lines


def test_append_grid_row_preserves_cell_styles() -> None:
    lines: list[tuple[str, str]] = []
    append_grid_row(lines, [("", " Jan"), ("class:focus", " Feb"), ("", " Mar")])
    assert ("class:focus", " Feb") in lines


def test_grid_arrows_with_text_input_on_same_screen() -> None:
    state = ScreenState(focus_index=0)
    enabled = list(range(1, 13))
    cancelled = {"value": False}

    def render() -> str:
        return f"month={enabled[state.focus_index]} input={state.text_input!r}"

    kb = KeyBindings()
    bind_quit(kb, state)
    bind_text_input(kb, state)

    @kb.add("right", eager=True)
    def right(event) -> None:
        _move_grid_focus(state, enabled, dx=1, dy=0, width=4)
        event.app.invalidate()

    @kb.add("q", eager=True)
    def quit_(event) -> None:
        cancelled["value"] = True
        event.app.exit()

    window = Window(FormattedTextControl(lambda: render()), wrap_lines=False, always_hide_cursor=True)
    layout = Layout(HSplit([window]))

    with create_pipe_input() as pipe:
        output = DummyOutput()
        app = Application(
            layout=layout,
            key_bindings=kb,
            input=pipe,
            output=output,
            full_screen=False,
            enable_page_navigation_bindings=False,
        )

        def run() -> None:
            with patch_stdout():
                app.run()

        thread = threading.Thread(target=run)
        thread.start()
        time.sleep(0.1)
        pipe.send_bytes(b"\x1b[C")
        time.sleep(0.1)
        pipe.send_text("q")
        time.sleep(0.1)
        if not cancelled["value"]:
            app.exit()
        thread.join()

    assert state.focus_index == 1
    assert cancelled["value"] is True


def test_hour_field_digit_rules() -> None:
    state = ScreenState(time_field="hour")
    selected: list[tuple[int, int]] = [(9, 0)]
    bounds = Bounds()
    today = date.today()

    state.field_input = "9"
    assert _commit_field(state, selected, bounds=bounds, on_date=today)
    assert selected[0][0] == 9
    assert state.field_input == ""

    state.field_input = "1"
    _commit_field(state, selected, bounds=bounds, on_date=today)
    assert selected[0][0] == 9
    assert state.field_input == "1"
    assert _commit_field(state, selected, bounds=bounds, on_date=today, force=True)
    assert selected[0][0] == 1

    state.field_input = "25"
    assert not _commit_field(state, selected, bounds=bounds, on_date=today)
    assert state.field_input == "25"

    state.field_input = "14"
    assert _commit_field(state, selected, bounds=bounds, on_date=today)
    assert selected[0][0] == 14


def test_minute_field_digit_rules() -> None:
    state = ScreenState(time_field="minute")
    selected: list[tuple[int, int]] = [(10, 0)]
    bounds = Bounds()
    today = date.today()

    state.field_input = "3"
    _commit_field(state, selected, bounds=bounds, on_date=today)
    assert selected[0][1] == 0
    assert state.field_input == "3"
    assert _commit_field(state, selected, bounds=bounds, on_date=today, force=True)
    assert selected[0][1] == 3

    state.field_input = "30"
    assert _commit_field(state, selected, bounds=bounds, on_date=today)
    assert selected[0][1] == 30

    state.field_input = "99"
    assert not _commit_field(state, selected, bounds=bounds, on_date=today)


def test_hour_change_preserves_valid_minute() -> None:
    bounds = Bounds.minute_interval(15)
    today = date.today()
    state = ScreenState(time_field="hour")
    selected: list[tuple[int, int]] = [(9, 30)]

    state.field_input = "10"
    assert _commit_field(state, selected, bounds=bounds, on_date=today)
    assert selected[0] == (10, 30)

    assert _minute_after_hour_change(10, 30, bounds, today) == 30


def test_hour_change_resets_invalid_minute() -> None:
    bounds = Bounds(
        min=datetime(2025, 6, 11, 9, 30),
        max=datetime(2025, 6, 11, 17, 0),
    )
    on_date = date(2025, 6, 11)
    assert _minute_after_hour_change(9, 45, bounds, on_date) == 45
    assert _minute_after_hour_change(17, 45, bounds, on_date) == 0


def test_hour_valid_respects_bounds() -> None:
    bounds = Bounds.hours_only(9, 10, 11)
    assert _hour_valid(9, bounds)
    assert not _hour_valid(8, bounds)


def test_reject_input_eager_clears_field_standard_keeps_text() -> None:
    class _FakeApp:
        def invalidate(self) -> None:
            return None

        def create_background_task(self, _coro) -> None:
            return None

    class _FakeEvent:
        app = _FakeApp()

    state = ScreenState(text_input="abcd", field_input="7")
    reject_input(state, _FakeEvent(), eager=True, field=True)
    assert state.field_input == ""
    assert state.text_input == "abcd"
    assert state.input_error

    state.field_input = "7"
    reject_input(state, _FakeEvent(), eager=False, field=True)
    assert state.field_input == "7"

    reject_input(state, _FakeEvent(), eager=True, field=False)
    assert state.text_input == ""


def test_day_entry_complete() -> None:
    assert not _day_entry_complete("")
    assert not _day_entry_complete("1")
    assert not _day_entry_complete("3")
    assert _day_entry_complete("5")
    assert _day_entry_complete("12")
    assert _day_entry_complete("15")
