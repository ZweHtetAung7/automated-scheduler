# Test Days (Phase 0)

Three scenarios worked out by hand with the v1 defaults from [customization.md](customization.md). Each one becomes a pytest case: the inputs are the fixture, and the checks at the end are the assertions. Exact times can shift a little as the algorithm is tuned; the checks are what must always hold.

**Aung to review:** does each expected day look like a schedule you would actually follow? If not, the rule that produced it needs changing, not the test.

---

## Shared student profile

Jordan, a soccer player. Timezone America/New_York.

| Item | Value |
|---|---|
| Sleep | Wake 7:00am, bed 11:00pm Sun–Fri. Saturday: wake 8:30am, bed 12:00am (per-day pattern) |
| Classes (campus) | MATH 151 Calculus: MWF 9:00–9:50 · BIO 110 Biology: MWF 11:00–11:50 · HIST 120 History: TTh 9:30–10:45 · ENG 101 English: TTh 1:00–2:15 |
| Practice (field) | Mon–Thu 3:30–5:30pm, Tuesday marked hard (unless a scenario says otherwise) |
| Settings | All defaults: 5h study max per day (3h on game/travel days), 1.5h preferred / 2h max per task per day, blocks 30–90 min, 10 min breaks, 15 min travel between different places, 25% estimate padding, finish 12h before deadline, peak focus 9am–12pm |

Hours below are **after** the 25% padding.

**Placement rule used by hand** (greedy): place tasks in priority order; each task gets its preferred 1.5h per day (up to 2h if the deadline needs it); fill the earliest free slots, splitting into blocks of at least 30 min and never leaving a piece shorter than 30 min.

---

## Scenario 1: Light Saturday

**Date:** Saturday, Oct 10. No classes, no practice, no game.

**Fixed:** Movie with friends 7:30–10:00pm (off campus, fixed).

**Tasks**
| Task | Remaining | Deadline | Grade | Difficulty |
|---|---|---|---|---|
| HIST essay | 7.5h (0% done) | Fri Oct 16, 11:59pm | 15% | 4 |
| MATH problem set | 3.75h (0% done) | Wed Oct 14, 11:59pm | 3% | 3 |
| ENG reading | 1.25h (0% done) | Tue Oct 13, 1:00pm | 2% | 1 |

**Expected day**
| Time | Block | Why |
|---|---|---|
| 8:30 | Wake | Saturday pattern |
| 8:45–9:15 | Breakfast | Within an hour of waking |
| 9:15–10:45 | HIST essay (1.5h) | Highest priority and hardest, so it gets peak focus hours |
| 10:55–11:55 | MATH problem set (1h) | Next priority; 65 min before lunch, but using all of it would leave a 25 min scrap |
| 12:00–12:45 | Lunch | |
| 12:55–1:25 | MATH problem set (30 min) | Finishes today's 1.5h |
| 1:35–2:50 | ENG reading (1.25h) | Whole task fits in one block |
| 2:50–6:30 | Free | Daily study is well under the max, so the rest is free |
| 6:30–7:15 | Dinner | |
| 7:15–7:30 | Travel | Different location |
| 7:30–10:00 | Movie | Fixed, never moved |
| 10:00–10:15 | Travel | |
| 12:00am | Bed | Saturday pattern |

**Checks**
1. Total study is 4.25h, at most 5h.
2. The essay sits inside 9am–12pm.
3. No task gets more than 2h; none goes past its preferred 1.5h without a deadline reason.
4. Every block is 30–90 min, with at least 10 min between study blocks.
5. Nothing overlaps meals, travel or the movie, and the movie is unchanged.
6. No game, travel or exam rules appear (no recovery blocks, no 3h cap), because there are no such events.
7. Every study block has a reason.

---

## Scenario 2: Heavy class and game day

**Date:** Wednesday, Oct 14. Home game replaces practice.

**Fixed:** MATH 9:00–9:50, BIO 11:00–11:50 (campus). Home game 4:00–6:00pm at the stadium.

**Rules that switch on** (first game): arrive 2h early (2:00pm), 2h recovery after (6:00–8:00pm), no heavy work (difficulty 4–5) before noon, game-day study max of 3h.

**Tasks**
| Task | Remaining | Deadline | Finish by (12h buffer) | Grade | Difficulty |
|---|---|---|---|---|---|
| MATH problem set | 1.5h | Thu Oct 15, 9:00am | Wed 9:00pm | 3% | 3 |
| ENG reading | 50 min | Thu Oct 15, 1:00pm | Thu 1:00am | 2% | 1 |
| HIST essay | 4h | Fri Oct 16, 11:59pm | Fri 11:59am | 15% | 4 |

Priority order: MATH (must finish today), then ENG (must also finish tonight), then the essay (has two more days).

**Expected day**
| Time | Block | Why |
|---|---|---|
| 7:00 | Wake | |
| 7:15–7:45 | Breakfast | |
| 7:45–8:45 | MATH problem set (1h) | Due tonight; not heavy, so allowed on game morning |
| 8:45–9:00 | Travel to campus | |
| 9:00–9:50 | MATH class | |
| 10:00–10:30 | MATH problem set (30 min) | Finishes it, well before 9pm |
| 10:30–11:00 | Free | 20 min left after the break, too short for a block |
| 11:00–11:50 | BIO class | |
| 12:00–12:45 | Lunch | |
| 12:55–1:45 | ENG reading (50 min) | Light task before the game |
| 1:45–2:00 | Travel to stadium | |
| 2:00–4:00 | Pre-game (arrive early) | Game rule |
| 4:00–6:00 | Game | |
| 6:00–8:00 | Recovery, with dinner 6:30–7:15 inside it | Game rule; eating during recovery is allowed |
| 8:00–8:40 | HIST essay (40 min) | Only 40 min of the 3h game-day cap remains |
| 8:40–11:00 | Free | |
| 11:00 | Bed | |

**Checks**
1. Total study is exactly 3h (game-day cap), not 5h.
2. No difficulty 4–5 work before 12:00pm.
3. Nothing is placed from 2:00pm (arrival) to 8:00pm (end of recovery), except dinner.
4. MATH is finished before 9:00pm and ENG before 1:00am Thursday.
5. Travel blocks appear between home, campus and stadium.
6. The "first game" note is created once (rule_activations).

**Open question for Aung:** the essay lands at 8:00pm right after a game. Should post-game evenings allow only light tasks? If yes, the essay gets 0h today and moves to Thursday.

---

## Scenario 3: Two deadlines colliding

**Dates:** Monday Oct 12 to Friday Oct 16. Normal class and practice week (Tuesday practice is hard, so 1h recovery 5:30–6:30pm).

**Tasks**
| Task | Remaining | Deadline | Finish by | Grade | Difficulty |
|---|---|---|---|---|---|
| HIST essay | 7.5h | Fri 11:59pm | Fri 11:59am | 15% | 4 |
| BIO lab report | 6h | Fri 11:59pm | Fri 11:59am | 10% | 3 |
| MATH problem set | 2.5h | Thu 9:00am | Wed 9:00pm | 3% | 3 |

16h of work across four days. Two big tasks share the same deadline.

**Expected study hours per day**
| Day | Essay | Lab | Math | Total |
|---|---|---|---|---|
| Mon | 2.0 | 1.5 | 1.25 | 4.75 |
| Tue | 2.0 | 1.5 | 1.25 | 4.75 |
| Wed | 2.0 | 1.5 | 0 | 3.5 |
| Thu | 1.5 | 1.5 | 0 | 3.0 |
| Fri | 0 | 0 | 0 | 0 |

The essay gets the 2h max, not the 1.5h preferred, because 1.5h × 4 days = 6h is less than the 7.5h needed. Its blocks should say so.

**Checks**
1. Essay and lab are fully placed and finish before Fri 11:59am; MATH finishes before Wed 9:00pm.
2. No day goes over 5h, and no task over 2h in a day.
3. Tuesday has a recovery block 5:30–6:30pm and no study in it.
4. No evening has study for more than 2 different courses.
5. The essay's start-by date is Monday, so a start-by warning shows if it hasn't started by then.

### Scenario 3b: same week, then an away trip is added

On Monday morning, Jordan adds an away game trip: leave Wed 12:00pm, game Thu 7:00pm, return Thu 10:00pm, marked "light study only". None of the three tasks are light (difficulty 3–4).

**Expected**
1. Adding the trip triggers a re-plan immediately.
2. The trip blocks all study from Wed noon to Thu 10pm except light tasks, and the travel/game-day cap of 3h applies.
3. The work no longer fits. The app shows a warning naming the essay and the lab, how many hours each is short, and options, for example:
   - Raise the daily study max on Mon and Tue
   - Allow normal study during travel
   - Use some of this week's free time
   - Ask for an extension
4. No hard constraint is broken to force a fit: sleep, meals, classes, practice, the trip and recovery stay untouched.
5. Start-by dates for both tasks move earlier and are flagged.
