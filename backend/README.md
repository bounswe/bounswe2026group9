# Social Event Mapper — Backend

[![Backend CI](https://github.com/bounswe/bounswe2026group9/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/bounswe/bounswe2026group9/actions/workflows/backend-ci.yml)

FastAPI + Supabase backend with JWT authentication, event management, and image upload.

> **Adding tests?** Read [TESTING.md](./TESTING.md) — it lays out the
> four CI lanes (unit / property / snapshot / benchmark) plus the
> shared-Supabase integration + E2E lanes, and tells you exactly which
> one a new test belongs in.

## Setup

### 1. Create env file

```bash
cp .env.example .env
```

Fill in the values:

| Variable | Source |
|----------|--------|
| `SUPABASE_URL` | Supabase Dashboard → Settings → API |
| `SUPABASE_KEY` | Supabase Dashboard → Settings → API → `service_role` key |
| `JWT_SECRET` | `openssl rand -hex 32` |
| `GOOGLE_CLIENT_ID` | Google Cloud Console → Credentials |
| `GOOGLE_CLIENT_SECRET` | Google Cloud Console → Credentials |
| `SMTP_USER` | Gmail address |
| `SMTP_PASSWORD` | Google Account → App Passwords |

### 2. Run with Docker

> **Note:** Supabase tables are already created on the shared account. For fresh setup, run SQL files in order (`001_` through `005_`) in Supabase SQL Editor.

From project root (where `docker-compose.yml` is):

```bash
docker-compose up --build
```

API: `http://localhost:8888`
Swagger docs: `http://localhost:8888/docs`

### 3. Run tests

Three lanes are available; pick one based on what you need.

**Fast unit lane** (no network, sub-second):

```bash
SUPABASE_URL=fake SUPABASE_KEY=fake JWT_SECRET=fake JWT_REFRESH_SECRET=fake \
  python -m pytest tests/test_*_unit.py --no-cov
```

**Hermetic integration lane** (testcontainers — local-only, needs a running Docker daemon, no Supabase secrets):

```bash
PG_CONTAINER=1 \
  JWT_SECRET=hermetic JWT_REFRESH_SECRET=hermetic \
  SUPABASE_URL=http://localhost:0 SUPABASE_KEY=bootstrap-only \
  python -m pytest tests/ -v
```

The conftest spots `PG_CONTAINER=1`, boots a `postgres:16-alpine` +
`postgrest/postgrest:v12.2.0` stack on a shared Docker network,
applies every non-`pg_cron` migration through `tests/db/migrate.py`,
and repoints `app.database._client` at the local stack. Per-test
isolation is `TRUNCATE public.* RESTART IDENTITY CASCADE` instead of
`cleanup_test_users`. **No CI workflow drives this today** — it's
useful for one-off local checks of migrations against a fresh DB.

**Default integration lane** (shared TEST_SUPABASE_*, what default CI gates on):

```bash
docker exec sem-backend python -m pytest tests/ -v
```

### 4. Run static analysis

Type-check (strict mypy, fails only on **new** errors past the baseline):

```bash
mypy app | mypy-baseline filter
```

Security scan:

```bash
bandit -c pyproject.toml -r app/
```

### 5. Run linter

```bash
docker exec sem-backend ruff check .
```

## Deployment Prep

### Production env template

Production deployment should use `backend/.env.production.example` as the base:

```bash
cp backend/.env.production.example backend/.env.production
```

Minimum required production values:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `JWT_SECRET`
- `ENVIRONMENT=production`
- `FRONTEND_URL`
- `BACKEND_URL`
- `CORS_ORIGINS`

When `ENVIRONMENT=production`, refresh cookies are sent with `secure=True`.
Email verification links and Google OAuth completion redirects also rely on `FRONTEND_URL`.

### GitHub Actions deploy secrets

The deploy workflow expects these GitHub repository secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `EC2_HOST`
- `EC2_USERNAME`
- `EC2_SSH_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `JWT_SECRET`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_FROM_NAME`
- `FRONTEND_URL`
- `BACKEND_URL`
- `CORS_ORIGINS`

### Production Docker Compose

Use `docker-compose.prod.yml` on the server:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

The compose file is set up for reverse proxy deployment:

- backend listens on container port `8000`
- frontend listens on container port `3000`
- host binds only `127.0.0.1:8000` and `127.0.0.1:3000`
- nginx serves the frontend from `/` and proxies backend API traffic to the backend container

Set the Docker images with `BACKEND_IMAGE` and `FRONTEND_IMAGE`, for example:

```bash
BACKEND_IMAGE=username/sem:latest FRONTEND_IMAGE=username/sem:frontend-latest docker compose -f docker-compose.prod.yml up -d
```

### EC2 bootstrap

Initial Ubuntu setup script:

```bash
bash deploy/ec2/bootstrap-ubuntu.sh
```

After bootstrap, reconnect via SSH so the `docker` group is active.

### Nginx reverse proxy

For the current root-domain deploy:

- `deploy/nginx/ec2-public-ip.conf` is the HTTP-only bootstrap config
- `deploy/nginx/ec2-https.conf` is the cert-aware HTTPS config used after Let's Encrypt is installed

Typical setup on Ubuntu:

```bash
sudo cp deploy/nginx/ec2-public-ip.conf /etc/nginx/sites-available/sem-backend
sudo ln -s /etc/nginx/sites-available/sem-backend /etc/nginx/sites-enabled/sem-backend
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

Health check after nginx is live:

```bash
curl https://thesocialeventmapper.social/health
```

### Automatic deploy from GitHub Actions

The production workflow is defined in `.github/workflows/deploy.yml`.

Current behavior:

- builds `backend/Dockerfile` and `frontend/Dockerfile`
- pushes `DOCKERHUB_USERNAME/sem:latest` and `DOCKERHUB_USERNAME/sem:frontend-latest`
- uploads `docker-compose.prod.yml`, nginx configs, and generated backend `.env.production` to EC2
- refreshes the live nginx site file with the correct HTTP or HTTPS template
- pulls and restarts both frontend and backend containers on EC2
- verifies backend health plus frontend availability both locally and through the public domain

### HTTPS setup

```bash
sudo certbot --nginx -d thesocialeventmapper.social
```

After HTTPS is enabled, deployment switches to the `deploy/nginx/ec2-https.conf`
template so the live site continues serving TLS traffic while routing `/` to the
frontend container and API paths to the backend container.

## API Endpoints

### Health

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /health | - | System + DB status |

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /auth/register | - | Register with email + password |
| POST | /auth/login | - | Login |
| POST | /auth/refresh | - | Refresh access token (cookie) |
| POST | /auth/logout | - | Logout (revokes refresh token) |
| GET | /auth/me | Bearer | Get current user info |
| GET | /auth/verify-email?token=x | - | Verify email address |
| POST | /auth/resend-verification | Bearer | Resend verification email |
| GET | /auth/google?mode=login | - | Start Google OAuth flow |
| GET | /auth/google/callback | - | Google OAuth callback |

Notes:

- Refresh tokens are opaque random tokens stored in the database, not JWTs.
- Verification emails link to `FRONTEND_URL/verify-email?token=...`; the frontend should call `GET /auth/verify-email`.
- Google OAuth finishes by redirecting the browser to `FRONTEND_URL/auth/callback` after the backend sets the refresh cookie.

### Events

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /events | Bearer | Create event (draft or published) |
| GET | /events/{id} | Optional | Get event detail (full for registered, limited for guest) |
| PUT | /events/{id} | Bearer | Update event (host only) |
| PATCH | /events/{id}/status | Bearer | Change status: draft→published, cancel, end |
| DELETE | /events/{id} | Bearer | Delete event (host only, must be cancelled/ended) |

**Duplicate detection:** creating an event with the same `title`, `start_datetime`, and *primary* location as another event from the same host returns `409 Conflict`. Non-primary stop name collisions are intentionally allowed.

**Lifecycle constraints:** once `start_datetime` is in the past, `time`, `locations`, and `segments` updates are rejected with `400`. Status changes follow `draft → published`, `published/updated → cancelled/ended`. Only `cancelled` or `ended` events can be deleted.

#### Itinerary segments (multi-stop events)

Both `POST /events` and `PUT /events/{id}` accept an optional `segments` array. Each segment ties a single location (referenced by **position** in the request's `locations` array) to a time window with an optional description.

```json
{
  "title": "City photo walk",
  "start_datetime": "2030-06-01T09:00:00+00:00",
  "end_datetime":   "2030-06-01T13:00:00+00:00",
  "category_ids": ["..."],
  "locations": [
    {"name": "Galata Tower", "latitude": 41.025, "longitude": 28.974, "is_primary": true,  "order_index": 0},
    {"name": "Karaköy Pier", "latitude": 41.022, "longitude": 28.978, "is_primary": false, "order_index": 1}
  ],
  "segments": [
    {"location_index": 0, "order_index": 0,
     "start_datetime": "2030-06-01T09:00:00+00:00",
     "end_datetime":   "2030-06-01T10:30:00+00:00",
     "description": "Meet at the tower"},
    {"location_index": 1, "order_index": 1,
     "start_datetime": "2030-06-01T11:00:00+00:00",
     "end_datetime":   "2030-06-01T12:00:00+00:00",
     "description": "Walk to the pier"}
  ]
}
```

Validation (`400` on failure):

- `location_index` must be `0 ≤ i < len(locations)`
- both timestamps must be timezone-aware; `end_datetime > start_datetime`
- each segment must lie within `[event.start_datetime, event.end_datetime]`
- `order_index` values must be contiguous from `0` (no gaps, no duplicates)
- when sorted by `order_index`, segments must not overlap in time (the rule is location-independent)

Update semantics on `PUT`:

- omitting `segments` leaves existing segments untouched
- `segments: []` clears all segments
- providing a non-empty array fully replaces existing segments
- replacing `locations` cascades through `event_segments.location_id`; the API rejects this with `400` unless `segments` is also re-sent (or set to `[]` to opt into clearing)

`location_index` semantics:

- on **create** and on **update with new `locations`**, `location_index` is the position in the request's `locations` array (`location_index = i` ⇔ `locations[i]`).
- on **update that sends `segments` without `locations`**, `location_index` is the position in the locations array returned by the most recent `GET /events/{id}` (the API orders locations by `created_at`, then `order_index`, then `id`).

`GET /events/{id}` includes `segments` ordered by `order_index`, each with the resolved `location_id`.

### Event Images

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /events/{id}/images | Bearer | Upload image (host only, max 10, max 20MB, JPEG/PNG/WebP) |
| DELETE | /events/{id}/images/{image_id} | Bearer | Delete image (host only) |

### Comments

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /events/{id}/comments | Bearer | Post a comment on a published event |
| GET | /events/{id}/comments | - | List comments (paginated, newest first) |
| DELETE | /events/{id}/comments/{comment_id} | Bearer | Delete comment (owner or host) |

### Invites & Access Requests (Private Events)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /events/{id}/invites | Bearer | Host generates invite link |
| GET | /events/{id}/invites | Bearer | Host lists active invites |
| POST | /events/{id}/invites/{token}/accept | Bearer | User accepts invite |
| POST | /events/{id}/access-requests | Bearer | User requests access to private event; host is notified |
| GET | /events/{id}/access-requests | Bearer | Host lists pending requests |
| PATCH | /events/{id}/access-requests/{request_id} | Bearer | Host approves or rejects request |

### Notifications

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /notifications | Bearer | List user's notifications (paginated, newest first) |
| PATCH | /notifications/{id}/read | Bearer | Mark single notification as read |
| PATCH | /notifications/read-all | Bearer | Mark all notifications as read |

**Query parameters** for `GET /notifications`: `page` (default 1), `page_size` (default 20, max 100).

**Automatic emission:** Notifications are created automatically when:
- An event is updated → `event_updated` sent to going attendees + bookmarkers
- An event is cancelled → `event_cancelled` sent to going attendees + bookmarkers
- An event is deleted → `event_deleted` sent to going attendees + bookmarkers (emitted *before* the row is removed; the notification's `event_id` is `NULL` after delete because the FK is `ON DELETE SET NULL`)
- A user requests access to a private event → `access_request` sent to the host
- A host approves an access request → `access_approved` sent to the requester
- A host rejects an access request → `access_rejected` sent to the requester
- The host is excluded from receiving their own action notifications

### Categories

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /categories | - | List predefined + approved categories (optional ?search=) |
| POST | /categories | Bearer | Create custom category (pending approval) |

### Bookmarks

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /events/{id}/bookmark | Bearer | Bookmark an event |
| DELETE | /events/{id}/bookmark | Bearer | Remove bookmark |

### Attendances

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /events/{id}/attendance | Bearer | Set attendance status (going/interested) |
| DELETE | /events/{id}/attendance | Bearer | Remove attendance |

### Users, Profiles & Ratings

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /users/me/bookmarks | Bearer | List current user's bookmarks |
| PUT | /users/me | Bearer | Update current user's profile |
| GET | /users/{id}/profile | Optional | Get host profile details (avg rating + count summary) |
| POST | /users/{id}/ratings | Bearer | Rate a host (1–5 stars + optional text review) — returns 201 |
| GET | /users/{id}/reviews | - | Paginated reviews for a host, newest-first |

**Rating eligibility:** the rater must have attended at least one *ended* event hosted by the target user. Self-rating is rejected with 400. Repeated POSTs from the same rater overwrite the previous score and review text (upsert).

**Optional review text:** `POST /users/{id}/ratings` accepts an optional `review_text` field (max 1000 characters). Whitespace-only values are normalised to `null` server-side. The same payload shape is used for new ratings and for editing an existing one.

```jsonc
// POST /users/{host_id}/ratings — minimal (back-compat with star-only clients)
{ "score": 4.5 }

// POST /users/{host_id}/ratings — with review text
{ "score": 4.5, "review_text": "Walk was excellent — leader was clear and friendly." }
```

**Reviews list:** `GET /users/{id}/reviews?page=1&page_size=20` returns reviews ordered by `created_at DESC, id DESC`. Star-only ratings are included with `review_text: null` so the list mirrors the aggregate rating count on the profile. Unknown host → 404 (mirrors `GET /users/{id}/profile`); existing host with no ratings → 200 with empty `items`.

```json
{
  "items": [
    {
      "id": "…",
      "rater_id": "…",
      "rater_username": "alice",
      "score": 5.0,
      "review_text": "Walk was excellent",
      "created_at": "2030-06-01T13:30:00+00:00"
    },
    {
      "id": "…",
      "rater_id": "…",
      "rater_username": "bob",
      "score": 4.0,
      "review_text": null,
      "created_at": "2030-06-01T12:00:00+00:00"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, router registration
│   ├── config.py             # Environment variables
│   ├── database.py           # Supabase client
│   ├── middleware/
│   │   └── auth.py           # JWT auth dependencies
│   ├── models/
│   │   ├── user.py           # Auth Pydantic schemas
│   │   ├── event.py          # Event/Category/Image Pydantic schemas
│   │   ├── comment.py        # Comment Pydantic schemas
│   │   ├── invite.py         # Invite/Access request Pydantic schemas
│   │   └── notification.py   # Notification Pydantic schemas
│   ├── routers/
│   │   ├── auth.py           # Auth endpoints
│   │   ├── events.py         # Event + Image endpoints
│   │   ├── categories.py     # Category endpoints
│   │   ├── comments.py       # Comment endpoints
│   │   ├── invites.py        # Invite + Access request endpoints
│   │   ├── notifications.py  # Notification endpoints
│   │   ├── bookmarks.py      # Bookmark endpoints
│   │   ├── attendances.py    # Attendance endpoints
│   │   └── users.py          # User, profile, rating endpoints
│   ├── services/
│   │   ├── auth.py           # JWT, password hashing
│   │   ├── email.py          # SMTP email sending
│   │   ├── oauth.py          # Google OAuth
│   │   ├── event.py          # Event business logic
│   │   ├── image.py          # Image upload/resize/delete
│   │   ├── category.py       # Category business logic
│   │   ├── comment.py        # Comment business logic
│   │   ├── invite.py         # Invite/Access request business logic
│   │   └── notification_emitter.py  # Auto-emit notifications on event changes
│   └── repositories/
│       ├── event.py          # Event DB operations
│       ├── user.py           # User DB operations
│       ├── image.py          # Image DB + storage operations
│       ├── category.py       # Category DB operations
│       ├── comment.py        # Comment DB operations
│       ├── invite.py         # Invite/Access request DB operations
│       └── notification.py   # Notification DB operations
├── tests/
│   ├── conftest.py           # Fixtures, cleanup, mocks
│   ├── test_auth.py          # Auth unit tests (29)
│   ├── test_auth_integration.py  # Auth integration tests (8)
│   ├── test_events.py        # Event CRUD tests (44)
│   ├── test_categories.py    # Category tests (9)
│   ├── test_images.py        # Image upload/delete tests (10)
│   ├── test_comments.py      # Comment tests (20)
│   ├── test_invites.py       # Invite/Access request tests (28)
│   ├── test_notifications.py # Notification tests (12)
│   ├── test_notification_emitter.py  # Notification emission tests
│   ├── test_segments_unit.py # Itinerary-segment + duplicate-detection unit tests
│   ├── test_reviews_unit.py  # Review/rating-text unit tests (issue #235)
│   ├── test_users.py         # User/profile/rating integration tests
│   └── test_health.py        # Health check test (1)
├── sql/                                # Apply manually in Supabase SQL Editor (no runner)
│   ├── 001_create_tables.sql           # Auth tables
│   ├── 002_create_core_tables.sql      # Core data model tables
│   ├── 003_pg_cron_auto_end.sql        # Auto-end expired events
│   ├── 004_revoke_public_access.sql    # Tighten RLS / public role
│   ├── 005_create_invite_tables.sql    # Invite + access-request tables
│   ├── 006_reconcile_invite_schema.sql # Reconcile invite schema + add notification types
│   ├── 007_add_phone_visibility.sql    # Phone visibility column on profiles
│   ├── 008_token_cleanup_cron.sql      # pg_cron job for refresh/verification token cleanup
│   ├── 009_atomic_event_rpc.sql        # create_event_atomic RPC (superseded by 013)
│   ├── 010_atomic_event_update_rpc.sql # update_event_atomic RPC (superseded by 013)
│   ├── 011_add_comment_parent_id.sql   # Threaded comments
│   ├── 012_create_event_segments.sql   # Itinerary segments table
│   ├── 013_atomic_event_rpc_segments.sql  # Replaces 009/010 with p_segments support
│   └── 014_add_rating_review_text.sql  # Optional free-text review on ratings (issue #235)
├── requirements.txt
├── pyproject.toml            # Ruff + pytest config
├── Dockerfile
└── .env.example
```

## Tech Stack

- **FastAPI** — Web framework
- **Supabase** — PostgreSQL database + object storage
- **bcrypt** — Password hashing
- **python-jose** — JWT tokens
- **Pillow** — Image processing (resize)
- **Docker** — Containerization
- **ruff** — Linter
- **pytest** — Testing
