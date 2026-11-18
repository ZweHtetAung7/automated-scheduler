# Backend

Python 3.12. Right now this is only the **scheduler engine** (`app/scheduler/`), pure Python with
no web server or database yet. The FastAPI routes and SQLAlchemy tables come next and will call
into it.

## Setup

Install [uv](https://docs.astral.sh/uv/) once (it manages Python versions, the virtual env and
dependencies), then from this folder:

```bash
uv sync            # creates .venv with Python 3.12, pydantic, pytest, ruff
```

## Everyday commands

```bash
uv run pytest                                   # run all tests (the 3 test days + unit tests)
uv run python scripts/show_schedule.py 2 --why  # print test day 2 with every block's reason
uv run ruff check . && uv run ruff format .     # lint + format
```

`show_schedule.py` takes `1`, `2`, `3` or `3b` (the scenarios in `docs/test-days.md`).

## Layout

```
app/scheduler/
  timeutil.py    Interval type and time helpers (local wall-clock time)
  settings.py    every setting + its default; resolve_settings(overrides)
  models.py      input/output shapes (Pydantic), mirroring docs/data-model.md
  timeline.py    Step A: one day's fixed timeline, free time and capacity
  priority.py    Step B: ranking R1-R8, start-by dates, how much of a task to do today
  placement.py   Step C: greedy placement + "why is this here?" reasons
  engine.py      generate_schedule(), explain_block(), start_by_changes(), warnings
tests/
  scenarios.py   Jordan's profile and the 3 test days as inputs
  checks.py      hard-constraint checks every schedule must pass
  test_scenarios.py, test_units.py
scripts/
  show_schedule.py
```

## Using the engine

```python
from datetime import date
from app.scheduler import generate_schedule, ScheduleInput

result = generate_schedule(inputs, start=date(2026, 10, 12), end=date(2026, 10, 16))
for day in result.days:
    for block in day.blocks:
        print(block.kind, block.start, block.end, block.title, block.reason)
print(result.warnings)
```
