"""Small time helpers used by every scheduler module.

The scheduler works in the user's *local wall-clock time* using naive datetimes.
Converting to and from UTC (how the database stores times) is the API layer's job,
so the scheduler itself never has to think about time zones.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

GRID_MINUTES = 5  # every computed duration is rounded to this grid


@dataclass(frozen=True, order=True)
class Interval:
    """A half-open time range [start, end)."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"Interval ends before it starts: {self.start} > {self.end}")

    @property
    def minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)

    def overlaps(self, other: Interval) -> bool:
        return self.start < other.end and other.start < self.end

    def contains(self, moment: datetime) -> bool:
        return self.start <= moment < self.end

    def intersect(self, other: Interval) -> Interval | None:
        start, end = max(self.start, other.start), min(self.end, other.end)
        return Interval(start, end) if start < end else None

    def clip(self, earliest: datetime | None, latest: datetime | None) -> Interval | None:
        start = max(self.start, earliest) if earliest else self.start
        end = min(self.end, latest) if latest else self.end
        return Interval(start, end) if start < end else None


def at(day: date, clock: time) -> datetime:
    """Combine a date and a time of day into a naive local datetime."""
    return datetime.combine(day, clock)


def minutes(n: float) -> timedelta:
    return timedelta(minutes=n)


def subtract(intervals: Iterable[Interval], cut: Interval) -> list[Interval]:
    """Remove `cut` from every interval, splitting where needed."""
    result: list[Interval] = []
    for iv in intervals:
        if not iv.overlaps(cut):
            result.append(iv)
            continue
        if iv.start < cut.start:
            result.append(Interval(iv.start, cut.start))
        if cut.end < iv.end:
            result.append(Interval(cut.end, iv.end))
    return result


def subtract_all(intervals: Iterable[Interval], cuts: Iterable[Interval]) -> list[Interval]:
    result = list(intervals)
    for cut in cuts:
        result = subtract(result, cut)
    return sorted(result)


def split_at(intervals: Iterable[Interval], moments: Iterable[datetime]) -> list[Interval]:
    """Split intervals at each moment that falls strictly inside them."""
    points = sorted(set(moments))
    result: list[Interval] = []
    for iv in intervals:
        start = iv.start
        for p in points:
            if start < p < iv.end:
                result.append(Interval(start, p))
                start = p
        result.append(Interval(start, iv.end))
    return result


def floor_grid(n: float) -> int:
    return int(math.floor(n / GRID_MINUTES + 1e-9) * GRID_MINUTES)


def ceil_grid(n: float) -> int:
    return int(math.ceil(n / GRID_MINUTES - 1e-9) * GRID_MINUTES)


def fmt_time(moment: datetime) -> str:
    """9:05am style, matching the docs."""
    hour = moment.hour % 12 or 12
    suffix = "am" if moment.hour < 12 else "pm"
    return f"{hour}:{moment.minute:02d}{suffix}"


def fmt_hours(n_minutes: float) -> str:
    """90 -> '1.5h', 40 -> '40 min'."""
    if n_minutes < 60:
        return f"{round(n_minutes)} min"
    hours = n_minutes / 60
    return f"{hours:.2f}".rstrip("0").rstrip(".") + "h"


def fmt_day(day: date) -> str:
    return day.strftime("%a %b ") + str(day.day)


def daterange(first: date, last: date) -> list[date]:
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]
