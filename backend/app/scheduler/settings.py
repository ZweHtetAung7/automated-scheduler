"""Every setting the scheduler uses, with its default value.

Design rule from docs/data-model.md: *defaults live in code, not in the database.*
The `setting_overrides` table will only store what a user changed, as dotted keys such as
`study.max_hours_per_day` or `weights.urgency`. `resolve_settings()` turns those overrides
into one validated `Settings` object. "Reset to defaults" is just deleting the override row.

Codes in comments (H16, S4, R1, A1...) refer to docs/constraints-v1.md.
"""

from __future__ import annotations

from datetime import time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class _Group(BaseModel):
    # forbid unknown fields so a typo in an override key fails loudly
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SleepSettings(_Group):
    min_hours: float = Field(8.0, ge=4, le=12)  # H3: bedtime moves earlier to protect this


class MealSettings(_Group):
    enabled: bool = True
    breakfast_after_wake_minutes: int = Field(15, ge=0, le=60)  # within 1 hour of waking
    breakfast_minutes: int = 30
    lunch_start: time = time(12, 0)
    lunch_minutes: int = 45
    dinner_start: time = time(18, 30)
    dinner_minutes: int = 45
    max_shift_minutes: int = 30  # meals can move up to 30 min earlier or later to fit events


class StudySettings(_Group):
    max_hours_per_day: float = Field(5.0, gt=0, le=16)  # H16
    preferred_hours_per_task: float = Field(1.5, gt=0)  # S1
    max_hours_per_task: float = Field(2.0, gt=0)  # H15
    min_block_minutes: int = Field(30, ge=5)  # H17
    max_block_minutes: int = Field(90, ge=15)  # H18
    break_minutes: int = Field(10, ge=0)  # H14
    max_courses_per_evening: int = Field(2, ge=1)  # S10
    evening_starts: time = time(17, 0)


class TravelSettings(_Group):
    enabled: bool = True
    minutes_between_places: int = Field(15, ge=0)  # H13
    home_location: str = "home"


class AthleticsSettings(_Group):
    arrive_early_for_games_minutes: int = Field(120, ge=0)  # H7
    season_mode: Literal["in_season", "off_season", "postseason"] = "in_season"  # S6
    # multiplies the daily study max (S6). Off-season frees up time for more study.
    season_study_multiplier: dict[str, float] = {
        "in_season": 1.0,
        "off_season": 1.2,
        "postseason": 1.0,
    }


class RecoverySettings(_Group):
    enabled: bool = True
    after_game_minutes: int = Field(120, ge=0)  # H12
    after_hard_practice_minutes: int = Field(60, ge=0)  # H12


class EnergySettings(_Group):
    peak_start: time = time(9, 0)  # S4
    peak_end: time = time(12, 0)
    light_tasks_in_low_energy: bool = True  # S9 (also covers "prefer light after a game")
    low_energy_hours_after_athletics: float = 2.0
    light_max_difficulty: int = Field(2, ge=1, le=5)  # difficulty <= this counts as "light"
    event_day_capacity_reduction: float = Field(0.4, ge=0, lt=1)  # S5: 5h -> 3h on game/travel days


class FatigueSettings(_Group):
    """Step A of scheduler-design.md: heavy days get fewer *usable* focus hours."""

    penalty_per_load_unit: float = 0.05
    max_penalty: float = 0.5
    load_weights: dict[str, float] = {
        "class": 1.0,
        "practice": 1.5,
        "game": 2.5,
        "team_other": 0.5,
        "travel": 2.0,
        "work": 1.0,
        "exam": 1.5,
        "social": 0.5,
        "other": 0.5,
    }
    intensity_multiplier: dict[str, float] = {"light": 0.5, "normal": 1.0, "hard": 1.5}


class PregameSettings(_Group):
    enabled: bool = True  # S2
    morning_until: time = time(12, 0)
    night_before_from: time = time(20, 0)
    heavy_min_difficulty: int = Field(4, ge=1, le=5)  # 4-5 counts as heavy


class DeadlineSettings(_Group):
    finish_buffer_hours: float = Field(12.0, ge=0)  # H20
    estimate_padding: float = Field(1.25, ge=1.0, le=3.0)  # A1
    start_by_warnings: bool = True  # A2


class WeightSettings(_Group):
    """Ranking weights R1-R8 (the "Balanced" preset)."""

    urgency: float = 0.30
    start_by: float = 0.20
    grade_weight: float = 0.20
    difficulty: float = 0.10
    remaining_work: float = 0.10
    course_standing: float = 0.05
    blocking: float = 0.05
    important_bonus: float = 0.15


class ScaleSettings(_Group):
    """How raw task values are scaled to 0-1 before weighting."""

    grade_weight_full_at: float = 25.0  # a task worth >= 25% of the grade scores 1.0
    remaining_full_at_hours: float = 10.0  # >= 10h of remaining work scores 1.0
    start_by_horizon_days: int = (
        7  # start-by pressure is 0 when the start-by date is >= 7 days away
    )


class Settings(_Group):
    sleep: SleepSettings = SleepSettings()
    meals: MealSettings = MealSettings()
    study: StudySettings = StudySettings()
    travel: TravelSettings = TravelSettings()
    athletics: AthleticsSettings = AthleticsSettings()
    recovery: RecoverySettings = RecoverySettings()
    energy: EnergySettings = EnergySettings()
    fatigue: FatigueSettings = FatigueSettings()
    pregame: PregameSettings = PregameSettings()
    deadlines: DeadlineSettings = DeadlineSettings()
    weights: WeightSettings = WeightSettings()
    scale: ScaleSettings = ScaleSettings()


class UnknownSettingError(KeyError):
    pass


def resolve_settings(overrides: dict[str, Any] | None = None) -> Settings:
    """Defaults + the user's overrides -> validated Settings.

    >>> resolve_settings({"study.max_hours_per_day": 6}).study.max_hours_per_day
    6.0
    """
    data = Settings().model_dump()
    for key, value in (overrides or {}).items():
        group, _, field = key.partition(".")
        if group not in data or field not in data[group]:
            raise UnknownSettingError(key)
        data[group][field] = value
    return Settings.model_validate(data)


def changed_keys(overrides: dict[str, Any]) -> set[str]:
    """Keys whose value really differs from the default (for "changed from default" markers)."""
    defaults = Settings().model_dump()
    resolved = resolve_settings(overrides).model_dump()
    return {
        key
        for key in overrides
        if resolved[key.partition(".")[0]][key.partition(".")[2]]
        != defaults[key.partition(".")[0]][key.partition(".")[2]]
    }
