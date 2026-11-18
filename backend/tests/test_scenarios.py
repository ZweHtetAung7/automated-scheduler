"""docs/test-days.md as tests. Each test's assertions are that scenario's "Checks" list.

Exact times may shift as the algorithm is tuned; the checks are what must always hold.
"""

from __future__ import annotations

from datetime import time

from app.scheduler import generate_schedule, start_by_changes
from app.scheduler.models import BlockKind, EventType

from . import scenarios as sc
from .checks import assert_hard_constraints, per_task_minutes

# ----------------------------------------------------------------------------- scenario 1


def test_scenario_1_light_saturday():
    inp = sc.scenario_1()
    result = generate_schedule(inp, sc.SAT_OCT_10, sc.SAT_OCT_10)
    day = result.day(sc.SAT_OCT_10)
    assert_hard_constraints(result, inp)

    # 1. Total study is 4.25h, at most 5h.
    assert day.study_minutes() == 255
    # 2. The essay sits inside 9am-12pm.
    essay = [b for b in day.study_blocks() if b.task_id == "hist-essay"]
    assert essay and all(time(9) <= b.start.time() and b.end.time() <= time(12) for b in essay)
    # 3. No task over 2h; none past its preferred 1.5h without a deadline reason.
    for task_id, total in per_task_minutes(result, sc.SAT_OCT_10).items():
        assert total <= 90, task_id
    # 4. (blocks 30-90 min with 10 min breaks: assert_hard_constraints)
    # 5. Nothing overlaps meals, travel or the movie, and the movie is unchanged.
    movie = next(f for f in day.fixed if f.event_id == "movie")
    assert (movie.start.time(), movie.end.time()) == (time(19, 30), time(22, 0))
    travel = [b for b in day.blocks if b.kind == BlockKind.TRAVEL]
    assert [(b.start.time(), b.end.time()) for b in travel] == [
        (time(19, 15), time(19, 30)),
        (time(22, 0), time(22, 15)),
    ]
    # 6. No game, travel or exam rules (no recovery blocks, no 3h cap).
    assert not [b for b in day.blocks if b.kind in (BlockKind.RECOVERY, BlockKind.PRE_GAME)]
    assert day.daily_study_max_minutes == 300
    assert not {"game_rules", "travel_rules"} & set(result.active_rules)
    # 7. Every study block has a reason (assert_hard_constraints), and the essay says why.
    assert "peak_focus" in {r.code for r in essay[0].reasons}


# ----------------------------------------------------------------------------- scenario 2


def test_scenario_2_heavy_class_and_game_day():
    inp = sc.scenario_2()
    result = generate_schedule(inp, sc.WED_OCT_14, sc.WED_OCT_14)
    day = result.day(sc.WED_OCT_14)
    assert_hard_constraints(result, inp)
    study = day.study_blocks()

    # 1. Total study is exactly 3h (game-day cap), not 5h.
    assert day.is_game_day and day.daily_study_max_minutes == 180
    assert day.study_minutes() == 180
    # 2. No difficulty 4-5 work before 12:00pm.
    assert all(b.start.time() >= time(12) for b in study if b.task_id == "hist-essay")
    # 3. Nothing placed from 2:00pm (arrival) to 8:00pm (end of recovery), except dinner.
    assert all(b.end.time() <= time(14) or b.start.time() >= time(20) for b in study)
    dinner = next(b for b in day.blocks if b.title == "Dinner")
    recovery = next(b for b in day.blocks if b.kind == BlockKind.RECOVERY)
    assert (recovery.start.time(), recovery.end.time()) == (time(18), time(20))
    assert recovery.start <= dinner.start and dinner.end <= recovery.end
    # 4. MATH finished before 9:00pm, ENG before 1:00am Thursday.
    assert per_task_minutes(result, sc.WED_OCT_14)["math-ps"] == 90
    assert per_task_minutes(result, sc.WED_OCT_14)["eng-reading"] == 50
    assert max(b.end for b in study if b.task_id == "math-ps").time() <= time(21)
    # 5. Travel blocks between home, campus and stadium.
    titles = [b.title for b in day.blocks if b.kind == BlockKind.TRAVEL]
    assert titles == ["Travel to campus", "Travel to stadium", "Travel home"]
    # 6. The "first game" note is created once.
    assert [n.rule_key for n in result.rule_notices].count("game_rules") == 1
    inp.seen_rule_notices = {"game_rules"}
    again = generate_schedule(inp, sc.WED_OCT_14, sc.WED_OCT_14)
    assert "game_rules" not in [n.rule_key for n in again.rule_notices]
    assert "game_rules" in again.active_rules

    # Your answer to the open question: after a game, light work is preferred...
    eng = next(b for b in study if b.task_id == "eng-reading")
    assert eng.start.time() >= time(20)
    assert "low_energy_light" in {r.code for r in eng.reasons}


def test_scenario_2_heavy_work_still_allowed_after_a_game_when_nothing_else_is_left():
    """...but it is a *soft* rule: with only heavy work left, it may still go after the game."""
    inp = sc.scenario_2()
    inp.tasks = [t for t in inp.tasks if t.id == "hist-essay"]
    inp.tasks[0].estimated_hours = 1.6  # 2h after padding
    result = generate_schedule(inp, sc.WED_OCT_14, sc.WED_OCT_14)
    assert_hard_constraints(result, inp)
    late = [b for b in result.day(sc.WED_OCT_14).study_blocks() if b.start.time() >= time(20)]
    assert late, "heavy work should still be allowed after the game when it's all that's left"


# ----------------------------------------------------------------------------- scenario 3


def test_scenario_3_two_deadlines_colliding():
    inp = sc.scenario_3()
    result = generate_schedule(inp, sc.MON_OCT_12, sc.FRI_OCT_16)
    assert_hard_constraints(result, inp)

    # 1. Essay and lab fully placed before Fri 11:59am; MATH before Wed 9:00pm.
    assert result.task("hist-essay").placed_minutes == 450
    assert result.task("bio-lab").placed_minutes == 360
    assert result.task("math-ps").placed_minutes == 150
    assert not [w for w in result.warnings if w.kind == "shortfall"]
    # 2. No day over 5h, no task over 2h a day (assert_hard_constraints).
    # Essay gets the 2h max (not 1.5h) because 1.5h x 4 days < 7.5h, and its blocks say so.
    essay_per_day = [
        per_task_minutes(result, d).get("hist-essay", 0)
        for d in (sc.MON_OCT_12, sc.TUE_OCT_13, sc.WED_OCT_14, sc.THU_OCT_15, sc.FRI_OCT_16)
    ]
    assert essay_per_day == [120, 120, 120, 90, 0]
    first_essay = next(
        b for b in result.day(sc.MON_OCT_12).study_blocks() if b.task_id == "hist-essay"
    )
    assert "raised_to_max" in {r.code for r in first_essay.reasons}
    # 3. Tuesday has a recovery block 5:30-6:30pm and no study in it.
    tue = result.day(sc.TUE_OCT_13)
    rec = next(b for b in tue.blocks if b.kind == BlockKind.RECOVERY)
    assert (rec.start.time(), rec.end.time()) == (time(17, 30), time(18, 30))
    # 4. No evening has study for more than 2 different courses.
    courses = {t.id: t.course_id for t in inp.tasks}
    for day in result.days:
        evening = {courses[b.task_id] for b in day.study_blocks() if b.start.time() >= time(17)}
        assert len(evening) <= 2, day.date
    # 5. The essay's start-by date is Monday, so a start-by warning shows.
    assert result.task("hist-essay").start_by == sc.MON_OCT_12
    assert any(w.kind == "start_by" and w.task_id == "hist-essay" for w in result.warnings)


def test_scenario_3b_away_trip_added():
    before = generate_schedule(sc.scenario_3(), sc.MON_OCT_12, sc.FRI_OCT_16)
    inp = sc.scenario_3b()
    # 1. Adding the trip triggers a re-plan: here, just calling the engine again.
    result = generate_schedule(inp, sc.MON_OCT_12, sc.FRI_OCT_16)
    # 4. No hard constraint is broken to force a fit.
    assert_hard_constraints(result, inp)

    # 2. The trip blocks non-light study Wed noon - Thu 10pm, and the 3h cap applies.
    for d in (sc.WED_OCT_14, sc.THU_OCT_15):
        day = result.day(d)
        assert day.is_travel_day and day.daily_study_max_minutes == 180
    for b in result.day(sc.WED_OCT_14).study_blocks():
        assert b.end.time() <= time(12)
    assert not result.day(sc.THU_OCT_15).study_blocks()
    # Meals still happen on the trip (dinner moves to after the game, inside recovery).
    thu_meals = [b.title for b in result.day(sc.THU_OCT_15).blocks if b.kind == BlockKind.MEAL]
    assert thu_meals == ["Breakfast", "Lunch", "Dinner"]

    # 3. The work no longer fits: warnings name the essay and the lab, with hours short and options.
    short = {w.task_id: w for w in result.warnings if w.kind == "shortfall"}
    assert set(short) == {"hist-essay", "bio-lab"}
    assert all(w.short_minutes and w.short_minutes > 0 for w in short.values())
    codes = {o.code for o in short["bio-lab"].options}
    assert {"raise_daily_max", "allow_study_during_travel", "ask_extension"} <= codes
    raise_max = next(o for o in short["bio-lab"].options if o.code == "raise_daily_max")
    assert "Mon, Tue" in raise_max.label
    # MATH still fits, because it can't wait (finish-by Wed 9pm).
    assert result.task("math-ps").placed_minutes == 150

    # 4b. Sleep, classes, practice, the trip and recovery stay untouched.
    thu = result.day(sc.THU_OCT_15)
    game = next(f for f in thu.fixed if f.type == EventType.GAME)
    assert (game.start.time(), game.end.time()) == (time(19), time(21))
    assert any(b.kind == BlockKind.RECOVERY for b in thu.blocks)

    # 5. Start-by dates for both tasks move earlier and are flagged (A4).
    moved = {w.task_id for w in start_by_changes(before, result)}
    assert moved == {"hist-essay", "bio-lab"}
