# Tech Stack: Daily Schedule Builder

Chosen for: a 2.5-week build with an AI coding agent, a web app first, and Python for the scheduler, chatbot and later ML. Everything here is popular and well documented, which matters because AI agents write much better code for mainstream tools.

## At a glance

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + TypeScript + Vite | Most common setup; agents handle it well |
| Styling / UI | Tailwind CSS + shadcn/ui | Good-looking components fast |
| Calendar views | FullCalendar (React) | Day and week views with drag-to-move built in |
| Data fetching | TanStack Query | Caching and refetch after re-plans |
| Backend | Python 3.12 + FastAPI | Fast to write, auto API docs, same language as solver and ML |
| Validation | Pydantic | Shared shapes for API, chatbot tools and LLM output |
| Database | PostgreSQL (SQLite while prototyping) | Reliable, free tiers everywhere |
| ORM / migrations | SQLAlchemy + Alembic | Standard for FastAPI |
| Auth + file storage | Supabase (Postgres + Auth + Storage) | One service for database, login and uploaded syllabi |
| Scheduler | Your own greedy algorithm in Python | Simple, debuggable, enough for the MVP |
| Solver (later) | Google OR-Tools CP-SAT | Free, handles constraint scheduling well |
| LLM | Claude API with tool use (`anthropic` Python SDK) | Chatbot, hour estimates, syllabus parsing |
| PDF / image parsing | pdfplumber for text; Claude vision for photos and scanned PDFs | Covers course calendar scanning |
| Calendar import | `icalendar` (.ics files) now; Google Calendar API later | .ics import is a cheap win without OAuth |
| Background jobs | APScheduler | Start-of-day re-plan, reminders |
| Testing | pytest (backend), Vitest (frontend), Playwright (end-to-end) | Your three Phase 0 test days become pytest cases |
| Lint / format | Ruff (Python), oxlint (TS, comes with the Vite template) | Keeps agent-written code consistent |
| Version control / CI | GitHub + GitHub Actions | Run tests on every push |
| Hosting | Vercel (frontend), Render or Railway (backend), Supabase (DB) | Free or cheap tiers, simple deploys |

## Layer details

### Frontend
- **React + TypeScript + Vite.** TypeScript catches the mistakes agents make (wrong field names, missing values) before you run anything.
- **FullCalendar** for daily and weekly views. Dragging a block can call the backend's `move_event`, then re-plan.
- **Chat panel:** a simple React component that streams responses from the backend.
- **Mobile:** make it a PWA (installable web app) first. A native app (React Native / Expo) can wait.

### Backend
Folder layout that keeps the scheduler separate from the web code, so the chatbot and tests can call it directly:
```
backend/
  app/
    api/          FastAPI routes
    models/       SQLAlchemy tables
    schemas/      Pydantic shapes
    scheduler/    capacity, priority, placement, explanations (pure Python, no web code)
    chatbot/      tool definitions, prompt, message handler
    importers/    ics, syllabus/course calendar scanning, Canvas (later)
  tests/
```

### Scheduler
- Pure Python functions: `compute_capacity`, `score_tasks`, `place_blocks`, `explain_block`.
- No database or web code inside, so it's easy to test with your hand-worked days.
- Swap the placement step for OR-Tools later without touching the rest.

### Chatbot and AI features
- **Claude API with tool use.** Each scheduler function (add_task, move_event, set_day_load, what_if, undo…) is defined as a tool; Pydantic models describe the inputs.
- **Model choice:** Claude Sonnet 5.5 for the chatbot (better at multi-step requests), Claude Haiku 4.5 for cheap, simple extraction jobs like hour estimates. Check current pricing before launch.
- **Keep the API key on the backend only**, never in the frontend.
- **Course calendar scanning:** upload goes to Supabase Storage, backend extracts text with pdfplumber (or sends the image/PDF to Claude), Claude returns structured items, user reviews before saving.

### Data
- Tables: users, profiles, fixed_events, tasks, scheduled_blocks, logs, chat_messages, chat_edits.
- Store times in UTC and the user's timezone on their profile.

### Later additions
- **ML (Phase 5):** pandas + scikit-learn, run inside the same backend.
- **Notifications:** web push from the PWA; email via Resend.
- **Canvas import:** Canvas REST API with a personal access token (schools can restrict this).
- **Google Calendar sync:** Google Calendar API with OAuth through Supabase Auth's Google login.

## Accounts to set up on day 1
GitHub, Supabase, Anthropic (API key), Vercel, Render or Railway.

## Rough monthly cost while building
Mostly free tiers. The only real cost is LLM usage, which is small for one user testing; set a spending limit on the Anthropic account.
