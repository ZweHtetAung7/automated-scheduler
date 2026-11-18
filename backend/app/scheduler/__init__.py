"""Scheduler engine: pure Python, no database or web code.

Pipeline (docs/scheduler-design.md section 2):
    timeline.py   Step A  daily capacity (sleep, events, meals, travel, recovery, fatigue)
    priority.py   Step B  task priority, start-by dates, how much to do today
    placement.py  Step C  greedy placement with explanations
    engine.py             generate_schedule() ties it together and builds warnings
"""

from .engine import explain_block, generate_schedule, start_by_changes
from .models import ScheduleInput, ScheduleResult
from .settings import Settings, resolve_settings

__all__ = [
    "ScheduleInput",
    "ScheduleResult",
    "Settings",
    "explain_block",
    "generate_schedule",
    "resolve_settings",
    "start_by_changes",
]
