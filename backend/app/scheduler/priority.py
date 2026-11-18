"""Step B of scheduler-design.md: how urgent each task is, and how much of it to do today.

Definitions used here (minutes, after A1 padding):

* remaining        estimated_hours x padding x (1 - percent_complete)
* finish_by        deadline - finish buffer (H20)
* task_cap(day)    the most this task could get on `day` if it had the day to itself:
                   min(per-task daily max H15, the day's study cap, free time it may use)
* planning days    today .. the day *before* the finish-by day (or just today if it is the
                   finish-by day). The plan aims to be done a day early, so the finish-by day is
                   only a fallback. This is what makes the essay in test day 3 front-load.
* start_by (A2)    latest planning day the task can start and still fit at task_cap per day.
                   None = it doesn't fit even if started today.
* mandatory today  remaining - everything it could still get on later days (incl. the finish-by
                   day). > 0 means "if this isn't done today, the deadline is missed".
* allotment        preferred hours per day (S1), raised to the max (H15) when the preferred pace
                   can't finish it within the planning days.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .models import Block, Course, Task
from .settings import Settings
from .timeline import DayContext
from .timeutil import ceil_grid


@dataclass
class TaskState:
    """A task plus what the scheduler has placed for it so far in this run."""

    task: Task
    remaining: int
    initial_remaining: int
    finish_by: datetime
    light: bool
    heavy: bool
    blocks: list[Block] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.task.id

    @property
    def last_end(self) -> datetime | None:
        return max((b.end for b in self.blocks), default=None)


def make_state(task: Task, settings: Settings) -> TaskState:
    padding = settings.deadlines.estimate_padding
    remaining = ceil_grid(task.estimated_hours * 60 * padding * (1 - task.percent_complete / 100))
    finish_by = task.deadline - timedelta(hours=settings.deadlines.finish_buffer_hours)
    return TaskState(
        task=task,
        remaining=remaining,
        initial_remaining=remaining,
        finish_by=finish_by,
        light=task.difficulty <= settings.energy.light_max_difficulty,
        heavy=task.difficulty >= settings.pregame.heavy_min_difficulty,
    )


def task_cap(state: TaskState, ctx: DayContext, settings: Settings) -> int:
    allowed = 0
    shortest = min(settings.study.min_block_minutes, state.remaining)
    for iv in ctx.free:
        if ctx.is_light_only(iv) and not state.light:
            continue
        clipped = iv.clip(state.task.release_at, state.finish_by)
        if clipped and clipped.minutes >= shortest:
            allowed += clipped.minutes
    max_per_task = int(settings.study.max_hours_per_task * 60)
    return min(max_per_task, ctx.cap_minutes, allowed)


def planning_days(state: TaskState, today: date, days: dict[date, DayContext]) -> list[date]:
    last = state.finish_by.date()
    if last > today:
        last -= timedelta(days=1)
    return [d for d in sorted(days) if today <= d <= last]


def start_by(
    state: TaskState, today: date, days: dict[date, DayContext], settings: Settings
) -> date | None:
    total = 0
    for d in reversed(planning_days(state, today, days)):
        total += task_cap(state, days[d], settings)
        if total >= state.remaining:
            return d
    return None


def future_capacity(
    state: TaskState, today: date, days: dict[date, DayContext], settings: Settings
) -> int:
    last = state.finish_by.date()
    return sum(task_cap(state, days[d], settings) for d in sorted(days) if today < d <= last)


def mandatory_today(
    state: TaskState, today: date, days: dict[date, DayContext], settings: Settings
) -> int:
    return max(0, state.remaining - future_capacity(state, today, days, settings))


@dataclass
class Allotment:
    minutes: int
    raised_to_max: bool
    planning_days: int


def allotment(
    state: TaskState, today: date, days: dict[date, DayContext], settings: Settings
) -> Allotment:
    preferred = int(settings.study.preferred_hours_per_task * 60)
    maximum = int(settings.study.max_hours_per_task * 60)
    plan = planning_days(state, today, days)
    comfortable = sum(min(preferred, task_cap(state, days[d], settings)) for d in plan)
    raised = state.remaining > comfortable
    target = maximum if raised else preferred
    return Allotment(
        min(target, state.remaining), raised and state.remaining > preferred, len(plan)
    )


@dataclass
class Score:
    priority: float
    factors: dict[str, float]
    start_by: date | None


def score(
    state: TaskState,
    today: date,
    days: dict[date, DayContext],
    all_states: list[TaskState],
    courses: dict[str, Course],
    settings: Settings,
) -> Score:
    """Ranking formula from constraints-v1.md section 4 (R1-R8)."""
    w, sc = settings.weights, settings.scale
    t = state.task

    available = sum(
        task_cap(state, days[d], settings)
        for d in sorted(days)
        if today <= d <= state.finish_by.date()
    )
    urgency_raw = state.remaining / available if available else math.inf
    sb = start_by(state, today, days, settings)
    if sb is None or sb <= today:
        pressure = 1.0
    else:
        pressure = max(0.0, 1 - (sb - today).days / sc.start_by_horizon_days)
    course = courses.get(t.course_id) if t.course_id else None
    standing = 1 - course.standing if course and course.standing is not None else 0.0
    blocking = any(t.id in other.task.depends_on and other.remaining > 0 for other in all_states)

    factors = {
        "urgency": min(1.0, urgency_raw),
        "start_by": pressure,
        "grade_weight": min(1.0, t.grade_weight / sc.grade_weight_full_at),
        "difficulty": (t.difficulty - 1) / 4,
        "remaining_work": min(1.0, state.remaining / 60 / sc.remaining_full_at_hours),
        "course_standing": standing,
        "blocking": 1.0 if blocking else 0.0,
        "important": 1.0 if t.is_important else 0.0,
    }
    priority = (
        w.urgency * factors["urgency"]
        + w.start_by * factors["start_by"]
        + w.grade_weight * factors["grade_weight"]
        + w.difficulty * factors["difficulty"]
        + w.remaining_work * factors["remaining_work"]
        + w.course_standing * factors["course_standing"]
        + w.blocking * factors["blocking"]
        + w.important_bonus * factors["important"]
    )
    factors["urgency_raw"] = round(urgency_raw, 3) if math.isfinite(urgency_raw) else 99.0
    return Score(round(priority, 4), {k: round(v, 3) for k, v in factors.items()}, sb)


def priority_key(state: TaskState, s: Score):
    """Higher priority first, then tie-breakers: earlier deadline, higher grade, already started."""
    t = state.task
    return (-s.priority, t.deadline, -t.grade_weight, 0 if t.percent_complete > 0 else 1, t.id)
