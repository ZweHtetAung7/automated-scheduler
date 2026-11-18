"""Step C of scheduler-design.md: greedy placement, one day at a time.

For each day:
  1. AMOUNTS: decide how many minutes each task gets today, within the day's study cap (H16).
       pass 1  "mandatory" minutes (work that can't move to a later day), earliest finish-by first
       pass 2  top up every task to its allotment (S1 preferred / H15 max), highest priority first
       tidy    no amount below the minimum block (H17) unless it finishes the task
  2. LAYOUT: put each task's minutes into free time, best slot first. A slot's "cost" is mostly
     how late it is (earlier is better), adjusted by soft constraints:
       S4  heavy tasks like peak focus hours, light tasks leave them free
       S9  light tasks like low-energy slots (after practice/games, on the bus), heavy ones avoid
       S2  heavy tasks avoid the morning of / night before a game
       S10 avoid a 3rd different course in one evening
       and avoid cutting a task into more blocks than needed.
     Blocks are 30-90 min (H17/H18), never leave a <30 min scrap, and keep a 10 min break (H14)
     from other study blocks.

Soft-constraint costs are in "hours of lateness": -4 means "worth starting 4 hours later for".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from .models import Block, BlockKind, Course, Reason
from .priority import (
    Score,
    TaskState,
    allotment,
    mandatory_today,
    priority_key,
    score,
    task_cap,
)
from .settings import Settings
from .timeline import DayContext
from .timeutil import (
    Interval,
    at,
    ceil_grid,
    floor_grid,
    fmt_day,
    fmt_hours,
    fmt_time,
    minutes,
    subtract,
)

# Soft-constraint costs (hours). Kept here, not in Settings, until we tune them with real use.
COST_SPLIT = 6.0  # block shorter than it could be -> the task gets cut into more pieces
COST_HEAVY_PEAK = -4.0
COST_LIGHT_PEAK = 2.0
COST_LIGHT_LOW_ENERGY = -8.0
COST_HEAVY_LOW_ENERGY = 6.0
COST_HEAVY_PREGAME = 50.0
COST_EXTRA_EVENING_COURSE = 20.0


@dataclass
class DayDecision:
    """Why each task got the amount it got today (used for explanations)."""

    score: Score
    mandatory: int
    allot_minutes: int
    raised_to_max: bool
    planning_days: int
    amount: int
    capped_by_day: bool
    remaining_before: int


def _deps_met(state: TaskState, by_id: dict[str, TaskState]) -> bool:
    return all(by_id[d].remaining == 0 for d in state.task.depends_on if d in by_id)


def _earliest(state: TaskState, by_id: dict[str, TaskState]) -> datetime | None:
    times = [state.task.release_at] + [
        by_id[d].last_end for d in state.task.depends_on if d in by_id
    ]
    times = [t for t in times if t is not None]
    return max(times) if times else None


def _block_length(left: int, room: int, settings: Settings) -> int | None:
    """Length of the next block, or None if no valid block fits in `room` minutes."""
    mn, mx = settings.study.min_block_minutes, settings.study.max_block_minutes
    length = floor_grid(min(left, mx, room))
    if length < left and left - length < mn:  # would leave a scrap
        length = left - mn
    if length <= 0 or (length < mn and length < left):
        return None
    return length


def _clock_hours(day_start: datetime, moment: datetime) -> float:
    return (moment - day_start).total_seconds() / 3600


class DayPlanner:
    def __init__(
        self,
        ctx: DayContext,
        states: list[TaskState],
        days: dict,
        courses: dict[str, Course],
        settings: Settings,
    ) -> None:
        self.ctx = ctx
        self.states = states
        self.by_id = {s.id: s for s in states}
        self.days = days
        self.courses = courses
        self.settings = settings
        self.free = list(ctx.free)
        self.pool = ctx.cap_minutes
        self.blocks: list[Block] = []
        self.decisions: dict[str, DayDecision] = {}
        self.minutes_today: dict[str, int] = {}

    # ------------------------------------------------------------------ public

    def run(self) -> list[Block]:
        done_ids: set[str] = set()
        while True:  # a second round lets a task start after its prerequisite finishes today
            eligible = [
                s
                for s in self.states
                if s.id not in done_ids
                and s.remaining > 0
                and self._open_today(s)
                and _deps_met(s, self.by_id)
            ]
            if not eligible or self.pool <= 0:
                break
            done_ids |= {s.id for s in eligible}
            self._round(eligible)
        return sorted(self.blocks, key=lambda b: b.start)

    # ------------------------------------------------------------------ amounts

    def _open_today(self, s: TaskState) -> bool:
        release = s.task.release_at
        return s.finish_by > self.ctx.wake and (release is None or release < self.ctx.bed)

    def _round(self, eligible: list[TaskState]) -> None:
        today, st = self.ctx.day, self.settings
        scores = {s.id: score(s, today, self.days, self.states, self.courses, st) for s in eligible}
        by_priority = sorted(eligible, key=lambda s: priority_key(s, scores[s.id]))
        mandatory = {s.id: mandatory_today(s, today, self.days, st) for s in eligible}
        allots = {s.id: allotment(s, today, self.days, st) for s in eligible}
        avail = {s.id: task_cap(s, self.ctx, st) for s in eligible}
        amounts = {s.id: 0 for s in eligible}

        urgent = sorted(
            (s for s in eligible if mandatory[s.id] > 0),
            key=lambda s: (s.finish_by, priority_key(s, scores[s.id])),
        )
        for s in urgent:  # pass 1
            give = min(ceil_grid(mandatory[s.id]), avail[s.id], self.pool)
            amounts[s.id] += give
            self.pool -= give
        for s in by_priority:  # pass 2
            target = min(allots[s.id].minutes, s.remaining, avail[s.id])
            add = max(0, min(target - amounts[s.id], self.pool))
            amounts[s.id] += add
            self.pool -= add
        mn = st.study.min_block_minutes
        for s in by_priority:  # tidy: no scraps unless it finishes the task
            a = amounts[s.id]
            if 0 < a < mn and a < s.remaining:
                need = min(mn, s.remaining) - a
                if self.pool >= need and avail[s.id] >= a + need:
                    amounts[s.id] += need
                    self.pool -= need
                else:
                    amounts[s.id] = 0
                    self.pool += a

        for s in eligible:
            al = allots[s.id]
            self.decisions[s.id] = DayDecision(
                score=scores[s.id],
                mandatory=mandatory[s.id],
                allot_minutes=al.minutes,
                raised_to_max=al.raised_to_max,
                planning_days=al.planning_days,
                amount=amounts[s.id],
                capped_by_day=amounts[s.id] < min(al.minutes, avail[s.id]),
                remaining_before=s.remaining,
            )

        # Layout: tasks that can't wait go first (earliest finish-by), then by priority.
        order = urgent + [s for s in by_priority if s not in urgent]
        for s in order:
            if amounts[s.id] > 0:
                placed = self._layout(s, amounts[s.id], rank=by_priority.index(s) + 1)
                self.pool += amounts[s.id] - placed  # return what didn't fit

    # ------------------------------------------------------------------ layout

    def _cost(self, s: TaskState, block: Interval, left: int) -> float:
        ctx, st = self.ctx, self.settings
        day_start = at(ctx.day, time(0, 0))
        cost = _clock_hours(day_start, block.start)
        if block.minutes < min(left, st.study.max_block_minutes):
            cost += COST_SPLIT
        peak = Interval(at(ctx.day, st.energy.peak_start), at(ctx.day, st.energy.peak_end))
        in_peak = peak.contains(block.start)
        low = ctx.in_zone("low_energy", block.start)
        if s.heavy and in_peak:
            cost += COST_HEAVY_PEAK
        if s.light and in_peak:
            cost += COST_LIGHT_PEAK
        if st.energy.light_tasks_in_low_energy:
            if s.light and low:
                cost += COST_LIGHT_LOW_ENERGY
            if s.heavy and low:
                cost += COST_HEAVY_LOW_ENERGY
        if s.heavy and ctx.overlaps_zone("pregame", block):
            cost += COST_HEAVY_PREGAME
        if s.task.course_id and block.start >= at(ctx.day, st.study.evening_starts):
            courses = self._evening_courses()
            if s.task.course_id not in courses and len(courses) >= st.study.max_courses_per_evening:
                cost += COST_EXTRA_EVENING_COURSE
        return cost

    def _evening_courses(self) -> set[str]:
        evening = at(self.ctx.day, self.settings.study.evening_starts)
        return {
            self.by_id[b.task_id].task.course_id
            for b in self.blocks
            if b.start >= evening and b.task_id and self.by_id[b.task_id].task.course_id
        }

    def _candidates(self, iv: Interval) -> list[datetime]:
        """Slot start plus soft-zone edges inside it, so e.g. a heavy task can start at noon."""
        points = {iv.start}
        for z in self.ctx.zones:
            if z.kind in ("pregame", "low_energy"):
                for p in (z.interval.start, z.interval.end):
                    if iv.start < p < iv.end:
                        points.add(p)
        return sorted(points)

    def _layout(self, s: TaskState, amount: int, rank: int) -> int:
        ctx, st = self.ctx, self.settings
        earliest = _earliest(s, self.by_id)
        brk = minutes(st.study.break_minutes)
        left = amount
        while left > 0:
            best: tuple[float, datetime, int] | None = None
            for iv in self.free:
                if ctx.is_light_only(iv) and not s.light:
                    continue
                portion = iv.clip(earliest, s.finish_by)
                if portion is None:
                    continue
                for start in self._candidates(portion):
                    length = _block_length(
                        left, int((portion.end - start).total_seconds() // 60), st
                    )
                    if length is None:
                        continue
                    block = Interval(start, start + minutes(length))
                    option = (self._cost(s, block, left), start, length)
                    if best is None or option[:2] < best[:2]:
                        best = option
            if best is None:
                break
            _, start, length = best
            block = Interval(start, start + minutes(length))
            self.free = sorted(subtract(self.free, Interval(block.start - brk, block.end + brk)))
            self._add_block(s, block, rank)
            left -= length
        return amount - left

    # ------------------------------------------------------------------ explanations

    def _add_block(self, s: TaskState, block: Interval, rank: int) -> None:
        d = self.decisions[s.id]
        st = self.settings
        reasons: list[Reason] = []
        due = f"{fmt_day(s.task.deadline.date())} {fmt_time(s.task.deadline)}"
        finish_by = f"{fmt_day(s.finish_by.date())} {fmt_time(s.finish_by)}"
        buffer = f"{st.deadlines.finish_buffer_hours:g}h before the {due} deadline"
        if d.mandatory >= d.remaining_before:
            reasons.append(
                Reason(
                    code="must_do_today",
                    text=f"Has to be done by {finish_by} ({buffer}) and later days have no room "
                    "for it, so it went first.",
                )
            )
        elif d.mandatory > 0:
            reasons.append(
                Reason(
                    code="partly_due_today",
                    text=f"At least {fmt_hours(d.mandatory)} of it has to happen today to be done "
                    f"by {finish_by} ({buffer}).",
                )
            )
        elif rank == 1:
            reasons.append(
                Reason(
                    code="top_priority",
                    text=f"Top priority today (due {due}, {s.task.grade_weight:g}% of the grade).",
                )
            )
        else:
            reasons.append(
                Reason(code="by_priority", text=f"#{rank} by priority today (due {due}).")
            )

        if d.raised_to_max and d.amount > st.study.preferred_hours_per_task * 60:
            reasons.append(
                Reason(
                    code="raised_to_max",
                    text=f"{fmt_hours(d.amount)} today, above your "
                    f"{fmt_hours(st.study.preferred_hours_per_task * 60)} preference, because "
                    f"{fmt_hours(d.remaining_before)} remain and {d.planning_days} day(s) at your "
                    "preferred pace wouldn't finish it a day early.",
                )
            )
        if d.capped_by_day:
            reasons.append(
                Reason(
                    code="capped_by_day",
                    text=f"Only {fmt_hours(d.amount)} today because the day's study limit "
                    f"({fmt_hours(self.ctx.cap_minutes)}) is used up.",
                )
            )

        peak = Interval(
            at(self.ctx.day, st.energy.peak_start), at(self.ctx.day, st.energy.peak_end)
        )
        if s.heavy and self.ctx.overlaps_zone("pregame", block):
            reasons.append(
                Reason(
                    code="pregame_forced",
                    text="No other slot fit, so this heavy task is in the pre-game window.",
                )
            )
        elif s.heavy and peak.contains(block.start):
            reasons.append(
                Reason(
                    code="peak_focus",
                    text=f"A hard task in your peak focus hours "
                    f"({fmt_time(peak.start)}-{fmt_time(peak.end)}).",
                )
            )
        elif s.light and self.ctx.in_zone("low_energy", block.start):
            reasons.append(
                Reason(
                    code="low_energy_light",
                    text="A light task in a low-energy slot, keeping better hours for harder work.",
                )
            )
        else:
            reasons.append(Reason(code="earliest_slot", text="Earliest free slot that fits."))
        if (
            s.heavy
            and self.ctx.zones_of("pregame")
            and not self.ctx.overlaps_zone("pregame", block)
        ):
            reasons.append(
                Reason(
                    code="pregame_avoided",
                    text="Kept out of the pre-game window (no heavy work the "
                    "morning of or night before a game).",
                )
            )

        b = Block(
            id=f"{self.ctx.day:%Y%m%d}-study-{len(self.blocks) + 1}",
            kind=BlockKind.STUDY,
            start=block.start,
            end=block.end,
            title=s.task.title,
            task_id=s.id,
            reasons=reasons,
        )
        self.blocks.append(b)
        s.blocks.append(b)
        s.remaining -= block.minutes
        self.minutes_today[s.id] = self.minutes_today.get(s.id, 0) + block.minutes
