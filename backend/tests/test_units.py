"""Unit tests for the pieces underneath the scenarios: one rule per test."""

from __future__ import annotations

from datetime import date, datetime, time

import pytest
from pydantic import ValidationError

from app.scheduler import generate_schedule, resolve_settings
from app.scheduler.models import (
    BlockKind,
    DayOverride,
    Event,
    EventException,
    EventType,
    ScheduleInput,
    SleepPattern,
    Task,
)
from app.scheduler.placement import _block_length
from app.scheduler.priority import make_state
from app.scheduler.settings import UnknownSettingError, changed_keys
from app.scheduler.timeline import build_day
from app.scheduler.timeutil import Interval, ceil_grid, fmt_hours, fmt_time, subtract

from . import scenarios as sc
from .checks import assert_hard_constraints

SUNDAY = date(2026, 10, 11)


def empty_week(**extra) -> ScheduleInput:
    """No events, wake 7:00, bed 23:00 every day."""
    sleep = [SleepPattern(weekday=i, wake_time=time(7), bed_time=time(23)) for i in range(7)]
    return ScheduleInput(sleep_patterns=sleep, **extra)


def task(id_: str, hours: float, due: datetime, **kw) -> Task:
    return Task(id=id_, title=id_, estimated_hours=hours, deadline=due, **kw)


# ----------------------------------------------------------------------------- timeutil


def test_subtract_splits_an_interval():
    day = Interval(sc.dt(SUNDAY, 8), sc.dt(SUNDAY, 12))
    parts = subtract([day], Interval(sc.dt(SUNDAY, 9), sc.dt(SUNDAY, 10)))
    assert parts == [
        Interval(sc.dt(SUNDAY, 8), sc.dt(SUNDAY, 9)),
        Interval(sc.dt(SUNDAY, 10), sc.dt(SUNDAY, 12)),
    ]


def test_formatting_and_grid():
    assert fmt_time(sc.dt(SUNDAY, 0, 5)) == "12:05am"
    assert fmt_time(sc.dt(SUNDAY, 13, 30)) == "1:30pm"
    assert fmt_hours(90) == "1.5h" and fmt_hours(40) == "40 min"
    assert ceil_grid(72.1) == 75


# ----------------------------------------------------------------------------- settings


def test_defaults_match_customization_doc():
    s = resolve_settings()
    assert s.study.max_hours_per_day == 5
    assert s.study.preferred_hours_per_task == 1.5 and s.study.max_hours_per_task == 2
    assert s.deadlines.estimate_padding == 1.25 and s.deadlines.finish_buffer_hours == 12
    assert s.weights.urgency == 0.30 and s.weights.important_bonus == 0.15


def test_overrides_are_validated():
    assert resolve_settings({"study.max_hours_per_day": 6}).study.max_hours_per_day == 6
    with pytest.raises(UnknownSettingError):
        resolve_settings({"study.max_hours_per_dya": 6})  # typo
    with pytest.raises(ValidationError):
        resolve_settings({"study.max_hours_per_day": -1})
    assert changed_keys({"study.max_hours_per_day": 5, "study.break_minutes": 15}) == {
        "study.break_minutes"
    }


# ----------------------------------------------------------------------------- timeline


def test_min_sleep_moves_a_weekly_bedtime_earlier():
    # Jordan's Saturday bedtime (12am) leaves only 7h before Sunday's 7am wake.
    ctx = build_day(sc.SAT_OCT_10, sc.scenario_1(), resolve_settings())
    assert ctx.bed == sc.dt(sc.SAT_OCT_10, 23)
    assert "Bedtime moved" in ctx.notes[0]


def test_one_day_override_wins_over_min_sleep_but_warns():
    inp = sc.scenario_1()
    inp.day_overrides = [DayOverride(date=sc.SAT_OCT_10, bed_time=time(1, 0))]
    ctx = build_day(sc.SAT_OCT_10, inp, resolve_settings())
    assert ctx.bed == sc.dt(SUNDAY, 1)
    assert "Only 6.0h of sleep" in ctx.notes[0]


def test_event_exception_moves_one_practice():
    inp = sc.scenario_3()
    inp.event_exceptions = [
        EventException(
            event_id="prac", date=sc.MON_OCT_12, new_start_time=time(18), new_end_time=time(20)
        )
    ]
    ctx = build_day(sc.MON_OCT_12, inp, resolve_settings())
    practice = next(o for o in ctx.occurrences if o.event.id == "prac")
    assert practice.interval == Interval(sc.dt(sc.MON_OCT_12, 18), sc.dt(sc.MON_OCT_12, 20))
    # dinner (normally 6:30) moves out of the way of practice
    dinner = next(i for i in ctx.items if i.title == "Dinner")
    assert dinner.interval.start >= sc.dt(sc.MON_OCT_12, 20)


def test_free_time_keeps_a_break_after_class_but_not_after_travel():
    ctx = build_day(sc.MON_OCT_12, sc.scenario_3(), resolve_settings())
    starts = {iv.start.time() for iv in ctx.free}
    assert time(10, 0) in starts  # class ends 9:50 -> study from 10:00
    assert time(17, 45) in starts  # travel home ends 5:45 -> study right away


def test_recovery_only_after_hard_practice():
    s = resolve_settings()
    assert build_day(sc.TUE_OCT_13, sc.scenario_3(), s).zones_of("recovery")
    assert not build_day(sc.MON_OCT_12, sc.scenario_3(), s).zones_of("recovery")


def test_fatigue_lowers_usable_hours_on_a_heavy_day():
    s = resolve_settings({"study.max_hours_per_day": 16})  # so the cap is fatigue, not H16
    light = build_day(sc.SAT_OCT_10, sc.scenario_1(), s)
    heavy = build_day(sc.TUE_OCT_13, sc.scenario_3(), s)
    assert heavy.fatigue_penalty > light.fatigue_penalty
    assert heavy.cap_minutes < heavy.free_minutes


# ----------------------------------------------------------------------------- priority


def test_padding_and_percent_complete():
    s = resolve_settings()
    t = task("x", 4, sc.dt(sc.FRI_OCT_16, 23, 59), percent_complete=50)
    assert make_state(t, s).remaining == 150  # 4h x 1.25 x 0.5
    assert make_state(t, s).finish_by == sc.dt(sc.FRI_OCT_16, 11, 59)


def test_important_flag_and_course_standing_raise_priority():
    due = sc.dt(sc.FRI_OCT_16, 23, 59)
    plain = task("plain", 2, due)
    boosted = task("boosted", 2, due, is_important=True)
    inp = empty_week(tasks=[plain, boosted])
    result = generate_schedule(inp, sc.MON_OCT_12, sc.MON_OCT_12)
    assert result.task("boosted").priority == pytest.approx(result.task("plain").priority + 0.15)


# ----------------------------------------------------------------------------- placement


def test_block_length_never_leaves_a_scrap():
    s = resolve_settings()
    assert _block_length(90, 65, s) == 60  # 65 would leave a 25 min scrap (test day 1)
    assert _block_length(120, 200, s) == 90  # H18
    assert _block_length(100, 200, s) == 70  # 90 would leave 10 -> leave 30 instead
    assert _block_length(50, 40, s) is None  # 40 + a 10 min scrap: doesn't fit here
    assert _block_length(20, 40, s) == 20  # finishing a small remainder is fine


def test_release_date_is_respected():
    t = task("posted-tue", 1, sc.dt(sc.FRI_OCT_16, 23, 59), release_at=sc.dt(sc.TUE_OCT_13, 12))
    inp = empty_week(tasks=[t])
    result = generate_schedule(inp, sc.MON_OCT_12, sc.WED_OCT_14)
    starts = [b.start for d in result.days for b in d.study_blocks()]
    assert starts and min(starts) >= sc.dt(sc.TUE_OCT_13, 12)


def test_dependency_waits_for_its_prerequisite():
    due = sc.dt(sc.FRI_OCT_16, 23, 59)
    outline = task("outline", 1, due)
    draft = task("draft", 1, due, depends_on=["outline"])
    inp = empty_week(tasks=[draft, outline])
    result = generate_schedule(inp, sc.MON_OCT_12, sc.MON_OCT_12)
    assert_hard_constraints(result, inp)
    blocks = result.day(sc.MON_OCT_12).study_blocks()
    outline_end = max(b.end for b in blocks if b.task_id == "outline")
    draft_start = min(b.start for b in blocks if b.task_id == "draft")
    assert draft_start >= outline_end


def test_overdue_task_is_flagged_not_placed():
    late = task("late", 2, sc.dt(sc.MON_OCT_12, 9))
    result = generate_schedule(empty_week(tasks=[late]), sc.MON_OCT_12, sc.MON_OCT_12)
    assert not result.day(sc.MON_OCT_12).study_blocks()
    assert result.warnings[0].kind == "overdue"


def test_now_stops_placement_in_the_past():
    t = task("t", 1, sc.dt(sc.FRI_OCT_16, 23, 59))
    now = sc.dt(sc.MON_OCT_12, 15)
    result = generate_schedule(empty_week(tasks=[t]), sc.MON_OCT_12, sc.MON_OCT_12, now=now)
    assert all(b.start >= now for b in result.day(sc.MON_OCT_12).study_blocks())


def test_travel_with_no_study_blocks_everything_but_meals():
    bus = Event(
        id="bus",
        type=EventType.TRAVEL,
        title="Bus",
        start_time=time(8),
        end_time=time(20),
        start_date=sc.MON_OCT_12,
        study_during="none",
    )
    t = task("t", 2, sc.dt(sc.FRI_OCT_16, 23, 59), difficulty=1)
    result = generate_schedule(empty_week(events=[bus], tasks=[t]), sc.MON_OCT_12, sc.MON_OCT_12)
    day = result.day(sc.MON_OCT_12)
    assert all(b.end.time() <= time(8) or b.start.time() >= time(20) for b in day.study_blocks())
    assert [b.title for b in day.blocks if b.kind == BlockKind.MEAL] == [
        "Breakfast",
        "Lunch",
        "Dinner",
    ]
