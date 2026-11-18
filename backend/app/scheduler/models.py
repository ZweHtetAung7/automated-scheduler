"""Input and output shapes of the scheduler engine (Pydantic models).

Inputs mirror the tables in docs/data-model.md so the API layer can load rows from the
database and pass them in unchanged. Outputs map onto `schedule_runs` and `scheduled_blocks`.

All datetimes are naive *local* times (see timeutil.py).
"""

from __future__ import annotations

from datetime import date, datetime, time
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, model_validator

# ----------------------------------------------------------------------------- enums


class EventType(StrEnum):
    CLASS = "class"
    PRACTICE = "practice"
    GAME = "game"
    TEAM_OTHER = "team_other"  # lifting, film, treatment, study hall (H8)
    TRAVEL = "travel"  # away trips (H9)
    WORK = "work"
    SOCIAL = "social"
    EXAM = "exam"
    OTHER = "other"


class Intensity(StrEnum):
    LIGHT = "light"
    NORMAL = "normal"
    HARD = "hard"


class StudyDuring(StrEnum):
    NONE = "none"
    LIGHT = "light"
    NORMAL = "normal"


class TaskType(StrEnum):
    ASSIGNMENT = "assignment"
    READING = "reading"
    PROJECT = "project"
    LAB = "lab"
    EXAM_PREP = "exam_prep"
    OTHER = "other"


class TaskStatus(StrEnum):
    OPEN = "open"
    DONE = "done"
    DROPPED = "dropped"


class BlockKind(StrEnum):
    STUDY = "study"
    MEAL = "meal"
    RECOVERY = "recovery"
    TRAVEL = "travel"
    PRE_GAME = "pre_game"  # NEW vs data-model.md: the "arrive 2h early" window before a game


# ----------------------------------------------------------------------------- inputs


class SleepPattern(BaseModel):
    weekday: int = Field(ge=0, le=6)  # Monday = 0
    wake_time: time
    bed_time: time  # may be after midnight, e.g. 00:30


class DayOverride(BaseModel):
    date: date
    wake_time: time | None = None
    bed_time: time | None = None


class Course(BaseModel):
    id: str
    name: str
    code: str | None = None
    standing: float | None = Field(None, ge=0, le=1)  # R6, None = not set


class Event(BaseModel):
    id: str
    type: EventType
    title: str
    course_id: str | None = None
    start_time: time
    end_time: time
    start_date: date
    # one-off: defaults to start_date (set it later for overnight trips)
    # repeating: last date of the series; None = repeats forever
    end_date: date | None = None
    repeat_weekdays: list[int] | None = None  # e.g. [0, 2, 4] for MWF; None = one-off
    location: str | None = None  # None = no travel time added (online, "wherever I am")
    intensity: Intensity = Intensity.NORMAL
    is_away: bool = False
    study_during: StudyDuring | None = None  # travel defaults to LIGHT
    flexible: bool = False  # Phase 3; treated as fixed for now
    arrive_early_minutes: int | None = None  # overrides the game default for this event

    @model_validator(mode="after")
    def _defaults(self) -> Event:
        if self.end_date is None and self.repeat_weekdays is None:
            self.end_date = self.start_date
        if self.study_during is None:
            self.study_during = (
                StudyDuring.LIGHT if self.type == EventType.TRAVEL else StudyDuring.NONE
            )
        return self


class EventException(BaseModel):
    """A coach moved practice or a class was cancelled on one date."""

    event_id: str
    date: date
    cancelled: bool = False
    new_start_time: time | None = None
    new_end_time: time | None = None


class Task(BaseModel):
    id: str
    title: str
    course_id: str | None = None
    type: TaskType = TaskType.ASSIGNMENT
    estimated_hours: float = Field(gt=0)  # what the student typed, before padding
    percent_complete: float = Field(0, ge=0, le=100)
    deadline: datetime
    release_at: datetime | None = None  # H21
    grade_weight: float = Field(5, ge=0, le=100)
    difficulty: int = Field(3, ge=1, le=5)
    is_important: bool = False  # R8
    depends_on: list[str] = []  # H22 (task_dependencies table)
    status: TaskStatus = TaskStatus.OPEN


class ScheduleInput(BaseModel):
    """Everything the engine needs for one user. Loaded by the API layer from the DB."""

    sleep_patterns: list[SleepPattern]
    day_overrides: list[DayOverride] = []
    setting_overrides: dict[str, Any] = {}
    courses: list[Course] = []
    events: list[Event] = []
    event_exceptions: list[EventException] = []
    tasks: list[Task] = []
    seen_rule_notices: set[str] = set()  # rule_activations rows with notice_shown = true

    @model_validator(mode="after")
    def _seven_days(self) -> ScheduleInput:
        if sorted(p.weekday for p in self.sleep_patterns) != list(range(7)):
            raise ValueError("sleep_patterns needs exactly one row per weekday (0-6)")
        return self


# ----------------------------------------------------------------------------- outputs


class Reason(BaseModel):
    code: str  # machine-readable, e.g. "peak_focus", "raised_to_max"
    text: str  # shown to the user


class Block(BaseModel):
    """One row of `scheduled_blocks`."""

    id: str
    kind: BlockKind
    start: datetime
    end: datetime
    title: str
    task_id: str | None = None
    event_id: str | None = None
    reasons: list[Reason] = []

    @property
    def minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)

    @property
    def reason(self) -> str:
        """The single "Placed here because..." string stored in scheduled_blocks.reason."""
        return " ".join(r.text for r in self.reasons)


class FixedItem(BaseModel):
    """Classes, practices, games... drawn from `events`, not stored as blocks."""

    event_id: str
    type: EventType
    title: str
    start: datetime
    end: datetime
    location: str | None = None


class DayPlan(BaseModel):
    date: date
    wake: datetime
    bed: datetime
    fixed: list[FixedItem]
    blocks: list[Block]
    is_game_day: bool
    is_travel_day: bool
    load_factor: float
    fatigue_penalty: float
    free_minutes: int  # study-usable free time before any study is placed
    daily_study_max_minutes: int  # H16 after S5/S6 adjustments
    study_cap_minutes: int  # min(daily max, usable focus)
    notes: list[str] = []

    def study_blocks(self) -> list[Block]:
        return [b for b in self.blocks if b.kind == BlockKind.STUDY]

    def study_minutes(self) -> int:
        return sum(b.minutes for b in self.study_blocks())


class Option(BaseModel):
    code: str
    label: str


class ScheduleWarning(BaseModel):
    kind: str  # "shortfall" | "start_by" | "overdue" | "blocked" | "meal" | "travel" | "sleep"
    severity: str  # "info" | "warning" | "critical"
    message: str
    task_id: str | None = None
    short_minutes: int | None = None
    options: list[Option] = []


class TaskReport(BaseModel):
    task_id: str
    title: str
    remaining_minutes: int  # after padding, before this plan
    placed_minutes: int  # placed in this plan, before the finish-by time
    finish_by: datetime
    start_by: date | None  # A2; None = doesn't fit even if started today
    priority: float
    factors: dict[str, float]


class RuleNotice(BaseModel):
    rule_key: str  # matches rule_activations.rule_key
    message: str


class ScheduleResult(BaseModel):
    """One `schedule_runs` row plus its blocks."""

    range_start: date
    range_end: date
    days: list[DayPlan]
    tasks: list[TaskReport]
    warnings: list[ScheduleWarning]
    active_rules: list[str]
    rule_notices: list[RuleNotice]  # only rules whose notice hasn't been shown yet
    settings_snapshot: dict[str, Any]

    def day(self, d: date) -> DayPlan:
        return next(p for p in self.days if p.date == d)

    def task(self, task_id: str) -> TaskReport:
        return next(t for t in self.tasks if t.task_id == task_id)

    def block(self, block_id: str) -> Block:
        return next(b for p in self.days for b in p.blocks if b.id == block_id)
