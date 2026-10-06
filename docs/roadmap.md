# Design Roadmap: Daily Schedule Builder

Each phase lists what to design, the key decisions, and how you know it's done. Finish the design of a phase before building it, but don't design later phases in detail yet; what you learn building phase 1 will change them.

Companion to [scheduler-design.md](scheduler-design.md), which has the formulas, feature details and chatbot design.

---

## Phase 0: Foundations (design first, before any code)

**Design**
1. **Problem statement and target user.** One paragraph: who (e.g. a student-athlete with 4–5 classes), what pain (too many deadlines, no time sense), what success looks like (fewer missed deadlines, sleep protected).
2. **Platform decision.** Recommended default: a web app first (works on phone and laptop, one codebase), with a mobile app later.
3. **Tech stack.** Recommended default: Python backend (FastAPI) because the solver library OR-Tools and later ML work are easiest in Python; React frontend; PostgreSQL (or SQLite while prototyping).
4. **Data model.** Entities and fields for User/Profile, FixedEvent, Task, ScheduledBlock, Log. Draw it as an ER diagram.
5. **Scheduling rules on paper.** Write out the hard constraints (sleep, meals, classes, deadlines, max hours per task per day) and soft goals (urgency, grade weight, spread, breaks), with the capacity and priority formulas.
6. **Three test scenarios** worked out by hand: a light Saturday, a heavy class+game day, and a week with two deadlines colliding. These become your first automated tests.

**Done when** you can schedule the three scenarios by hand using only your written rules, and you'd be happy with the result.

---

## Phase 1: Core scheduler (MVP)

**Design**
1. **Scheduler engine API.** Clean functions the UI (and later the chatbot) call: `add_task`, `update_task`, `add_event`, `move_event`, `set_preference`, `generate_schedule(date_range)`, `explain_block(block)`.
2. **Capacity calculation** per day, including the heavy-day fatigue penalty.
3. **Priority score** from deadline urgency, grade weight, remaining work, difficulty.
4. **Greedy placement algorithm** with buffers, per-task daily limits, sleep and meal protection.
5. **Explanations.** What reason text each block stores ("placed here because…").
6. **Screens** (wireframes): onboarding (day start/end, sleep, meals, breaks), class and activity entry, task entry, daily schedule view.

**Done when** a new user can enter their week and get a believable daily schedule, and the three Phase 0 scenarios pass as tests.

---

## Phase 2: Living schedule

**Design**
1. **Re-plan triggers:** task completed, block skipped, new task, start of day. Decide what stays locked (blocks already started) vs. what moves.
2. **Time logging:** the check-in flow ("done? how long did it take?") and the Log table.
3. **Deadline risk warnings:** when to warn, and what options to offer.
4. **Study sessions:** session length rules and minimum block size.
5. **Exam prep mode:** how review sessions are spaced before an exam.
6. **Energy-aware placement:** how peak hours are entered and used.
7. **Recovery days and travel/away games.**
8. **Screens:** weekly view, check-in prompt, warning cards, task detail with progress.

**Done when** you can use it yourself for two real weeks without manually fixing the schedule more than occasionally.

---

## Phase 3: Integrations and wellbeing

**Design**
1. **Calendar sync** (Google first): one-way import of classes/events, then optional export of study blocks.
2. **LMS import** (Canvas first, since its API is common at colleges): assignments, due dates, grade weights.
3. **Notifications:** which ones, when, and how users turn them off.
4. **Burnout signals:** the thresholds (rest hours per week, late nights) and how warnings are shown.
5. **Flexible vs. fixed social plans** and **what-if planning** (re-plan without saving).
6. **Accounts and privacy:** login, where data lives, deleting an account.

**Done when** a new user can be set up mostly by import instead of typing everything in.

---

## Phase 4: Chatbot

**Design**
1. **Tool list:** map each engine API function from Phase 1 to a chatbot tool, plus `what_if` and `undo`.
2. **Conversation flow:** message → edits → validate → re-plan → diff → confirm.
3. **Diff display:** how changes are shown in chat (moved / shortened / added / removed).
4. **Ambiguity rules:** when the bot asks a question back instead of guessing.
5. **Context sent to the model:** today's date, timezone, current week's schedule and tasks.
6. **Test set:** 30–50 example messages with the edits you expect, rerun on every prompt or model change.
7. **Chat screen** next to (or on top of) the schedule view.

**Done when** the bot handles your test set correctly and undo always works.

---

## Phase 5: Learning from the user

**Design**
1. **Duration correction:** per course or task type, actual ÷ estimated time from logs, applied to new estimates.
2. **Best hours:** completion rate by hour of day.
3. **Personal fatigue:** completion rate on days after heavy events, replacing the hand-tuned penalty.
4. **Solver upgrade:** switch from greedy to OR-Tools CP-SAT if schedules feel unbalanced.
5. **When to trust learned values:** minimum amount of data before they override defaults.

**Done when** schedules measurably fit the user better than the defaults (fewer skipped and overrun blocks).

---

## Summary

| Phase | Focus | Main design output |
|---|---|---|
| 0 | Foundations | Data model, rules, hand-worked scenarios |
| 1 | Core scheduler | Engine API, algorithm, MVP screens |
| 2 | Living schedule | Re-planning, logging, warnings, weekly view |
| 3 | Integrations | Calendar/LMS import, notifications, burnout |
| 4 | Chatbot | Tools, conversation flow, diff and undo |
| 5 | Learning | Personal estimates, solver upgrade |

## Next version

Parked ideas live in [next-version-notes.md](next-version-notes.md). First one: estimating hours from the assignment description.
