# Daily Schedule Builder for College Students: Design Brainstorm

## Guiding principle: maximum user control

The user controls as much as possible. Every constraint, weight and preference the scheduler uses should be visible and editable by the user, with sensible defaults so the app works before anything is changed.

**Control without nagging.** Users are never forced to fill out constraints they don't care about. Onboarding asks only for the minimum needed to build a first schedule; everything else uses defaults silently. All changes live in a **Customization** area the user opens when they want to, not in prompts or required forms.

**Hard constraints** (sleep, classes, practice, games, meals, commute): entered and edited by the user. Only the few needed for a first schedule are asked up front; the rest start from defaults and are changed in Customization. They have no weights, because the scheduler never breaks them.

**Soft constraint weights** (urgency, grade weight, difficulty, spreading work out, free evenings, and so on): all set by the user.
- Defaults out of the box, so day one works without tuning.
- Plain controls, not raw numbers: sliders or a drag-to-rank "what matters most" list.
- Presets such as "Deadline crunch", "Balanced" and "Protect my rest" as starting points.
- A live preview showing how the day changes as a weight moves.
- Anything learned later (durations, best hours, fatigue) is shown to the user and can be overridden or turned off.

## 1. Should the scheduler use ML to make decisions?

**Short answer: not for the core decisions. Use rules + an optimizer first, and add ML only where it learns from the user's own history.**

### Why rules + optimization fit the core problem

The decision "put less work on a day with four classes and practice" is not something you need to *learn*. You already know the rule: a day's free capacity is the time between wake and sleep, minus classes, athletics, meals, rest and buffers. Once capacity is computed, fewer tasks land on heavy days automatically.

Scheduling is a **constraint problem**: hard limits (deadlines, fixed events, max hours per task per day, sleep) plus soft goals (finish urgent and heavily weighted work first, spread effort, keep breaks). Optimizers solve exactly this, and they give you:

- **Explainability.** "Essay moved to Thursday because Tuesday has 5 hours of class and practice." Students will not trust a schedule they can't understand.
- **Guarantees.** A solver never schedules past a deadline or over a class. An ML model can, and you'd need rules to catch it anyway.
- **No training data needed.** On day one you have zero users and zero logs. ML needs data you don't have yet.
- **Easy tuning.** Changing a weight is a one-line change, not a retrain.

### Where ML genuinely helps (add later)

Use ML for the parts that are *estimation* from personal data, not for the decisions:

| What to learn | Signal | Why it matters |
|---|---|---|
| Real task duration | Planned vs. actual time logged | Students underestimate badly ("planning fallacy"). After a few weeks you can say "your lab reports take ~1.6x what you estimate." |
| Productive hours | When the user actually completes work vs. skips | Puts hard tasks in their best focus window. |
| Fatigue after events | Completion rate on days after games or late nights | Turns a hand-tuned "athletics penalty" into a personal one. |
| Skip / reschedule risk | Which blocks get moved | Add more buffer before risky tasks. |

Start these as simple statistics (averages, ratios per course or task type). Upgrade to real models (regression, gradient boosting) only once simple averages stop being good enough. The learned values feed *into* the optimizer as inputs; the optimizer still makes the decisions.

## 2. Suggested architecture

```
Inputs ──► Capacity per day ──► Task priority ──► Solver ──► Schedule ──► User feedback
                                                                              │
              learned estimates (durations, best hours, fatigue) ◄────────────┘
```

### Step A: Daily capacity
```
available = (day_end - day_start)
          - classes - athletics - gym - social commitments
          - meals - commute - required rest
load_factor = weighted count of hard events (e.g. class=1, practice=1.5, game=2.5)
usable_focus = available × (1 - fatigue_penalty(load_factor))
```
The fatigue penalty is how "lighter loads on heavy days" happens: a day with 2 free hours after 3 classes and a game gets fewer *focus* hours than 2 free hours on an empty Saturday.

### Step B: Task priority score
```
remaining_hours = estimated_total × (1 - percent_complete)
urgency = remaining_hours / hours_available_before_deadline   (>1 means trouble)
priority = w1·urgency + w2·grade_weight + w3·difficulty + w4·user_boost
```

### Step C: Solver
- Start simple: a **greedy scheduler** (highest priority first, earliest feasible slot, respecting per-task daily max and buffers). Good enough for an MVP and easy to debug.
- Upgrade to a **constraint solver** (Google OR-Tools CP-SAT is free and handles this well) when you want globally better schedules, e.g. spreading work evenly or minimizing context switches.

### Step D: Re-plan
Rebuild the schedule whenever something changes: a task is marked done, a block is skipped, a new assignment arrives, or the day starts.

## 3. Features (in scope)

All of these are part of the plan. The grouping is the order they get built, not whether they're in.

### Core (MVP)
- **Fixed events**: class schedule, practices, games, gym, work, social plans. Manual entry first, calendar import later.
- **Assignment input**: deadline, grade weight, estimated hours, percent complete, difficulty.
- **Day start and end** per weekday.
- **Sleep and meal protection**: sleep window and meal blocks are hard constraints, never optional.
- **Per-task limits**: preferred and maximum hours per day.
- **Buffers**: idle time between tasks, plus travel time between locations.
- **Heavy-day awareness**: capacity and fatigue penalty from classes and athletics (Step A).
- **Re-planning**: automatic when a task is done, a block is skipped, or a new assignment arrives, plus a manual button.
- **"Why is this here?"** explanation on every block.

### Phase 2
- **Study sessions**: split tasks into 25 to 90 minute blocks with a minimum length, so there are no 10-minute scraps.
- **Exam prep mode**: spaced review sessions over the days before an exam, not one cram block.
- **Deadline risk warnings**: "At your current pace, the lab report won't fit before Friday. Options: start tonight, shorten gym, or ask for an extension."
- **Energy-aware placement**: hard tasks in peak focus hours, light tasks (email, readings) in low-energy slots.
- **Travel and away games**: block whole days and front-load work before them.
- **Recovery days**: a guaranteed light day after games or big exams.
- **Weekly view** alongside the daily view.
- **Time logging**: start/stop timer or a quick "how long did it take?" check-in. This is the data the ML features need later.

### Phase 3
- **Calendar sync** (Google, Apple, Outlook) and **LMS import** (Canvas, Blackboard, Moodle) for deadlines and grade weights.
- **Flexible vs. fixed social plans**: movable plans can shift, fixed ones can't.
- **Notifications**: start-of-block nudges and an end-of-day review.
- **Burnout signals**: warn when the week has too little rest or too many late nights.
- **What-if planning**: "If I go out Saturday, what moves?"
- **Group projects**: shared availability with teammates.
- **Chatbot** (section 5).
- **Personal estimates from logs**: real durations, best hours, fatigue after events (section 1).

## 4. Inputs to collect (data model sketch)

- **User profile**: day start/end per weekday, sleep target, meal times, preferred break length, max study hours per day, peak focus hours.
- **Fixed events**: title, type (class, practice, game, gym, social, work), start/end, recurring rule, location, intensity, fixed or flexible.
- **Tasks**: course, title, type (assignment, exam, reading, project), deadline, grade weight, estimated hours, percent complete, difficulty, min/preferred/max hours per day, can-split flag, dependencies.
- **Logs**: planned block, actual start/end, completed or skipped, self-rated focus/energy.
- **Chat history**: messages and the edits each one produced, so changes can be undone.

## 5. Chatbot for changing the schedule

The user types something like *"Practice got moved to 6pm tomorrow and I'm wiped, can I skip studying tonight?"* and gets back an updated schedule.

### The key design rule
**The language model translates; the scheduler decides.** The chatbot should not write the schedule itself. It turns the conversation into structured changes to your data (events, tasks, preferences), then the same solver from section 2 rebuilds the schedule. This keeps every guarantee (no work past deadlines, sleep protected, explanations still work) and means the chatbot can't invent an impossible plan.

### How a message flows
```
User message
   │
   ▼
LLM with tools ──► structured edits  (e.g. move_event, add_task, set_day_capacity)
   │                      │
   │                      ▼
   │               validate edits (does the event exist? is the time valid?)
   │                      │
   │                      ▼
   │               solver re-plans  ──► new schedule + diff vs. old schedule
   │                                           │
   ▼                                           ▼
LLM writes a short summary of what changed ◄───┘
   │
   ▼
User sees the diff and confirms (or says "undo" / "no, keep gym")
```

### Tools the chatbot can call
Give the LLM a small set of functions (tool calling / function calling, which all major LLM APIs support). Each maps to one data change:

| Tool | Example message |
|---|---|
| `add_task(title, course, deadline, est_hours, weight)` | "I have a 5 page essay for History due Monday, worth 15%" |
| `update_task(task, percent_complete / est_hours / deadline)` | "I'm about halfway done with the lab report" |
| `add_event / move_event / cancel_event` | "Practice moved to 6pm tomorrow" |
| `set_day_load(date, light/normal/off)` | "I'm exhausted, go easy on me tonight" |
| `block_time(date, start, end, reason)` | "I'm going out Friday night" |
| `set_preference(key, value)` | "Never schedule anything before 9am" |
| `get_schedule(date range)` | "What does Thursday look like?" |
| `explain_block(block)` | "Why is calc homework at 10pm?" |
| `what_if(edits)` | "What happens if I skip the gym this week?" (re-plans without saving) |
| `undo(last change)` | "Undo that" |

### Details worth getting right
- **Confirm before saving.** Show the diff ("Moved: Essay draft from 7pm to tomorrow 2pm. Shortened: gym from 90 to 60 min.") and apply only after the user accepts. Small, obvious edits can auto-apply with an undo button.
- **Ask when it's ambiguous.** "Move my study session" when there are three sessions today should get a question back, not a guess.
- **Resolve relative times.** Pass today's date, the user's timezone and current schedule to the model so "tomorrow", "after practice" and "next Friday" resolve correctly.
- **Say no honestly.** If a request makes a deadline impossible, the solver reports it and the bot explains the tradeoff rather than silently dropping work.
- **Keep the model's context small.** Send the current week's schedule and task list, not the whole history.
- **Log every edit with the message that caused it,** so undo works and you can debug bad interpretations.
- **Test with a fixed set of example messages** and the edits you expect, and rerun them whenever you change the prompt or model.

### Why this order works
The chatbot sits on top of the scheduler and data model, so it's cheap to add once those exist, and none of the core work is wasted. Build the scheduler with a clean API (add task, move event, re-plan) from day one, because those functions become the chatbot's tools with almost no extra work.

## 6. Build order

1. Data model and manual input for events, tasks and preferences.
2. Capacity calculation, priority score and heavy-day fatigue penalty.
3. Greedy scheduler with "why is this here?" explanations, sleep/meal protection and buffers.
4. Re-planning, time logging and deadline risk warnings.
5. Study sessions, exam prep mode, energy-aware placement, recovery days, weekly view.
6. Calendar and LMS import, notifications, burnout signals.
7. Chatbot over the scheduler's API: tools, confirm-and-diff, undo, what-if.
8. Swap greedy for a constraint solver (OR-Tools CP-SAT) if schedules feel poorly balanced.
9. Personal duration and best-hours estimates from logs (simple ratios first, ML later).
