# datepicker

Interactive terminal date and time picker for Typer CLIs.

```bash
pip install -e .
datepicker-demo month --year 2025
datepicker-demo day --year 2025 --month 6 --days-of-week mon,wed,fri
datepicker-demo time --interval 15min --hours 9-17
datepicker-demo datetime
```

```python
from datetime import datetime

from datepicker import Bounds, pick_year, pick_month, pick_day, pick_time, pick_datetime

year = pick_year(bounds=Bounds(max=datetime(2025, 12, 31)))
month = pick_month(year=year, bounds=bounds)
day = pick_day(year=year, month=month, bounds=Bounds.days_of_week_only("mon", "fri"))
t = pick_time(bounds=Bounds.minute_interval(15))
```
