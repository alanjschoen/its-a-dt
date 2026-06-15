# its-a-dt

Interactive terminal date and time picker for Python CLIs. Built on [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/), with a composable `Bounds` API for constraining what users can select.

Navigate with arrow keys, type values directly, or combine both. Multi-step flows (date, datetime) support back navigation with backspace.

![Demo](https://raw.githubusercontent.com/alanjschoen/its-a-dt/main/demo.gif)

## Install

```bash
pip install its-a-dt
```

## CLI

Run the full datetime wizard (no subcommand), or pick one field at a time:

```bash
its-a-dt                              # year → month → day → time
its-a-dt datetime --min 2025-01-01 --max 2025-12-31
its-a-dt date --days-of-week mon,wed,fri
its-a-dt year
its-a-dt month --year 2025
its-a-dt day --year 2025 --month 6 --days-of-week mon,wed,fri
its-a-dt time --interval 15min --hours 9-17
```

Common options:

| Option | Description |
|--------|-------------|
| `--min`, `--max` | Earliest/latest allowed value (ISO date or datetime) |
| `--days-of-week` | Comma-separated weekdays (`mon,wed,fri`) |
| `--days-of-month` | Comma-separated days of month (`1,15`) |
| `--hours` | Allowed hours (`9-17` or `9,10,11,15`) |
| `--interval` | Time step (`15min`, `30min`, `1hr`, `2hr`, …) |
| `--default`, `-d` | Starting value |
| `--eager` | Auto-advance as soon as a value is fully specified |

Press `q` or Ctrl-C to cancel. Selected values are printed to stdout.

## Python API

Import individual pickers or use the composed flows:

```python
from datetime import datetime

from its_a_dt import Bounds, pick_date, pick_datetime, pick_day, pick_month, pick_time, pick_year
from its_a_dt import Cancelled, GoBack

bounds = Bounds(max=datetime(2025, 12, 31))

year = pick_year(bounds=bounds)
month = pick_month(year=year, bounds=bounds)
day = pick_day(year=year, month=month, bounds=Bounds.days_of_week_only("mon", "fri"))
t = pick_time(bounds=Bounds.minute_interval(15))

# or run the full flow in one call
dt = pick_datetime(bounds=bounds)
```

Each picker returns the selected value, or `GoBack` if the user navigated to the previous step. Raise `Cancelled` when the user quits (press `q`).

### Bounds

`Bounds` limits which values appear in each picker. Combine constraints as needed:

```python
Bounds(max=datetime(2025, 12, 31))
Bounds.days_of_week_only("mon", "wed", "fri")
Bounds.days_of_month_only(1, 15)
Bounds.hours_only(9, 10, 11)
Bounds.hour_range(9, 17)
Bounds.minute_interval(15)   # 0, 15, 30, 45
Bounds.hour_interval(2)      # every 2 hours; minutes locked to :00
```

Date-range bounds affect year, month, and day pickers. Hour and minute constraints apply to the time picker. When picking a time for a specific date, pass `on_date` so min/max datetime bounds are evaluated correctly.

### Eager mode

By default, typed values are committed on Enter (or → in the time picker). With `eager=True`, pickers auto-advance as soon as the input uniquely identifies a value:

- **Year** — four digits entered
- **Month** — enough letters to identify one month (`f` → February, `jul` → July)
- **Day** — one or two digits when unambiguous
- **Time** — hour/minute digits when fully specified

Invalid input in eager mode clears the field; in standard mode it is kept so you can keep editing.

## Development

See [development.md](development.md) for local setup, testing, and publishing.
