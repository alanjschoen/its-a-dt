"""Shared prompt_toolkit screen infrastructure for picker UIs."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable, Literal, Optional

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Window
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style

_RESERVED_TEXT_KEYS = frozenset("qQ")

STYLE = Style.from_dict(
    {
        "title": "bold",
        "focus": "bold reverse",
        "disabled": "#666666",
        "palette": "#888888",
        "hint": "#666666",
        "input": "underline",
        "input-error": "underline ansired",
    }
)

_INPUT_ERROR_FLASH_SECONDS = 0.2


class GoBack(Exception):
    """Raised when the user presses back on the first step of a wizard."""


class Cancelled(Exception):
    """Raised when the user presses q to quit without selecting."""


@dataclass
class ScreenState:
    focus_index: int = 0
    text_input: str = ""
    field_input: str = ""
    time_field: Literal["hour", "minute"] = "hour"
    go_back: bool = False
    cancelled: bool = False
    done: bool = False
    input_error: bool = False


def run_screen(
    *,
    state: ScreenState,
    render: Callable[[], FormattedText],
    bind_keys: Callable[[KeyBindings, ScreenState], None],
) -> ScreenState:
    control = FormattedTextControl(lambda: render())
    kb = KeyBindings()
    bind_keys(kb, state)
    root_window = Window(content=control, wrap_lines=False, always_hide_cursor=True)
    layout = Layout(HSplit([root_window]))
    layout.focus(root_window)
    app = Application(
        layout=layout,
        key_bindings=kb,
        full_screen=True,
        style=STYLE,
        enable_page_navigation_bindings=False,
        mouse_support=False,
        erase_when_done=True,
    )
    with patch_stdout():
        app.run()
    return state


def list_focus_index(items: list[int], value: Optional[int]) -> int:
    if not items:
        return 0
    if value is not None and value in items:
        return items.index(value)
    if value is not None:
        return min(range(len(items)), key=lambda index: abs(items[index] - value))
    return len(items) // 2


def visible_indices(length: int, focus_index: int, *, window_size: int = 11) -> tuple[int, int]:
    if length <= window_size:
        return 0, length
    half = window_size // 2
    start = max(0, focus_index - half)
    end = min(length, start + window_size)
    start = max(0, end - window_size)
    return start, end


def reject_input(
    screen: ScreenState,
    event,
    *,
    eager: bool = False,
    field: bool = False,
) -> None:
    """Briefly highlight invalid input. Eager mode clears; standard mode keeps text."""
    if eager:
        if field:
            screen.field_input = ""
        else:
            screen.text_input = ""
    screen.input_error = True
    event.app.invalidate()

    async def _clear_error() -> None:
        await asyncio.sleep(_INPUT_ERROR_FLASH_SECONDS)
        screen.input_error = False
        get_app().invalidate()

    event.app.create_background_task(_clear_error())


def bind_digit_input(
    kb: KeyBindings,
    screen: ScreenState,
    *,
    max_length: int,
    back_on_empty: bool = False,
    eager: bool = False,
    is_complete: Callable[[str], bool],
    try_accept: Callable[[str], bool],
) -> None:
    """Digit-only input line with optional eager auto-accept when complete."""

    @kb.add("backspace", eager=True)
    def _backspace(event) -> None:
        if screen.text_input:
            screen.text_input = screen.text_input[:-1]
            screen.input_error = False
            event.app.invalidate()
            return
        if back_on_empty:
            screen.go_back = True
            event.app.exit()

    @kb.add(Keys.Any, eager=True)
    def _type(event) -> object:
        char = event.data
        if len(char) != 1 or not char.isprintable():
            return NotImplemented
        if char in _RESERVED_TEXT_KEYS:
            return NotImplemented
        if not char.isdigit():
            return NotImplemented
        if len(screen.text_input) >= max_length:
            return None
        screen.text_input += char
        screen.input_error = False
        if eager and is_complete(screen.text_input):
            if try_accept(screen.text_input):
                event.app.exit()
            else:
                reject_input(screen, event, eager=True)
        event.app.invalidate()
        return None


def append_input_line(
    lines: list[tuple[str, str]],
    prompt: str,
    text: str,
    *,
    error: bool = False,
) -> None:
    style = "class:input-error" if error else "class:input"
    lines.append(("", "\n"))
    lines.append((style, f"{prompt}{text}█\n"))


def append_palette(lines: list[tuple[str, str]], text: str) -> None:
    lines.append(("class:palette", f"\n{text}\n"))


def append_grid_row(
    lines: list[tuple[str, str]],
    cells: list[tuple[str, str]],
    *,
    sep: str = "  ",
) -> None:
    for index, cell in enumerate(cells):
        if index:
            lines.append(("", sep))
        lines.append(cell)
    lines.append(("", "\n"))


def bind_quit(kb: KeyBindings, screen: ScreenState) -> None:
    @kb.add("q", eager=True)
    @kb.add("Q", eager=True)
    @kb.add("c-c", eager=True)
    def _quit(event) -> None:
        screen.cancelled = True
        event.app.exit()


def bind_text_input(
    kb: KeyBindings,
    screen: ScreenState,
    *,
    digits_only: bool = False,
    max_length: Optional[int] = None,
    time_input: bool = False,
    back_on_empty: bool = False,
) -> None:
    @kb.add("backspace", eager=True)
    def _backspace(event) -> None:
        if screen.text_input:
            screen.text_input = screen.text_input[:-1]
            screen.input_error = False
            event.app.invalidate()
            return
        if back_on_empty:
            screen.go_back = True
            event.app.exit()

    @kb.add(Keys.Any, eager=True)
    def _maybe_type(event) -> object:
        char = event.data
        if len(char) != 1 or not char.isprintable():
            return NotImplemented
        if char in _RESERVED_TEXT_KEYS:
            return NotImplemented
        if digits_only and not char.isdigit():
            return NotImplemented
        if time_input and char not in "0123456789:":
            return NotImplemented
        if max_length is not None and len(screen.text_input) >= max_length:
            return None
        screen.text_input += char
        screen.input_error = False
        event.app.invalidate()
        return None
