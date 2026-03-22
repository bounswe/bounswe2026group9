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

> **Note:** Supabase tables are already created on the shared account. For fresh setup, run `sql/001_create_tables.sql` and `sql/002_create_core_tables.sql` in Supabase SQL Editor.

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
│   │   └── event.py          # Event/Category/Image Pydantic schemas
│   ├── routers/
│   │   ├── auth.py           # Auth endpoints
│   │   ├── events.py         # Event + Image endpoints
│   │   └── categories.py     # Category endpoints
│   ├── services/
│   │   ├── auth.py           # JWT, password hashing
│   │   ├── email.py          # SMTP email sending
│   │   ├── oauth.py          # Google OAuth
│   │   ├── event.py          # Event business logic
│   │   ├── image.py          # Image upload/resize/delete
│   │   └── category.py       # Category business logic
│   └── repositories/
│       ├── event.py          # Event DB operations
│       ├── user.py           # User DB operations
│       ├── image.py          # Image DB + storage operations
│       └── category.py       # Category DB operations
├── tests/
│   ├── conftest.py           # Fixtures, cleanup, mocks
│   ├── test_auth.py          # Auth unit tests (29)
│   ├── test_auth_integration.py  # Auth integration tests (8)
│   ├── test_events.py        # Event CRUD tests (44)
│   ├── test_categories.py    # Category tests (9)
│   ├── test_images.py        # Image upload/delete tests (10)
│   └── test_health.py        # Health check test (1)
├── sql/
│   ├── 001_create_tables.sql         # Auth tables
│   ├── 002_create_core_tables.sql    # Core data model tables
│   └── 003_pg_cron_auto_end.sql      # Auto-end expired events
├── postman/
│   └── SEM_Auth.postman_collection.json
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
