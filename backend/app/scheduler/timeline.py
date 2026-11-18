"""Step A of scheduler-design.md: each day's fixed timeline and study capacity.

For one date this module works out:
  * the awake window (wake time -> bedtime, with H3 minimum sleep enforced)
  * fixed events that day (classes, practice, games...), with per-date exceptions applied
  * blocks the scheduler adds around them: pre-game arrival (H7), travel between places (H13),
    meals (H4)
  * zones: recovery (H12, no study), away trips (H9, light/none study), pre-game protection
    (S2, avoid heavy work), low-energy windows (S9)
  * the free intervals study can go into, with 10-minute breaks (H14) already applied
  * capacity: load factor, fatigue penalty, daily study max and the day's study cap (H16, S5, S6)

Nothing here decides *which task* goes where; that is placement.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .models import (
    BlockKind,
    Event,
    EventException,
    EventType,
    Intensity,
    ScheduleInput,
    StudyDuring,
)
from .settings import Settings
from .timeutil import (
    Interval,
    at,
    floor_grid,
    fmt_time,
    minutes,
    split_at,
    subtract_all,
)

ONE_DAY = timedelta(days=1)
MEAL_FALLBACK_MINUTES = 180  # how far lunch/dinner may move when events block the usual time


@dataclass
class Occurrence:
    """One event on one date."""

    event: Event
    interval: Interval  # the event itself
    occupied: Interval  # including arrive-early time for games


@dataclass
class Item:
    """Something that occupies time on the calendar (event, pre-game, meal, travel)."""

    kind: str  # "event" or a BlockKind value
    interval: Interval
    title: str
    event_id: str | None = None
    needs_break: bool = True  # study next to this item needs the H14 break


@dataclass
class Zone:
    """A window with study rules but no physical activity of its own."""

    kind: str  # "recovery" | "trip" | "pregame" | "low_energy"
    interval: Interval
    event_id: str | None = None
    study: StudyDuring | None = None  # only for trip zones


@dataclass
class DayContext:
    day: date
    wake: datetime
    bed: datetime
    occurrences: list[Occurrence]
    items: list[Item]
    zones: list[Zone]
    free: list[Interval]
    is_game_day: bool
    is_travel_day: bool
    load_factor: float
    fatigue_penalty: float
    free_minutes: int
    daily_max_minutes: int
    cap_minutes: int
    notes: list[str] = field(default_factory=list)

    def zones_of(self, kind: str) -> list[Zone]:
        return [z for z in self.zones if z.kind == kind]

    def in_zone(self, kind: str, moment: datetime) -> bool:
        return any(z.interval.contains(moment) for z in self.zones_of(kind))

    def overlaps_zone(self, kind: str, iv: Interval) -> bool:
        return any(z.interval.overlaps(iv) for z in self.zones_of(kind))

    def is_light_only(self, iv: Interval) -> bool:
        """Free intervals are split at trip boundaries, so checking the start is enough."""
        return any(
            z.study == StudyDuring.LIGHT and z.interval.contains(iv.start)
            for z in self.zones_of("trip")
        )


# ----------------------------------------------------------------------------- sleep


def _sleep_times(day: date, inp: ScheduleInput):
    pattern = next(p for p in inp.sleep_patterns if p.weekday == day.weekday())
    override = next((o for o in inp.day_overrides if o.date == day), None)
    wake_t = (override and override.wake_time) or pattern.wake_time
    bed_t = (override and override.bed_time) or pattern.bed_time
    explicit_bed = bool(override and override.bed_time)
    return wake_t, bed_t, explicit_bed


def awake_window(day: date, inp: ScheduleInput, settings: Settings) -> tuple[Interval, list[str]]:
    """Wake -> bed for `day`. Bed after midnight belongs to this day (H1, H2, H3)."""
    notes: list[str] = []
    wake_t, bed_t, explicit_bed = _sleep_times(day, inp)
    wake = at(day, wake_t)
    bed = at(day, bed_t)
    if bed_t <= wake_t:  # e.g. bed 00:30 -> after midnight
        bed += ONE_DAY

    next_wake_t, _, _ = _sleep_times(day + ONE_DAY, inp)
    next_wake = at(day + ONE_DAY, next_wake_t)
    latest_bed = next_wake - timedelta(hours=settings.sleep.min_hours)
    if bed > latest_bed:
        if explicit_bed:
            # A one-day change the user typed wins, but we tell them.
            hours = (next_wake - bed).total_seconds() / 3600
            notes.append(
                f"Only {hours:.1f}h of sleep before tomorrow's {fmt_time(next_wake)} wake."
            )
        else:
            notes.append(
                f"Bedtime moved from {fmt_time(bed)} to {fmt_time(latest_bed)} to keep "
                f"{settings.sleep.min_hours:g}h of sleep before tomorrow's {fmt_time(next_wake)} "
                "wake."
            )
            bed = latest_bed
    return Interval(wake, bed), notes


# ----------------------------------------------------------------------------- events


def _exception_for(
    exceptions: list[EventException], event_id: str, day: date
) -> EventException | None:
    return next((x for x in exceptions if x.event_id == event_id and x.date == day), None)


def _occurrence_interval(ev: Event, day: date, exc: EventException | None) -> Interval:
    start_t = (exc and exc.new_start_time) or ev.start_time
    end_t = (exc and exc.new_end_time) or ev.end_time
    if ev.repeat_weekdays is None:
        start, end = at(ev.start_date, start_t), at(ev.end_date or ev.start_date, end_t)
    else:
        start, end = at(day, start_t), at(day, end_t)
    if end <= start:
        end += ONE_DAY
    return Interval(start, end)


def occurrences_on(
    day: date, inp: ScheduleInput, window: Interval, settings: Settings
) -> list[Occurrence]:
    """All events that overlap this day's awake window, exceptions applied."""
    result: list[Occurrence] = []
    for ev in inp.events:
        if ev.repeat_weekdays is None:
            occ_date = ev.start_date
        else:
            if day.weekday() not in ev.repeat_weekdays or day < ev.start_date:
                continue
            if ev.end_date is not None and day > ev.end_date:
                continue
            occ_date = day
        exc = _exception_for(inp.event_exceptions, ev.id, occ_date)
        if exc and exc.cancelled:
            continue
        iv = _occurrence_interval(ev, occ_date, exc)
        if not iv.overlaps(window):
            continue
        occupied = iv
        if ev.type == EventType.GAME:
            early = ev.arrive_early_minutes
            if early is None:
                early = settings.athletics.arrive_early_for_games_minutes
            occupied = Interval(iv.start - minutes(early), iv.end)
        result.append(Occurrence(ev, iv, occupied))
    return sorted(result, key=lambda o: o.occupied.start)


def _has_game_on(day: date, inp: ScheduleInput, settings: Settings) -> bool:
    whole_day = Interval(at(day, datetime.min.time()), at(day + ONE_DAY, datetime.min.time()))
    return any(
        o.event.type == EventType.GAME and o.interval.start.date() == day
        for o in occurrences_on(day, inp, whole_day, settings)
    )


# ----------------------------------------------------------------------------- building a day


def _travel_items(
    occs: list[Occurrence], trips: list[Zone], window: Interval, settings: Settings
) -> tuple[list[Item], list[str]]:
    """Travel blocks between different places (H13). Inside an away trip, the trip covers it."""
    if not settings.travel.enabled:
        return [], []
    tmin = settings.travel.minutes_between_places
    home = settings.travel.home_location

    def inside_trip(o: Occurrence) -> bool:
        return any(z.interval.contains(o.occupied.start) for z in trips)

    located = [
        o
        for o in occs
        if o.event.type != EventType.TRAVEL and o.event.location and not inside_trip(o)
    ]
    items: list[Item] = []
    notes: list[str] = []
    current, prev_end = home, window.start
    for o in located:
        loc = o.event.location
        if loc != current:
            end = o.occupied.start
            start = max(prev_end, end - minutes(tmin))
            if start < end:
                items.append(
                    Item(
                        BlockKind.TRAVEL,
                        Interval(start, end),
                        f"Travel to {loc}",
                        o.event.id,
                        needs_break=False,
                    )
                )
            if (end - start) < minutes(tmin):
                notes.append(
                    f"Only {int((end - start).total_seconds() // 60)} min to get to "
                    f"{o.event.title} at {fmt_time(end)}."
                )
            current = loc
        prev_end = max(prev_end, o.occupied.end)

    trip_later = any(z.interval.end > prev_end for z in trips)
    if located and current != home and not trip_later:
        end = min(prev_end + minutes(tmin), window.end)
        if prev_end < end:
            items.append(
                Item(
                    BlockKind.TRAVEL,
                    Interval(prev_end, end),
                    "Travel home",
                    located[-1].event.id,
                    needs_break=False,
                )
            )
    return items, notes


def _place_meals(
    day: date, window: Interval, taken: list[Interval], settings: Settings
) -> tuple[list[Item], list[str]]:
    """Meals at their usual times, shifted up to 30 min to dodge events (H4)."""
    m = settings.meals
    if not m.enabled:
        return [], []
    wake = window.start
    # (name, preferred start, length, how far the fallback may move it, prefer moving later)
    plan = [
        (
            "Breakfast",
            wake + minutes(m.breakfast_after_wake_minutes),
            m.breakfast_minutes,
            60 - m.breakfast_after_wake_minutes,
            False,
        ),  # stays within an hour of waking
        ("Lunch", at(day, m.lunch_start), m.lunch_minutes, MEAL_FALLBACK_MINUTES, False),
        # customization.md: dinner "moves after practice if they overlap"
        ("Dinner", at(day, m.dinner_start), m.dinner_minutes, MEAL_FALLBACK_MINUTES, True),
    ]
    items: list[Item] = []
    notes: list[str] = []
    busy = list(taken)

    def free_at(iv: Interval) -> bool:
        inside = window.start <= iv.start and iv.end <= window.end
        return inside and not any(iv.overlaps(b) for b in busy)

    shifts = [0]
    for s in range(5, m.max_shift_minutes + 1, 5):
        shifts += [s, -s]  # prefer later: "dinner moves after practice"
    for name, preferred, dur, reach, prefer_later in plan:
        chosen = None
        for s in shifts:
            iv = Interval(preferred + minutes(s), preferred + minutes(s + dur))
            if free_at(iv):
                chosen = iv
                break
        if chosen is None:
            # Fallback: the gap closest to the usual time, before or after whatever is in the
            # way. Dinner tries after first (post-practice / post-game meal).
            options = []
            for g in subtract_all([window], busy):
                if g.minutes < dur:
                    continue
                for start in (
                    max(g.start, preferred),
                    min(g.end, preferred + minutes(dur)) - minutes(dur),
                ):
                    start = min(max(start, g.start), g.end - minutes(dur))
                    if abs(start - preferred) <= minutes(reach):
                        wrong_side = prefer_later and start < preferred
                        options.append((wrong_side, abs(start - preferred), start))
            if options:
                start = min(options)[2]
                chosen = Interval(start, start + minutes(dur))
        if chosen is None:
            notes.append(f"Couldn't fit {name.lower()} on {day:%a}; check the day's events.")
            continue
        busy.append(chosen)
        items.append(Item(BlockKind.MEAL, chosen, name))
    return items, notes


def build_day(
    day: date, inp: ScheduleInput, settings: Settings, now: datetime | None = None
) -> DayContext:
    window, notes = awake_window(day, inp, settings)
    occs = occurrences_on(day, inp, window, settings)

    items: list[Item] = []
    zones: list[Zone] = []
    for o in occs:
        ev = o.event
        if ev.type == EventType.TRAVEL:
            trip = o.interval.intersect(window)
            if trip:
                zones.append(Zone("trip", trip, ev.id, ev.study_during))
                if ev.study_during == StudyDuring.LIGHT:
                    zones.append(Zone("low_energy", trip, ev.id))
            continue
        if o.occupied.start < o.interval.start:  # game arrival
            pre = Interval(o.occupied.start, o.interval.start).intersect(window)
            if pre:
                items.append(Item(BlockKind.PRE_GAME, pre, f"Arrive early: {ev.title}", ev.id))
        shown = o.interval.intersect(window)
        if shown:
            items.append(Item("event", shown, ev.title, ev.id))

        recovery_end = o.interval.end
        rec = settings.recovery
        rec_minutes = 0
        if rec.enabled and ev.type == EventType.GAME:
            rec_minutes = rec.after_game_minutes
        elif rec.enabled and ev.type == EventType.PRACTICE and ev.intensity == Intensity.HARD:
            rec_minutes = rec.after_hard_practice_minutes
        if rec_minutes:
            recovery_end = o.interval.end + minutes(rec_minutes)
            rz = Interval(o.interval.end, recovery_end).intersect(window)
            if rz:
                zones.append(Zone("recovery", rz, ev.id))
        if ev.type in (EventType.PRACTICE, EventType.GAME):
            low_hours = settings.energy.low_energy_hours_after_athletics
            lz = Interval(recovery_end, recovery_end + timedelta(hours=low_hours)).intersect(window)
            if lz:
                zones.append(Zone("low_energy", lz, ev.id))

    # Pre-game protection (S2): no heavy work the morning of, or the night before, a game.
    if settings.pregame.enabled:
        games_today = [
            o for o in occs if o.event.type == EventType.GAME and o.interval.start.date() == day
        ]
        if games_today:
            end = min(at(day, settings.pregame.morning_until), games_today[0].occupied.start)
            if window.start < end:
                zones.append(Zone("pregame", Interval(window.start, end), games_today[0].event.id))
        if _has_game_on(day + ONE_DAY, inp, settings):
            start = at(day, settings.pregame.night_before_from)
            if start < window.end:
                zones.append(Zone("pregame", Interval(max(start, window.start), window.end)))

    trips = [z for z in zones if z.kind == "trip"]
    travel, travel_notes = _travel_items(occs, trips, window, settings)
    items += travel
    meals, meal_notes = _place_meals(day, window, [i.interval for i in items], settings)
    items += meals
    notes += travel_notes + meal_notes
    items.sort(key=lambda i: i.interval.start)

    # Free intervals for study.
    start = window.start
    if now and window.start < now:
        start = min(now, window.end)
    blocked = [i.interval for i in items] + [
        z.interval
        for z in zones
        if z.kind == "recovery" or (z.kind == "trip" and z.study == StudyDuring.NONE)
    ]
    free = subtract_all([Interval(start, window.end)], blocked)
    brk = minutes(settings.study.break_minutes)
    buffered: list[Interval] = []
    for iv in free:
        s, e = iv.start, iv.end
        if any(i.needs_break and i.interval.end == s for i in items):
            s += brk
        if any(i.needs_break and i.interval.start == e for i in items):
            e -= brk
        if s < e:
            buffered.append(Interval(s, e))
    trip_edges = [t for z in trips for t in (z.interval.start, z.interval.end)]
    free = split_at(buffered, trip_edges)

    # Capacity (Step A).
    fat = settings.fatigue
    load = 0.0
    for o in occs:
        weight = fat.load_weights.get(o.event.type.value, 0.5)
        load += weight * fat.intensity_multiplier.get(o.event.intensity.value, 1.0)
    penalty = min(fat.max_penalty, fat.penalty_per_load_unit * load)
    min_block = settings.study.min_block_minutes
    free_minutes = sum(iv.minutes for iv in free if iv.minutes >= min_block)
    usable = free_minutes * (1 - penalty)

    is_game_day = any(o.event.type == EventType.GAME for o in occs)
    is_travel_day = any(o.event.type == EventType.TRAVEL for o in occs)
    daily_max = settings.study.max_hours_per_day * 60
    daily_max *= settings.athletics.season_study_multiplier.get(settings.athletics.season_mode, 1)
    if is_game_day or is_travel_day:
        daily_max *= 1 - settings.energy.event_day_capacity_reduction
    daily_max = floor_grid(daily_max)
    cap = floor_grid(min(daily_max, usable))

    return DayContext(
        day=day,
        wake=window.start,
        bed=window.end,
        occurrences=occs,
        items=items,
        zones=zones,
        free=free,
        is_game_day=is_game_day,
        is_travel_day=is_travel_day,
        load_factor=round(load, 2),
        fatigue_penalty=round(penalty, 3),
        free_minutes=free_minutes,
        daily_max_minutes=daily_max,
        cap_minutes=cap,
        notes=notes,
    )
