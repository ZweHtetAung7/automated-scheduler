# Constraint Review: Version 1 (Student-Athletes, Web)

Review of Aung's v1 description. Three parts: fixes to how existing items are classified, missing constraints, and accuracy safeguards.

## 1. Reclassify a few items

| Item | You listed it as | Should be | Why |
|---|---|---|---|
| Deadline | Soft | **Hard** | Work must finish before it. Urgency (how close it is) is the soft part. |
| Hours required | Soft constraint | **Input** | It's the amount of work to place, not a rule about where to place it. |
| Difficulty, grade weight | Soft | Soft **priority factors** | Correct; they decide order, not feasibility. |
| Recovery time | Hard | Hard, **but tied to events** | Recovery should attach automatically after games or hard practices, not be entered separately each time. |

## 2. Missing hard constraints

1. **Class schedule.** The biggest one. Fixed lecture, lab and section times.
2. **Wake time and minimum sleep hours**, not just bedtime. A 6am lift means an earlier bedtime the night before.
3. **Team commitments beyond practice and games:** lifting, film sessions, team meetings, athletic training or treatment, and mandatory study hall.
4. **Travel and away games:** departure and return times. Long bus or flight time can be marked "light study possible" (readings, flashcards) or "no study."
5. **Travel time between places:** e.g. 15 minutes from the field to the library.
6. **Job or work shifts**, for students who work.
7. **Max total study hours per day**, in addition to max hours per assignment. Without it, five assignments at 2 hours each can fill a whole day.
8. **Minimum and maximum block length:** no 10-minute fragments, and no 4-hour sessions without a break.
9. **Assignment release date:** the earliest date work can start (when it's posted).
10. **Dependencies:** e.g. outline before draft, draft before final, finish the reading before the problem set.
11. **Finish buffer:** finish N hours or a day before the deadline, not the minute before.

## 3. Missing soft constraints and priority factors

1. **Percent complete.** In the original idea, missing from this description. Remaining work = hours required × (1 − percent complete).
2. **Event intensity:** a game day, travel day or two-a-day lowers study capacity more than a light walkthrough.
3. **Pre-game protection:** keep heavy work off the night before and the morning of a game.
4. **Peak focus hours:** put hard assignments in the user's best hours.
5. **Season mode:** in-season, off-season and postseason change weekly capacity a lot. One toggle saves re-entering everything.
6. **Exams with prep time:** exams are events with spaced study sessions before them, not tasks with a due time.
7. **Current standing in the course:** a class the student is struggling in can get a priority boost.
8. **Spread vs. batch preference:** some people prefer one long session, others small daily chunks.
9. **Minimum free/social time per week**, so the schedule stays livable and the student keeps using it.

## 4. Accuracy safeguards

These address the core problem (starting too late) more than any single constraint:

1. **Estimate padding.** Students underestimate. Multiply estimates by about 1.25 by default until logged data replaces it.
2. **Start-by date.** For every assignment, compute and show the latest day it can start and still fit. "Start the history essay by Tuesday" is the warning that prevents last-minute work.
3. **Feasibility check.** When everything can't fit, say so right away and show what to trade off, instead of silently overloading the student.
4. **Weekly re-check:** when a game or travel day is added, immediately flag assignments whose start-by date moved earlier.
5. **Schedule changes from coaches:** practices move often, so moving an event must trigger a re-plan.

## Summary: top five to add first
1. Class schedule
2. Wake time and minimum sleep
3. Other team commitments (lifting, film, treatment, study hall) and away-game travel
4. Max total study hours per day
5. Start-by dates with estimate padding
