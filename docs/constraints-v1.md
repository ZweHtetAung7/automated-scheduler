# Version 1 Constraints and Ranking Factors

The complete list for v1 (college student-athletes, web). Combines Aung's original list with the additions from [constraints-review.md](constraints-review.md). Items marked ★ are from Aung's original list.

Three kinds of rules:
- **Hard constraints** must never be broken. If they can't all be met, the app says so instead of breaking one.
- **Soft constraints** are preferences. The scheduler tries to honor them and breaks them only when it has to, starting with the least important.
- **Ranking factors** decide which task gets the best time slots first.

---

## 1. Hard constraints

The user has full control over these values.

### Daily structure
| # | Constraint | Example value |
|---|---|---|
| H1 | Wake time (per weekday) | 7:00am, 5:30am on lift days |
| H2 | ★ Bedtime (per weekday) | 11:00pm |
| H3 | Minimum sleep hours | 8 hours (moves bedtime earlier before an early event) |
| H4 | ★ Meal times and length | Breakfast 7:30 (30 min), lunch 12:00 (45 min), dinner 6:30 (45 min) |

### Fixed commitments
| # | Constraint | Example value |
|---|---|---|
| H5 | Class schedule | MWF 9:00–9:50 Calc, TTh 11:00–12:15 History |
| H6 | ★ Practice times | Mon–Thu 3:00–5:30pm |
| H7 | ★ Game times | Sat 1:00pm, arrive 2 hours early |
| H8 | Other team commitments | Lifting, film, team meetings, treatment, mandatory study hall |
| H9 | Away-game travel | Depart Fri 2:00pm, return Sun 6:00pm; mark as "light study OK" or "no study" |
| H10 | Job or work shifts | Tue 6:00–9:00pm |
| H11 | Other fixed personal events | Appointments, club meetings |

### Recovery and transitions
| # | Constraint | Example value |
|---|---|---|
| H12 | ★ Recovery time after games and hard practices | 2 hours after games, 1 hour after hard practices; attached automatically |
| H13 | Travel time between locations | 15 min from field to library |
| H14 | ★ Idle time between tasks | 10 min |

### Workload limits
| # | Constraint | Example value |
|---|---|---|
| H15 | ★ Max hours per assignment per day | 2 hours |
| H16 | Max total study hours per day | 5 hours (lower on game days, see S5) |
| H17 | Minimum block length | 30 min, so no 10-minute scraps |
| H18 | Maximum block length before a break | 90 min |

### Task timing
| # | Constraint | Example value |
|---|---|---|
| H19 | ★ Deadline | Fri 11:59pm |
| H20 | Finish buffer before deadline | Finish 12 hours early |
| H21 | Release date (earliest start) | Assignment posted Monday |
| H22 | Dependencies | Outline before draft, reading before problem set |

---

## 2. Soft constraints (preferences)

Listed from most to least important. When something has to give, the lowest one gives first.

| # | Constraint | What it does |
|---|---|---|
| S1 | ★ Preferred hours per assignment per day | Aim for this; the max (H15) is the hard ceiling |
| S2 | Pre-game protection | No heavy work the night before or the morning of a game |
| S3 | Exam prep spacing | Spread review sessions over the days before an exam |
| S4 | Peak focus hours | Put hard tasks in the user's best hours (e.g. 9am–12pm) |
| S5 | Event intensity | Lower study capacity on game days, travel days and two-a-days |
| S6 | Season mode | In-season, off-season, postseason change weekly capacity |
| S7 | Spread vs. batch | Small daily chunks or fewer long sessions, per user preference |
| S8 | Minimum free/social time per week | Keep the week livable, e.g. 6 hours |
| S9 | Light tasks in low-energy slots | Readings and email after practice or on the bus |
| S10 | Fewer context switches | Avoid bouncing between many courses in one evening |

---

## 3. Inputs per task

Not constraints, but the scheduler needs them for each assignment.

| Input | Notes |
|---|---|
| ★ Hours required | Student's estimate; padded by 25% by default (A1) |
| Percent complete | Remaining hours = hours required × (1 − percent complete) |
| ★ Deadline, release date, dependencies | See H19–H22 |
| ★ Grade weight | % of final grade |
| ★ Difficulty | 1–5 |
| Task type | Assignment, exam, reading, project, lab |
| Course | Links to current standing (R6) |

---

## 4. Ranking factors

Used to decide which task gets placed first and into the best slots.

| # | Factor | How it's measured | Range |
|---|---|---|---|
| R1 | ★ Deadline urgency | Remaining hours ÷ available study hours before the deadline. Above 1.0 means it can't fit. | 0 to 1+ |
| R2 | Start-by pressure | Days until the latest possible start date. 0 means start today. | 0 to 1 (1 = must start now) |
| R3 | ★ Grade weight | % of final grade, scaled | 0 to 1 |
| R4 | ★ Difficulty | 1–5 scaled. Harder tasks rank higher so they get peak hours and earlier starts. | 0 to 1 |
| R5 | ★ Remaining work | Remaining hours, scaled. Bigger jobs need earlier starts. | 0 to 1 |
| R6 | Course standing | Higher for a course the student is struggling in | 0 to 1 |
| R7 | Blocking other tasks | Higher if other tasks depend on this one | 0 or 1 |
| R8 | User boost | The student manually marks a task as important | 0 or 1 |

### Starting formula
```
priority = 0.30 × urgency
         + 0.20 × start_by_pressure
         + 0.20 × grade_weight
         + 0.10 × difficulty
         + 0.10 × remaining_work
         + 0.05 × course_standing
         + 0.05 × blocking
         + user_boost bonus (0.15)
```
These weights are a starting point. Tune them after testing on your three example days.

### Tie-breakers
1. Earlier deadline first
2. Higher grade weight
3. Task the student already started (avoid leaving things half done)

---

## 5. Accuracy safeguards

| # | Safeguard | What it does |
|---|---|---|
| A1 | Estimate padding | Multiply estimates by 1.25 until logged data replaces it |
| A2 | Start-by date | Show the latest day each task can start and still fit |
| A3 | Feasibility check | When hard constraints can't all be met, say what doesn't fit and offer trade-offs |
| A4 | Re-check on changes | A new game, travel day or moved practice re-runs the schedule and flags start-by dates that moved earlier |
