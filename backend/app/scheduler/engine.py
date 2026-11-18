"""The scheduler's public entry points.

    generate_schedule(inputs, start, end)   -> ScheduleResult  (one schedule_runs row)
    explain_block(result, block_id)         -> "Placed here because..."
    start_by_changes(old, new)              -> A4: tasks whose start-by date moved earlier

Pure functions: no database, no web code. The API layer (Phase 1, next step) loads rows,
calls these, and saves the result. The chatbot (Phase 4) will call the same functions.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from .models import (
    Block,
    BlockKind,
    DayPlan,
    EventType,
    FixedItem,
    Intensity,
    Option,
    Reason,
    RuleNotice,
    ScheduleInput,
    ScheduleResult,
    ScheduleWarning,
    TaskReport,
    TaskStatus,
)
from .placement import DayPlanner
from .priority import TaskState, make_state, planning_days, score, start_by
from .settings import Settings, resolve_settings
from .timeline import DayContext, awake_window, build_day
from .timeutil import daterange, fmt_day, fmt_hours, fmt_time

MAX_LOOKAHEAD_DAYS = 120


def generate_schedule(
    inp: ScheduleInput, start: date, end: date, now: datetime | None = None
) -> ScheduleResult:
    """Plan study blocks for every day from `start` to `end` (inclusive).

    Days after `end`, up to the latest finish-by date, are still built so urgency and
    start-by dates can see the future; they just don't get blocks.
    `now` (optional) stops anything being placed earlier than that moment.
    """
    if end < start:
        raise ValueError("end must be on or after start")
    settings = resolve_settings(inp.setting_overrides)
    states = [make_state(t, settings) for t in inp.tasks if t.status == TaskStatus.OPEN]
    courses = {c.id: c for c in inp.courses}

    last_needed = max([end] + [s.finish_by.date() for s in states])
    last_needed = min(last_needed, start + timedelta(days=MAX_LOOKAHEAD_DAYS))
    days: dict[date, DayContext] = {
        d: build_day(d, inp, settings, now if now and now.date() == d else None)
        for d in daterange(start, last_needed)
    }

    # Snapshot priorities and start-by dates as of the first day (shown on task cards).
    first = days[start]
    initial = {s.id: score(s, start, days, states, courses, settings) for s in states}

    plans: list[DayPlan] = []
    for d in daterange(start, end):
        study = DayPlanner(days[d], states, days, courses, settings).run()
        plans.append(_day_plan(days[d], study, settings))

    next_wake = awake_window(end + timedelta(days=1), inp, settings)[0].start
    warnings = _warnings(states, days, plans, start, end, next_wake, first, initial, settings)
    for p in plans:
        warnings += [
            ScheduleWarning(kind="day_note", severity="info", message=f"{fmt_day(p.date)}: {n}")
            for n in p.notes
        ]

    reports = [
        TaskReport(
            task_id=s.id,
            title=s.task.title,
            remaining_minutes=s.initial_remaining,
            placed_minutes=sum(b.minutes for b in s.blocks if b.end <= s.finish_by),
            finish_by=s.finish_by,
            start_by=initial[s.id].start_by,
            priority=initial[s.id].priority,
            factors=initial[s.id].factors,
        )
        for s in states
    ]
    active = _active_rules(inp)
    notices = [
        RuleNotice(rule_key=k, message=_notice_text(k, settings))
        for k in active
        if k not in inp.seen_rule_notices
    ]
    return ScheduleResult(
        range_start=start,
        range_end=end,
        days=plans,
        tasks=reports,
        warnings=warnings,
        active_rules=active,
        rule_notices=notices,
        settings_snapshot=settings.model_dump(mode="json"),
    )


def explain_block(result: ScheduleResult, block_id: str) -> str:
    return result.block(block_id).reason


def start_by_changes(old: ScheduleResult, new: ScheduleResult) -> list[ScheduleWarning]:
    """A4: after a change (new game, trip, moved practice), flag start-by dates that moved
    earlier. None means "doesn't fit even if started today", the earliest possible."""
    out: list[ScheduleWarning] = []
    before = {t.task_id: t for t in old.tasks}
    for t in new.tasks:
        if t.task_id not in before:
            continue
        was, now_ = before[t.task_id].start_by, t.start_by
        if was is None:
            continue
        if now_ is None or now_ < was:
            target = fmt_day(now_) if now_ else "already late, even starting today"
            out.append(
                ScheduleWarning(
                    kind="start_by_moved",
                    severity="warning",
                    task_id=t.task_id,
                    message=f"{t.title}: start-by moved earlier, from {fmt_day(was)} to {target}.",
                )
            )
    return out


# ----------------------------------------------------------------------------- day output


def _day_plan(ctx: DayContext, study: list[Block], settings: Settings) -> DayPlan:
    blocks: list[Block] = list(study)
    fixed: list[FixedItem] = []
    occ_by_event = {o.event.id: o for o in ctx.occurrences}
    counter = 0

    def bid(kind: str) -> str:
        nonlocal counter
        counter += 1
        return f"{ctx.day:%Y%m%d}-{kind}-{counter}"

    for item in ctx.items:
        if item.kind == "event":
            o = occ_by_event[item.event_id]
            fixed.append(
                FixedItem(
                    event_id=o.event.id,
                    type=o.event.type,
                    title=o.event.title,
                    start=item.interval.start,
                    end=item.interval.end,
                    location=o.event.location,
                )
            )
            continue
        kind = BlockKind(item.kind)
        text = {
            BlockKind.MEAL: "Meal time protected (hard constraint).",
            BlockKind.TRAVEL: f"{settings.travel.minutes_between_places} min to get between "
            "different places.",
            BlockKind.PRE_GAME: "Arrive early for the game (game rule).",
        }[kind]
        blocks.append(
            Block(
                id=bid(kind.value),
                kind=kind,
                start=item.interval.start,
                end=item.interval.end,
                title=item.title,
                event_id=item.event_id,
                reasons=[Reason(code=kind.value, text=text)],
            )
        )
    for z in ctx.zones_of("recovery"):
        title = occ_by_event[z.event_id].event.title if z.event_id in occ_by_event else "event"
        blocks.append(
            Block(
                id=bid("recovery"),
                kind=BlockKind.RECOVERY,
                start=z.interval.start,
                end=z.interval.end,
                title=f"Recovery after {title}",
                event_id=z.event_id,
                reasons=[
                    Reason(
                        code="recovery", text="No study during recovery; meals and travel are fine."
                    )
                ],
            )
        )
    blocks.sort(key=lambda b: (b.start, b.kind != BlockKind.RECOVERY))
    return DayPlan(
        date=ctx.day,
        wake=ctx.wake,
        bed=ctx.bed,
        fixed=fixed,
        blocks=blocks,
        is_game_day=ctx.is_game_day,
        is_travel_day=ctx.is_travel_day,
        load_factor=ctx.load_factor,
        fatigue_penalty=ctx.fatigue_penalty,
        free_minutes=ctx.free_minutes,
        daily_study_max_minutes=ctx.daily_max_minutes,
        study_cap_minutes=ctx.cap_minutes,
        notes=ctx.notes,
    )


# ----------------------------------------------------------------------------- warnings


def _warnings(
    states: list[TaskState],
    days: dict[date, DayContext],
    plans: list[DayPlan],
    start: date,
    end: date,
    next_wake: datetime,
    first: DayContext,
    initial: dict,
    settings: Settings,
) -> list[ScheduleWarning]:
    out: list[ScheduleWarning] = []
    max_task = settings.study.max_hours_per_task
    for s in states:
        t = s.task
        due = f"{fmt_day(t.deadline.date())} {fmt_time(t.deadline)}"
        fby = f"{fmt_day(s.finish_by.date())} {fmt_time(s.finish_by)}"
        if s.finish_by <= first.wake:
            out.append(
                ScheduleWarning(
                    kind="overdue",
                    severity="critical",
                    task_id=s.id,
                    message=f"{t.title} is past its finish-by time ({fby}) with "
                    f"{fmt_hours(s.initial_remaining)} left. Due {due}.",
                    options=[
                        Option(code="ask_extension", label="Ask for an extension"),
                        Option(code="update_progress", label="Update % complete if it's done"),
                    ],
                )
            )
            continue

        placed = sum(b.minutes for b in s.blocks if b.end <= s.finish_by)
        short = s.initial_remaining - placed
        in_range = s.finish_by <= next_wake  # its last workable day is inside this plan
        has_shortfall = in_range and short > 0
        if has_shortfall:
            out.append(
                ScheduleWarning(
                    kind="shortfall",
                    severity="critical",
                    task_id=s.id,
                    short_minutes=short,
                    message=f"{t.title} doesn't fit: {fmt_hours(short)} short before {fby} "
                    f"(due {due}).",
                    options=_tradeoffs(s, days, plans, settings),
                )
            )

        sb = initial[s.id].start_by
        if settings.deadlines.start_by_warnings and t.percent_complete == 0:
            if sb is None and not has_shortfall:
                day_before = fmt_day(s.finish_by.date() - timedelta(days=1))
                out.append(
                    ScheduleWarning(
                        kind="start_by",
                        severity="warning",
                        task_id=s.id,
                        message=(
                            f"{t.title} is behind: even starting today at up to {max_task:g}h "
                            f"a day, it won't be done by {day_before} (a day before its {fby} "
                            "finish-by). It can still fit if the finish-by day is used."
                        ),
                    )
                )
            elif sb is not None and sb <= start:
                out.append(
                    ScheduleWarning(
                        kind="start_by",
                        severity="info",
                        task_id=s.id,
                        message=(
                            f"Start {t.title} today: it's the latest day it can start and "
                            f"still fit at up to {max_task:g}h a day."
                        ),
                    )
                )
        if any(d in {x.id for x in states} for d in t.depends_on) and not s.blocks and s.remaining:
            out.append(
                ScheduleWarning(
                    kind="blocked",
                    severity="info",
                    task_id=s.id,
                    message=f"{t.title} is waiting on another task to be finished first.",
                )
            )
    return out


def _tradeoffs(
    s: TaskState, days: dict[date, DayContext], plans: list[DayPlan], settings: Settings
) -> list[Option]:
    """A3: concrete things the student could change to make it fit."""
    opts: list[Option] = []
    window = [p.date for p in plans if p.date <= s.finish_by.date()]
    studied = {p.date: p.study_minutes() for p in plans}
    # Days where the study limit was the bottleneck: the cap was used up and free time is left.
    full_days = [
        d
        for d in window
        if studied[d] >= days[d].cap_minutes - 5
        and days[d].free_minutes >= studied[d] + settings.study.min_block_minutes
    ]
    if full_days:
        names = ", ".join(f"{d:%a}" for d in full_days)
        opts.append(
            Option(
                code="raise_daily_max",
                label=f"Raise the daily study max on {names} (uses some free time)",
            )
        )
    has_light_trip = any(
        z.study and z.study.value == "light" for d in window for z in days[d].zones_of("trip")
    )
    if has_light_trip and not s.light:
        opts.append(
            Option(code="allow_study_during_travel", label="Allow normal study during travel")
        )
    if settings.deadlines.finish_buffer_hours > 0:
        opts.append(
            Option(
                code="lower_finish_buffer",
                label=f"Finish closer to the deadline (buffer is now "
                f"{settings.deadlines.finish_buffer_hours:g}h)",
            )
        )
    opts.append(Option(code="ask_extension", label="Ask for an extension"))
    return opts


# ----------------------------------------------------------------------------- rule notices

RULE_TRIGGERS = {
    "game_rules": lambda e: e.type == EventType.GAME,
    "travel_rules": lambda e: e.type == EventType.TRAVEL,
    "hard_practice_recovery": lambda e: (
        e.type == EventType.PRACTICE and e.intensity == Intensity.HARD
    ),
    "work_shift_rules": lambda e: e.type == EventType.WORK,
}


def _active_rules(inp: ScheduleInput) -> list[str]:
    return [k for k, hit in RULE_TRIGGERS.items() if any(hit(e) for e in inp.events)]


def _notice_text(key: str, s: Settings) -> str:
    reduced = s.study.max_hours_per_day * (1 - s.energy.event_day_capacity_reduction)
    return {
        "game_rules": (
            f"Game rules are on: arrive {fmt_hours(s.athletics.arrive_early_for_games_minutes)} "
            f"early, {fmt_hours(s.recovery.after_game_minutes)} of recovery after, no heavy work "
            f"the night before or morning of a game, and at most {reduced:g}h of study on game "
            "days. Change these in Customization."
        ),
        "travel_rules": (
            f"Travel rules are on: trips default to light study only, and travel days have at "
            f"most {reduced:g}h of study. Change these in Customization."
        ),
        "hard_practice_recovery": (
            f"Added {fmt_hours(s.recovery.after_hard_practice_minutes)} of recovery after hard "
            "practices. Change this in Customization."
        ),
        "work_shift_rules": "Work shifts now count toward each day's load and capacity.",
    }[key]


__all__ = ["generate_schedule", "explain_block", "start_by_changes", "planning_days", "start_by"]
