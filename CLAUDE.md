# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Social Event Mapper — a map-based event discovery platform (CMPE354 course project). Monorepo with three independent services sharing a Supabase PostgreSQL database.

## Build & Run Commands

### Backend (FastAPI + Supabase)

```bash
# Start (from repo root)
docker-compose up --build              # API at http://localhost:8888, Swagger at /docs

# Tests (against live Supabase — requires .env with valid credentials)
docker exec sem-backend python -m pytest tests/ -v
docker exec sem-backend python -m pytest tests/test_events.py -v          # single file
docker exec sem-backend python -m pytest tests/test_events.py::test_name -v  # single test

# Lint
docker exec sem-backend ruff check .
docker exec sem-backend ruff check . --fix
```

### Frontend (Next.js 16 + React 19)

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
npm run check        # lint + typecheck + format check + test (run before PRs)
npm run test:run     # vitest single run
```

### Mobile (Android / Kotlin Compose)

```bash
cd mobile
./gradlew build
./gradlew installDebug
./gradlew test
```

## Architecture

### Backend layering (`backend/app/`)

Strict three-layer separation — routers never touch the database directly:

```
routers/   →  services/   →  repositories/
(HTTP I/O)    (business     (Supabase queries,
               logic,        single-table ops)
               validation)
```

- **9 routers**: auth, events, categories, comments, invites, notifications, bookmarks, attendances, users
- **Middleware**: `middleware/auth.py` provides `get_current_user` (JWT dependency) and `require_role(*roles)` factory
- **Models**: Pydantic request/response schemas in `models/` — not ORM models
- **Database**: Supabase client singleton in `database.py`; no ORM, queries use `supabase-py` query builder. Multi-step writes that must be atomic (event create/update, including itinerary segments) go through the Postgres RPC functions in `sql/013_atomic_event_rpc_segments.sql` (which supersedes `009`/`010`) rather than chained query-builder calls
- **Migrations**: Hand-written SQL in `backend/sql/` (001–013), applied manually via Supabase SQL editor — there is no migration runner, so when adding SQL also coordinate applying it to the live Supabase project. RPC-replacing migrations (e.g. 013 over 009/010) must be applied before deploying the matching backend code, or every event create breaks

### Frontend (`frontend/src/`)

Next.js App Router. Auth state via React context (`providers/auth-provider.tsx`). Centralized API client in `lib/api.ts` with automatic 401 → refresh token retry — always go through it rather than calling `fetch` directly so refresh-on-401 stays consistent. Event-specific helpers live in `lib/events-api.ts`. Path alias: `@/*` → `./src/*`. `npm run check` is the aggregate gate (format + lint + typecheck + tests); CI runs the same parts individually.

### Mobile (`mobile/`)

Jetpack Compose + Retrofit. Session tokens stored in DataStore (`data/local/SessionManager.kt`). API interface in `data/remote/ApiService.kt`.

## Testing

Backend tests hit a **real Supabase instance** (no local DB mock). Each test run generates unique identities via `tests_support.py::build_test_identity()` using the `TEST_RUN_ID` env var to avoid collisions across parallel CI shards — set it to anything unique when running tests outside Docker. `conftest.py` sets `TESTING=1` before app import, which disables the SlowAPI per-endpoint rate limiter and patches out real email sending while still capturing raw verification tokens for assertions. Cleanup runs automatically after each test via the `cleanup_test_users` autouse fixture.

CI shards integration tests into 5 groups: auth-core, events, discovery, comments-invites, media-notifications (see `.github/workflows/backend-ci.yml`). Unit tests (`test_*_unit.py`) run first as a fast gate; only those should be added when a feature can be tested without DB round-trips.

## Deployment

Push to `main` triggers `.github/workflows/deploy.yml` for backend and frontend: build Docker images → push to Docker Hub → SSH deploy to EC2 using `docker-compose.prod.yml`. Nginx (configs in `deploy/nginx/`) reverse-proxies port 80 → backend `127.0.0.1:8000`. Health check at `GET /health` (verifies Supabase reachability). Live URL: https://thesocialeventmapper.social. Android APK builds on every push to `main` via `.github/workflows/android-build.yml` and is attached to GitHub releases when one is created.

## Key Conventions

- **Ruff config**: `pyproject.toml` — line length 120, Python 3.12 target, `B008` ignored (FastAPI `Depends` pattern)
- **Event lifecycle states**: draft → published → updated → cancelled / ended
- **Private events**: visible in discovery with limited preview; full details only via access grant (invite link or approved request)
- **Rate limiting (two layers)**: (1) SlowAPI per-endpoint IP-based limits via the shared `limiter` in `app/rate_limit.py` (skipped when `TESTING=1`); (2) DB-driven event-creation quota in the `rate_limit_config` table (single row) — max events per user per time window
- **Notifications**: emitted by `services/notification_emitter.py` to going attendees + bookmarkers on event changes. Types: `event_updated`, `event_cancelled`, `event_deleted` (emitted *before* the row is removed; `notifications.event_id` is `ON DELETE SET NULL`), `access_request`, `access_approved`, `access_rejected`. Host is excluded from their own action notifications
- **Itinerary segments**: events can carry an optional `segments[]` payload tying each step to a location (by index into `locations[]`) and a time window. Validation lives in `services/event.py::validate_segments`. Replacing `locations` cascades through `event_segments` — the API rejects this unless `segments` is also re-sent (or set to `[]` to clear). Time/location/segment changes are all blocked once `start_datetime` is in the past (FRS-2)
- **Duplicate event detection**: `title + start_datetime + primary location` per host triggers `409`. Non-primary stop name collisions are intentionally allowed
- **Image uploads**: Supabase Storage, max 10 per event, 20MB each, auto-resized to 2048px
