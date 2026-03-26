# Social Event Mapper — Backend

FastAPI + Supabase backend with JWT authentication, event management, and image upload.

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
| `JWT_REFRESH_SECRET` | `openssl rand -hex 32` |
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

```bash
docker exec sem-backend python -m pytest tests/ -v
```

### 4. Run linter

```bash
docker exec sem-backend ruff check .
```

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

### Events

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /events | Bearer | Create event (draft or published) |
| GET | /events/{id} | Optional | Get event detail (full for registered, limited for guest) |
| PUT | /events/{id} | Bearer | Update event (host only) |
| PATCH | /events/{id}/status | Bearer | Change status: draft→published, cancel, end |
| DELETE | /events/{id} | Bearer | Delete event (host only, must be cancelled/ended) |

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
| POST | /events/{id}/access-requests | Bearer | User requests access to private event |
| GET | /events/{id}/access-requests | Bearer | Host lists pending requests |
| PATCH | /events/{id}/access-requests/{request_id} | Bearer | Host approves or denies request |

### Notifications

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /notifications | Bearer | List user's notifications (paginated, newest first) |
| PATCH | /notifications/{id}/read | Bearer | Mark single notification as read |
| PATCH | /notifications/read-all | Bearer | Mark all notifications as read |

**Query parameters** for `GET /notifications`: `page` (default 1), `page_size` (default 20, max 100).

**Automatic emission:** Notifications are created automatically when:
- An event is updated → `event_updated` sent to all going/interested/bookmarked users
- An event is cancelled → `event_cancelled` sent to all going/interested/bookmarked users
- The host is excluded from receiving their own notifications

### Categories

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /categories | - | List predefined + approved categories (optional ?search=) |
| POST | /categories | Bearer | Create custom category (pending approval) |

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
│   │   └── notifications.py  # Notification endpoints
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
│   ├── test_invites.py       # Invite/Access request tests (27)
│   ├── test_notifications.py # Notification tests (12)
│   ├── test_notification_emitter.py  # Notification emission tests (10)
│   └── test_health.py        # Health check test (1)
├── sql/
│   ├── 001_create_tables.sql         # Auth tables
│   ├── 002_create_core_tables.sql    # Core data model tables
│   ├── 003_pg_cron_auto_end.sql      # Auto-end expired events
│   └── 005_create_invite_tables.sql  # Invite/Access tables
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
