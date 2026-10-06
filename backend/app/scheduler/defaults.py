"""Default settings from docs/customization.md.

Defaults live in code; the database stores only the settings a user changes.
Keys are dotted "group.setting" names, matching the setting_overrides table.
Durations are in minutes, times are "HH:MM" local time.
"""

from typing import Any

DEFAULT_SETTINGS: dict[str, Any] = {
    # Group 1. Sleep and daily rhythm
    "sleep.same_every_day": True,
    "sleep.wake_time": "07:00",
    "sleep.bed_time": "23:00",
    "sleep.min_hours": 8,
    # Group 2. Meals
    "meals.breakfast_minutes": 30,
    "meals.breakfast_within_minutes_of_wake": 60,
    "meals.lunch_time": "12:00",
    "meals.lunch_minutes": 45,
    "meals.dinner_time": "18:30",
    "meals.dinner_minutes": 45,
    "meals.max_shift_minutes": 30,
    # Group 3. Classes and fixed commitments
    "commitments.social_plans_flexible": False,
    # Group 4. Athletics (event-triggered rules switch on with the first matching event)
    "athletics.arrive_early_for_games_minutes": 120,
    "athletics.away_travel_study": "light",
    "athletics.season_mode": "in_season",
    # Group 5. Recovery and rest
    "recovery.after_game_minutes": 120,
    "recovery.after_hard_practice_minutes": 60,
    "recovery.pre_game_protection": True,
    "recovery.min_free_hours_per_week": 6,
    # Group 6. Study limits and blocks
    "study.max_hours_per_day": 5,
    "study.max_hours_game_or_travel_day": 3,
    "study.preferred_hours_per_task_per_day": 1.5,
    "study.max_hours_per_task_per_day": 2,
    "study.min_block_minutes": 30,
    "study.max_block_minutes": 90,
    "study.break_minutes": 10,
    "study.travel_minutes": 15,
    "study.spread_work": True,
    "study.max_courses_per_evening": 2,
    # Group 7. Energy and focus
    "energy.peak_start": "09:00",
    "energy.peak_end": "12:00",
    "energy.light_tasks_in_low_energy_slots": True,
    "energy.game_or_travel_capacity_reduction": 0.40,
    # Group 8. Deadlines and safety margins
    "deadlines.finish_buffer_hours": 12,
    "deadlines.estimate_padding": 0.25,
    "deadlines.exam_review_sessions": 4,
    "deadlines.exam_review_days": 7,
    "deadlines.start_by_warnings": True,
    # Group 9. Priorities (Balanced preset)
    "weights.urgency": 0.30,
    "weights.start_by_pressure": 0.20,
    "weights.grade_weight": 0.20,
    "weights.difficulty": 0.10,
    "weights.remaining_work": 0.10,
    "weights.course_standing": 0.05,
    "weights.blocking": 0.05,
    "weights.important_bonus": 0.15,
    # Group 10. Task defaults
    "task.difficulty": 3,
    "task.grade_weight": 5,
    "task.percent_complete": 0,
    "task.type": "assignment",
}


def effective_settings(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Defaults with the user's changes applied. Unknown keys are rejected."""
    overrides = overrides or {}
    unknown = set(overrides) - set(DEFAULT_SETTINGS)
    if unknown:
        raise KeyError(f"Unknown setting(s): {', '.join(sorted(unknown))}")
    return {**DEFAULT_SETTINGS, **overrides}
