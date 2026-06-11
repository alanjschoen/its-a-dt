# its-a-dt

Interactive terminal date and time picker for Typer CLIs.

```bash
pip install its-a-dt
its-a-dt month --year 2025
its-a-dt day --year 2025 --month 6 --days-of-week mon,wed,fri
its-a-dt time --interval 15min --hours 9-17
its-a-dt datetime
```

```python
from datetime import datetime

from its_a_dt import Bounds, pick_year, pick_month, pick_day, pick_time, pick_datetime

year = pick_year(bounds=Bounds(max=datetime(2025, 12, 31)))
month = pick_month(year=year, bounds=bounds)
day = pick_day(year=year, month=month, bounds=Bounds.days_of_week_only("mon", "fri"))
t = pick_time(bounds=Bounds.minute_interval(15))
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Build and publish

```bash
pip install hatch
hatch build          # creates dist/its_a_dt-*.whl and dist/its_a_dt-*.tar.gz
hatch publish        # upload to PyPI (configure credentials first)
```

To publish via GitHub Actions, create a PyPI trusted publisher for this repository, then cut a GitHub release. The workflow in `.github/workflows/publish.yml` builds and uploads the package automatically.
