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
- host binds only `127.0.0.1:8000`
- nginx should proxy public traffic to that local port

Set the Docker image with `BACKEND_IMAGE`, for example:

```bash
BACKEND_IMAGE=username/sem:latest docker compose -f docker-compose.prod.yml up -d
```

### EC2 bootstrap

Initial Ubuntu setup script:

```bash
bash deploy/ec2/bootstrap-ubuntu.sh
```

After bootstrap, reconnect via SSH so the `docker` group is active.

### Nginx reverse proxy

For the current IP-based deploy, use `deploy/nginx/ec2-public-ip.conf`.

A starter nginx site config is available at `deploy/nginx/api.example.com.conf`.

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
curl http://13.49.23.178/health
```

### Automatic deploy from GitHub Actions

The production workflow is defined in `.github/workflows/deploy.yml`.

Current behavior:

- builds `backend/Dockerfile`
- pushes `DOCKERHUB_USERNAME/sem:latest`
- uploads `docker-compose.prod.yml`, nginx config, and generated `.env.production` to EC2
- reloads nginx
- pulls and restarts the backend container on EC2
- verifies both local container health and public `http://EC2_HOST/health`

### HTTPS later

After a domain is attached, switch nginx to `deploy/nginx/api.example.com.conf` and enable certbot:

```bash
sudo certbot --nginx -d api.example.com
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
│   ├── test_invites.py       # Invite/Access request tests (28)
│   ├── test_notifications.py # Notification tests (12)
│   ├── test_notification_emitter.py  # Notification emission tests (11)
│   └── test_health.py        # Health check test (1)
├── sql/
│   ├── 001_create_tables.sql         # Auth tables
│   ├── 002_create_core_tables.sql    # Core data model tables
│   ├── 003_pg_cron_auto_end.sql      # Auto-end expired events
│   ├── 005_create_invite_tables.sql  # Invite/Access tables
│   └── 006_reconcile_invite_schema.sql  # Manual Supabase reconcile script
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
