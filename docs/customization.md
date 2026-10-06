# Customization: Groups, Defaults and Plan

Follows the guiding principle in [scheduler-design.md](scheduler-design.md): the user controls everything, but is never made to fill out what they don't care about. Codes (H1, S4, R3, A1) refer to [constraints-v1.md](constraints-v1.md).

**Onboarding asks for only three things** (marked **Start** below): class schedule, team schedule (practices and games), and wake/bed times. Everything else starts at its default and is changed later in Customization.

**Event-triggered constraints** (marked **On event** below) are ignored until the user adds that kind of event. A user with no games never sees or is affected by game recovery, pre-game protection or game-day capacity. When they add their first game, those rules switch on with their defaults, and the app shows them once in a short note ("Added 2 hours of recovery after this game; change in Customization").

Default values are proposals for Aung to review.

---

## Part 1: Groups and defaults

### Group 1. Sleep and daily rhythm
| Setting | Default | Asked at |
|---|---|---|
| Bedtime (H2) | User picks a bedtime for each day of the week, or taps **Same every day** and picks one. Pre-filled at 11:00pm | **Start** |
| Wake time (H1) | Same picker as bedtime: per day or **Same every day**. Pre-filled at 7:00am | **Start** |
| One-day change | Any time, the user can change wake or bed time for one specific date (e.g. "bed at 1am this Friday") without touching the weekly pattern | Anytime, from the day view |
| Minimum sleep (H3) | 8 hours; bedtime moves earlier before an early event | Customization |

### Group 2. Meals
| Setting | Default | Asked at |
|---|---|---|
| Breakfast (H4) | 30 min, within 1 hour of waking | Customization |
| Lunch | 12:00pm, 45 min | Customization |
| Dinner | 6:30pm, 45 min (moves after practice if they overlap) | Customization |
| Meals can shift | Up to 30 min earlier or later to fit events | Customization |

### Group 3. Classes and fixed commitments
| Setting | Default | Asked at |
|---|---|---|
| Class schedule (H5) | None | **Start** |
| Job or work shifts (H10) | None | Customization (rules apply only once a shift is added) |
| Other fixed events (H11) | None | Customization |
| Social plans: flexible or fixed | Fixed | Customization |

### Group 4. Athletics
| Setting | Default | Asked at |
|---|---|---|
| Practice times (H6) | None | **Start** |
| Game times (H7) | None | **Start** |
| Arrive early for games | 2 hours | **On event**: first game |
| Other team commitments (H8): lift, film, treatment, study hall | None | Customization |
| Away-game travel (H9) | Marked "light study OK" | **On event**: first away trip |
| Season mode (S6) | In-season | Customization |

### Group 5. Recovery and rest
| Setting | Default | Asked at |
|---|---|---|
| Recovery after games (H12) | 2 hours | **On event**: first game |
| Recovery after hard practices | 1 hour | **On event**: first practice marked hard |
| Pre-game protection (S2) | No heavy work the night before or morning of a game | **On event**: first game |
| Minimum free/social time per week (S8) | 6 hours | Customization |

### Group 6. Study limits and blocks
| Setting | Default | Asked at |
|---|---|---|
| Max study hours per day (H16) | 5 hours (3 on game and travel days, once those exist) | Customization |
| Preferred hours per assignment per day (S1) | 1.5 hours | Customization |
| Max hours per assignment per day (H15) | 2 hours | Customization |
| Minimum block length (H17) | 30 min | Customization |
| Max block before a break (H18) | 90 min | Customization |
| Break between tasks (H14) | 10 min | Customization |
| Travel time between places (H13) | 15 min | Customization |
| Spread vs. batch (S7) | Spread (small daily chunks) | Customization |
| Fewer context switches (S10) | On, max 2 courses per evening | Customization |

### Group 7. Energy and focus
| Setting | Default | Asked at |
|---|---|---|
| Peak focus hours (S4) | 9:00am to 12:00pm | Customization |
| Light tasks in low-energy slots (S9) | On (after practice, on the bus) | Customization |
| Event intensity (S5) | Game day and travel day lower capacity by 40% | **On event**: first game or trip |

### Group 8. Deadlines and safety margins
| Setting | Default | Asked at |
|---|---|---|
| Finish buffer before deadline (H20) | 12 hours | Customization |
| Estimate padding (A1) | 25% extra on every estimate | Customization |
| Exam prep spacing (S3) | 4 review sessions over the 7 days before an exam | **On event**: first exam |
| Start-by warnings (A2) | On | Customization |

### Group 9. Priorities (ranking weights)
Shown as a drag-to-rank list or sliders, not numbers. Default preset: **Balanced**.

| Factor | Default weight |
|---|---|
| Deadline urgency (R1) | 30% |
| Start-by pressure (R2) | 20% |
| Grade weight (R3) | 20% |
| Difficulty (R4) | 10% |
| Remaining work (R5) | 10% |
| Course standing (R6) | 5% |
| Blocking other tasks (R7) | 5% |
| "Important" flag bonus (R8) | +15% |

### Group 10. Task defaults (pre-filled when adding a task)
| Setting | Default |
|---|---|
| Difficulty | 3 of 5 |
| Grade weight | 5% |
| Percent complete | 0% |
| Task type | Assignment |

---

## Part 2: What the Customization area will include

1. **The ten groups above** as sections, each with a "Reset to defaults" button.
2. **Presets** that set many values at once:
   - **Balanced** (default)
   - **Deadline crunch:** urgency weighted higher, max study hours raised, free time lowered
   - **Protect my rest:** more sleep and recovery, lower daily study max
   - **Off-season:** higher weekly capacity, less recovery time
3. **Priority ranking** as a drag-to-rank list or sliders (Group 9), never raw numbers.
4. **Sleep schedule:** wake and bed time per day of the week or "Same every day", plus one-day changes from the day view at any time. Per-weekday meals and study max stay off until the user turns them on.
5. **Season mode switch** (in-season, off-season, postseason) in one tap.
6. **Live preview:** a before/after of today's schedule while a setting changes, with "Apply" or "Cancel".
7. **Changed-from-default markers** so the user can see what they customized.
8. **Event-triggered rules** appear in Customization only after the matching event exists (games, away trips, hard practices, exams).
9. **Required vs. optional toggles:** each hard constraint except sleep and classes can be turned off entirely.
10. **Learned values panel (later, Phase 5):** shows what the app learned (e.g. "your essays take 1.4× your estimate") with the option to accept, edit or turn each one off.
