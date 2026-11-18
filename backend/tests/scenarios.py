"""The three hand-worked test days from docs/test-days.md, as scheduler inputs.

Shared profile: Jordan, a soccer player. Dates are in 2026, when Oct 10 is a Saturday.
Task `estimated_hours` are what Jordan would type; the docs list hours *after* 25% padding,
so e.g. the 7.5h essay is typed as 6h (6 x 1.25 = 7.5).
"""

from __future__ import annotations

from datetime import date, datetime, time

from app.scheduler.models import (
    Course,
    Event,
    EventException,
    EventType,
    Intensity,
    ScheduleInput,
    SleepPattern,
    StudyDuring,
    Task,
)

SAT_OCT_10 = date(2026, 10, 10)
MON_OCT_12 = date(2026, 10, 12)
TUE_OCT_13 = date(2026, 10, 13)
WED_OCT_14 = date(2026, 10, 14)
THU_OCT_15 = date(2026, 10, 15)
FRI_OCT_16 = date(2026, 10, 16)

SEMESTER_START = date(2026, 8, 24)

MWF, TTH = [0, 2, 4], [1, 3]


def dt(d: date, hh: int, mm: int = 0) -> datetime:
    return datetime.combine(d, time(hh, mm))


def jordan_sleep() -> list[SleepPattern]:
    weekday = [
        SleepPattern(weekday=i, wake_time=time(7, 0), bed_time=time(23, 0))
        for i in (0, 1, 2, 3, 4, 6)
    ]
    saturday = SleepPattern(weekday=5, wake_time=time(8, 30), bed_time=time(0, 0))
    return sorted(weekday + [saturday], key=lambda p: p.weekday)


COURSES = [
    Course(id="math", name="Calculus I", code="MATH 151"),
    Course(id="bio", name="Biology", code="BIO 110"),
    Course(id="hist", name="History", code="HIST 120"),
    Course(id="eng", name="English", code="ENG 101"),
]


def _weekly(
    id_: str,
    type_: EventType,
    title: str,
    days: list[int],
    start: time,
    end: time,
    location: str,
    course: str | None = None,
    intensity: Intensity = Intensity.NORMAL,
) -> Event:
    return Event(
        id=id_,
        type=type_,
        title=title,
        course_id=course,
        start_time=start,
        end_time=end,
        start_date=SEMESTER_START,
        repeat_weekdays=days,
        location=location,
        intensity=intensity,
    )


def jordan_events() -> list[Event]:
    return [
        _weekly(
            "cls-math",
            EventType.CLASS,
            "MATH 151 Calculus",
            MWF,
            time(9),
            time(9, 50),
            "campus",
            "math",
        ),
        _weekly(
            "cls-bio",
            EventType.CLASS,
            "BIO 110 Biology",
            MWF,
            time(11),
            time(11, 50),
            "campus",
            "bio",
        ),
        _weekly(
            "cls-hist",
            EventType.CLASS,
            "HIST 120 History",
            TTH,
            time(9, 30),
            time(10, 45),
            "campus",
            "hist",
        ),
        _weekly(
            "cls-eng",
            EventType.CLASS,
            "ENG 101 English",
            TTH,
            time(13),
            time(14, 15),
            "campus",
            "eng",
        ),
        # Practice Mon-Thu 3:30-5:30 at the field; Tuesday is marked hard.
        _weekly(
            "prac",
            EventType.PRACTICE,
            "Soccer practice",
            [0, 2, 3],
            time(15, 30),
            time(17, 30),
            "field",
        ),
        _weekly(
            "prac-tue",
            EventType.PRACTICE,
            "Soccer practice (hard)",
            [1],
            time(15, 30),
            time(17, 30),
            "field",
            intensity=Intensity.HARD,
        ),
    ]


def base_input(**extra) -> ScheduleInput:
    data = dict(sleep_patterns=jordan_sleep(), courses=COURSES, events=jordan_events())
    for key, value in extra.items():
        data[key] = data.get(key, []) + value if isinstance(value, list) else value
    return ScheduleInput(**data)


# ----------------------------------------------------------------------------- scenario 1


def scenario_1() -> ScheduleInput:
    """Light Saturday, Oct 10: only a movie 7:30-10:00pm."""
    movie = Event(
        id="movie",
        type=EventType.SOCIAL,
        title="Movie with friends",
        start_time=time(19, 30),
        end_time=time(22, 0),
        start_date=SAT_OCT_10,
        location="cinema",
    )
    tasks = [
        Task(
            id="hist-essay",
            title="HIST essay",
            course_id="hist",
            estimated_hours=6,
            deadline=dt(FRI_OCT_16, 23, 59),
            grade_weight=15,
            difficulty=4,
        ),
        Task(
            id="math-ps",
            title="MATH problem set",
            course_id="math",
            estimated_hours=3,
            deadline=dt(WED_OCT_14, 23, 59),
            grade_weight=3,
            difficulty=3,
        ),
        Task(
            id="eng-reading",
            title="ENG reading",
            course_id="eng",
            estimated_hours=1,
            deadline=dt(TUE_OCT_13, 13, 0),
            grade_weight=2,
            difficulty=1,
        ),
    ]
    return base_input(events=[movie], tasks=tasks)


# ----------------------------------------------------------------------------- scenario 2


def scenario_2() -> ScheduleInput:
    """Wednesday Oct 14: classes plus a home game 4-6pm that replaces practice."""
    game = Event(
        id="game-home",
        type=EventType.GAME,
        title="Home game",
        start_time=time(16),
        end_time=time(18),
        start_date=WED_OCT_14,
        location="stadium",
    )
    no_practice = EventException(event_id="prac", date=WED_OCT_14, cancelled=True)
    tasks = [
        Task(
            id="math-ps",
            title="MATH problem set",
            course_id="math",
            estimated_hours=1.2,
            deadline=dt(THU_OCT_15, 9, 0),
            grade_weight=3,
            difficulty=3,
        ),
        Task(
            id="eng-reading",
            title="ENG reading",
            course_id="eng",
            estimated_hours=40 / 60,
            deadline=dt(THU_OCT_15, 13, 0),
            grade_weight=2,
            difficulty=1,
        ),
        Task(
            id="hist-essay",
            title="HIST essay",
            course_id="hist",
            estimated_hours=3.2,
            deadline=dt(FRI_OCT_16, 23, 59),
            grade_weight=15,
            difficulty=4,
        ),
    ]
    return base_input(events=[game], event_exceptions=[no_practice], tasks=tasks)


# ----------------------------------------------------------------------------- scenario 3


def scenario_3_tasks() -> list[Task]:
    return [
        Task(
            id="hist-essay",
            title="HIST essay",
            course_id="hist",
            estimated_hours=6,
            deadline=dt(FRI_OCT_16, 23, 59),
            grade_weight=15,
            difficulty=4,
        ),
        Task(
            id="bio-lab",
            title="BIO lab report",
            course_id="bio",
            estimated_hours=4.8,
            deadline=dt(FRI_OCT_16, 23, 59),
            grade_weight=10,
            difficulty=3,
        ),
        Task(
            id="math-ps",
            title="MATH problem set",
            course_id="math",
            estimated_hours=2,
            deadline=dt(THU_OCT_15, 9, 0),
            grade_weight=3,
            difficulty=3,
        ),
    ]


def scenario_3() -> ScheduleInput:
    """Mon Oct 12 - Fri Oct 16: two big tasks share a Friday deadline."""
    return base_input(tasks=scenario_3_tasks())


def scenario_3b() -> ScheduleInput:
    """Same week, then an away trip: leave Wed noon, game Thu 7pm, back Thu 10pm."""
    trip = Event(
        id="trip",
        type=EventType.TRAVEL,
        title="Away trip",
        start_time=time(12),
        end_time=time(22),
        start_date=WED_OCT_14,
        end_date=THU_OCT_15,
        is_away=True,
        study_during=StudyDuring.LIGHT,
    )
    game = Event(
        id="game-away",
        type=EventType.GAME,
        title="Away game",
        start_time=time(19),
        end_time=time(21),
        start_date=THU_OCT_15,
        location="away stadium",
        is_away=True,
    )
    # Jordan is away, so Wednesday's and Thursday's practices and Thursday's classes are off.
    away = [
        EventException(event_id="prac", date=WED_OCT_14, cancelled=True),
        EventException(event_id="prac", date=THU_OCT_15, cancelled=True),
        EventException(event_id="cls-hist", date=THU_OCT_15, cancelled=True),
        EventException(event_id="cls-eng", date=THU_OCT_15, cancelled=True),
    ]
    return base_input(events=[trip, game], event_exceptions=away, tasks=scenario_3_tasks())
