"""Hard-constraint checks that must hold for *every* schedule, whatever the scenario."""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from app.scheduler.models import BlockKind, ScheduleInput, ScheduleResult
from app.scheduler.priority import make_state
from app.scheduler.settings import resolve_settings


def per_task_minutes(result: ScheduleResult, day) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for b in result.day(day).study_blocks():
        totals[b.task_id] += b.minutes
    return dict(totals)


def assert_hard_constraints(result: ScheduleResult, inp: ScheduleInput) -> None:
    st = resolve_settings(inp.setting_overrides)
    finish_by = {t.id: make_state(t, st).finish_by for t in inp.tasks}
    brk = timedelta(minutes=st.study.break_minutes)
    for day in result.days:
        study = day.study_blocks()
        busy = [(f.start, f.end, f.title) for f in day.fixed]
        busy += [(b.start, b.end, b.title) for b in day.blocks if b.kind != BlockKind.STUDY]
        for b in study:
            where = f"{b.title} {b.start:%a %H:%M}"
            assert day.wake <= b.start and b.end <= day.bed, f"{where} is outside wake-bed (H1-H3)"
            for s, e, title in busy:
                assert not (b.start < e and s < b.end), f"{where} overlaps {title}"
            assert st.study.min_block_minutes <= b.minutes <= st.study.max_block_minutes, (
                f"{where} is {b.minutes} min (H17/H18)"
            )
            assert b.end <= finish_by[b.task_id], f"{where} ends after the finish-by time (H20)"
            assert b.reasons and b.reason, f"{where} has no explanation"
        for a, b in zip(study, study[1:], strict=False):
            assert b.start - a.end >= brk, f"less than a break between {a.title} and {b.title}"
        assert day.study_minutes() <= day.daily_study_max_minutes, f"{day.date} is over H16"
        for task_id, total in per_task_minutes(result, day.date).items():
            assert total <= st.study.max_hours_per_task * 60, f"{task_id} over H15 on {day.date}"
