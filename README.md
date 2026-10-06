# Automatic Scheduler

A web-based day planner for college student-athletes who keep missing deadlines or starting assignments too late, not from carelessness, but because there is simply too much on their plate.

Automatic Scheduler builds each day from your tasks (how long they take, how urgent they are, how much is already done) and your personal constraints. **Hard constraints** such as classes, practice, games, sleep and meals are never broken, and you can change any of them. **Soft constraints** such as urgency, grade weight and spreading work out decide how the remaining time is used.

The first version targets college students active in extracurriculars, especially sports, and runs on the web.

## Guiding principle

**You stay in control, without the busywork.** You only enter what's needed to get your first schedule; everything else starts from sensible defaults. When you want to change something, every constraint, weight and preference is in the Customization area, with simple sliders and presets like "Deadline crunch", "Balanced" and "Protect my rest".

- **Sign-up asks for three things:** your class schedule, your practices and games, and your wake and bed times (per day, or "same every day").
- **Change any single day:** adjust wake or bed time for a specific date whenever you want, without touching your weekly pattern.
- **Rules appear when they matter:** game recovery, pre-game protection, travel-day limits and exam prep only switch on once you add a game, trip or exam.

## How it works

1. **Daily capacity.** Free time between wake and sleep, minus classes, athletics, meals, commute and required rest. Heavy days get a fatigue penalty, so fewer focus hours land on them.
2. **Task priority.** Remaining hours (estimate × (1 − % complete)) against time left before the deadline, plus grade weight, difficulty and a manual boost.
3. **Placement.** A greedy scheduler places the highest-priority work in the earliest feasible slot, respecting per-task daily limits, buffers, sleep and meals. Google OR-Tools CP-SAT can replace it later.
4. **Explanations.** Every block says why it was placed where it is.
5. **Re-planning.** The schedule updates when tasks finish, blocks are skipped, or new tasks arrive.

Machine learning is used later only to learn personal estimates (real task durations, best focus hours, fatigue), which feed into the scheduler as inputs.

## Tech stack

| Layer | Choice |
|---|---|
| Frontend | React + TypeScript + Vite, Tailwind CSS + shadcn/ui, FullCalendar, TanStack Query |
| Backend | Python 3.12 + FastAPI, Pydantic, SQLAlchemy + Alembic |
| Database / auth | PostgreSQL via Supabase (SQLite while prototyping) |
| Scheduler | Pure-Python greedy algorithm, OR-Tools CP-SAT later |
| AI | Claude API with tool use (chatbot, hour estimates, syllabus parsing) |
| Testing | pytest, Vitest, Playwright |
| Lint / format | Ruff (Python), oxlint (TypeScript) |
| CI / hosting | GitHub Actions; Vercel (frontend), Render or Railway (backend) |

## Project layout

Folders marked *(later)* don't exist yet.

```
frontend/         React app
backend/
  app/
    api/          FastAPI routes
    models/       SQLAlchemy tables (later)
    schemas/      Pydantic shapes (later)
    scheduler/    defaults, capacity, priority, placement, explanations (pure Python)
    chatbot/      tool definitions, prompt, message handler (later)
    importers/    .ics, syllabus scanning, Canvas (later)
  tests/
docs/             design notes
```

## Roadmap

| Phase | Focus |
|---|---|
| 0 | Foundations: data model, rules, three hand-worked test days |
| 1 | Core scheduler MVP: engine API, greedy placement, basic screens |
| 2 | Living schedule: re-planning, time logging, deadline warnings, weekly view |
| 3 | Integrations: calendar and Canvas import, notifications, burnout signals |
| 4 | Chatbot: edit the schedule in plain language, with diff and undo |
| 5 | Learning from the user: personal duration and energy estimates, solver upgrade |

## Running locally

Requires Python 3.12+ with [uv](https://docs.astral.sh/uv/), and Node 22+.

**Backend** (http://localhost:8000, API docs at `/docs`):
```
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

**Frontend** (http://localhost:5173, forwards `/api` to the backend):
```
cd frontend
npm install
npm run dev
```

**Checks** (the same ones CI runs on every push):
```
cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest
cd frontend && npm run lint && npm test && npm run build
```

## Status

Phase 1 started: project skeleton with backend, frontend and CI. Next: the core scheduler. See `docs/` for the full design notes.
