# ICanRun Triathlon App — Agent Memory

## Project Status
- Scaffolding: COMPLETE
- Auth system: COMPLETE
- Workout CRUD (backend + frontend): COMPLETE
- Competition CRUD (backend + frontend): COMPLETE
- Plan service (Friel): COMPLETE
- Analytics service: COMPLETE
- Admin router + frontend page: COMPLETE
- Subscriptions router: COMPLETE
- Frontend calendar/dashboard: COMPLETE
- Frontend results/analytics page: COMPLETE
- Frontend settings page: COMPLETE
- Frontend admin page: COMPLETE
- Frontend login/register pages: COMPLETE
- Landing page: COMPLETE
- Backend tests: 129 passing (auth, workouts, competitions, plans, analytics, admin, subscriptions)

## Key Architectural Decisions

### Database
- SQLite + aiosqlite (not PostgreSQL) — simplicity for MVP
- `create_tables()` called on startup (idempotent); Alembic configured but no migration files yet

### Backend Structure
- `app/api/v1/routers/` — FastAPI routers (NOT `app/routers/`)
- `app/api/v1/router.py` — aggregates all routers
- `app/services/` — business logic layer
- `app/repositories/` — data access layer (BaseRepository generic)

### Auth System
- In-memory refresh token blacklist in `auth_service.py` (_blacklisted_jtis dict)
- Both access and refresh tokens have `jti` (UUID) — required for test uniqueness
- New users get 30-day Trial subscription on registration
- `pytest.ini` in backend/ with `asyncio_mode = auto`

### User Model Extensions
- Added `birth_year`, `gender`, `weight_kg`, `height_cm` to User model (all nullable)
- GenderType = Literal["male", "female", "other"]

### Admin Seeding
- Default admin seeded in `app/main.py` `seed_admin()` via lifespan event
- Email: abramov.yu.v@gmail.com | Role: ADMIN | Subscription: PRO (no expiry)

### Frontend Structure
- Next.js 14 App Router: route groups `(auth)`, `(app)`, root `page.tsx` = landing
- Auth guard in `(app)/layout.tsx` — redirects to /login if not authenticated
- State: Zustand (`authStore`, `calendarStore`) + React Query for server data
- Tokens in localStorage: `icanrun_access_token`, `icanrun_refresh_token`

### Pydantic v2 Field Shadowing Bug (CRITICAL)
- `date: Optional[date] = None` in a Pydantic model SHADOWS the imported `date` type
- Causes `none_required` validation errors — field only accepts None, nothing else
- Fix: always use `import datetime as dt` and reference types as `dt.date`, `dt.datetime`
- Already fixed in: `app/schemas/workout.py`, `app/schemas/competition.py`

### SQLite Nullable Unique Constraint
- `unique=True` on nullable SQLAlchemy columns causes issues — multiple NULLs break constraint
- `garmin_activity_id`: removed `unique=True`, kept `index=True` — app-layer deduplication

### Admin Settings
- Settings stored on pydantic-settings `Settings` object at runtime (in-memory, not in DB)
- Changes survive request but NOT server restarts — MVP limitation
- `pydantic_settings` v2 Settings objects ARE mutable at runtime
- `google_client_secret` is never returned to clients (returns empty string)

### Client Components
- `"use client"` components must NOT export `metadata` or use server-only Next.js APIs
- Unused imports like `import type { Metadata } from "next"` should be removed from client pages

## Key Files
- Backend entry: `backend/app/main.py`
- Plan service: `backend/app/services/plan_service.py` (Joe Friel methodology)
- Analytics service: `backend/app/services/analytics_service.py`
- Admin router: `backend/app/api/v1/routers/admin.py`
- Subscriptions router: `backend/app/api/v1/routers/subscriptions.py`
- Frontend API client: `frontend/src/lib/api.ts`
- Types: `frontend/src/types/index.ts`
- Calendar: `frontend/src/components/calendar/MonthCalendar.tsx`
- Competition badge: `frontend/src/components/calendar/CompetitionBadge.tsx`

## Patterns Established
- Error responses: `{"detail": "message"}` with optional `X-Error-Code` header
- All API under `/api/v1/`
- SportType colors: running=red, swimming=blue, cycling=amber, strength=violet, triathlon=emerald
- UI language: Russian (labels, weekday names, month names)
- Weekdays: 0=Monday convention (differs from JS Date where 0=Sunday)
- Test fixtures: `regular_user` (trial), `admin_user` (pro), `get_auth_headers()` helper

## What Still Needs Work
- Garmin integration: service stubbed, router not implemented
- YooKassa payments: router does not exist; frontend has placeholder `alert()`
- Admin settings persistence: changes lost on server restart (in-memory only for MVP)
- Alembic migration history: tables via `create_tables()` only; no versioned migrations yet

## Dependencies (key versions)
- FastAPI 0.115.6, SQLAlchemy 2.0.36, Pydantic 2.10.4
- Next.js 14.2.18, React Query 5.x, Zustand 5.x, dnd-kit 6.x, Recharts 2.x
