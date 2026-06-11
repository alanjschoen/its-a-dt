from __future__ import annotations

import threading
import time

from prompt_toolkit.application import Application
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Window
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.patch_stdout import patch_stdout

from its_a_dt.pick_month import _move_grid_focus
from its_a_dt.screen import ScreenState, append_grid_row, bind_quit, bind_text_input


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
