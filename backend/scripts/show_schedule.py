"""Print a test scenario's schedule as a table, like the ones in docs/test-days.md.

uv run python scripts/show_schedule.py 1      # light Saturday
uv run python scripts/show_schedule.py 2      # game day
uv run python scripts/show_schedule.py 3      # two deadlines colliding (Mon-Fri)
uv run python scripts/show_schedule.py 3b     # ... after adding an away trip
add --why to print every block's explanation
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.scheduler import generate_schedule  # noqa: E402
from app.scheduler.models import DayPlan, ScheduleResult  # noqa: E402
from app.scheduler.timeutil import fmt_day, fmt_hours, fmt_time  # noqa: E402
from tests import scenarios as sc  # noqa: E402

RUNS = {
    "1": (sc.scenario_1, sc.SAT_OCT_10, sc.SAT_OCT_10),
    "2": (sc.scenario_2, sc.WED_OCT_14, sc.WED_OCT_14),
    "3": (sc.scenario_3, sc.MON_OCT_12, sc.FRI_OCT_16),
    "3b": (sc.scenario_3b, sc.MON_OCT_12, sc.FRI_OCT_16),
}


def print_day(day: DayPlan, why: bool) -> None:
    flags = [
        f for f, on in (("game day", day.is_game_day), ("travel day", day.is_travel_day)) if on
    ]
    print(f"\n=== {fmt_day(day.date)}  {' / '.join(flags)}")
    print(
        f"    study {fmt_hours(day.study_minutes())} of cap {fmt_hours(day.study_cap_minutes)} "
        f"(daily max {fmt_hours(day.daily_study_max_minutes)}, load {day.load_factor}, "
        f"fatigue -{day.fatigue_penalty:.0%})"
    )
    rows = [(day.wake, day.wake, "Wake", "")]
    rows += [(f.start, f.end, f.title, f"[{f.type.value}]") for f in day.fixed]
    rows += [(b.start, b.end, b.title, f"[{b.kind.value}]") for b in day.blocks]
    rows.append((day.bed, day.bed, "Bed", ""))
    rows.sort(key=lambda r: (r[0], r[1]))
    for start, end, title, tag in rows:
        span = fmt_time(start) if start == end else f"{fmt_time(start)}-{fmt_time(end)}"
        print(f"    {span:<17} {title:<28} {tag}")
    if why:
        for b in day.study_blocks():
            print(f"      - {fmt_time(b.start)} {b.title}: {b.reason}")


def print_result(result: ScheduleResult, why: bool) -> None:
    for day in result.days:
        print_day(day, why)
    print("\nTasks (as of the first day):")
    for t in sorted(result.tasks, key=lambda t: -t.priority):
        sb = fmt_day(t.start_by) if t.start_by else "late"
        print(
            f"    {t.title:<18} priority {t.priority:.3f}  "
            f"remaining {fmt_hours(t.remaining_minutes)}  "
            f"placed {fmt_hours(t.placed_minutes)}  start by {sb}"
        )
    if result.warnings:
        print("\nWarnings:")
        for w in result.warnings:
            print(f"    [{w.severity}] {w.message}")
            for o in w.options:
                print(f"        option: {o.label}")
    for n in result.rule_notices:
        print(f"\nNotice ({n.rule_key}): {n.message}")


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "1"
    build, first, last = RUNS[key]
    print_result(generate_schedule(build(), first, last), why="--why" in sys.argv)
