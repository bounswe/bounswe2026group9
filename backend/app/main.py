import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app import logging_config
from app.config import settings
from app.rate_limit import limiter

# Install the JSON formatter as soon as the app module loads so any
# import-time logging (FastAPI, uvicorn) already routes through it.
# Routers are imported _after_ this so their module-level
# ``logging.getLogger(...)`` calls inherit the configured root.
logging_config.configure()
_logger = logging.getLogger("app.main")

from app.routers import (  # noqa: E402 — must follow logging_config.configure()
    attendances,
    auth,
    bookmarks,
    categories,
    comments,
    events,
    invites,
    notifications,
    users,
)
from app.routers.attendances import _qr_router  # noqa: E402

API_DESCRIPTION = """
Backend API for **Social Event Mapper** — a platform for discovering, hosting,
and attending social events.

The API follows the **OpenAPI 3.1** specification (FastAPI ≥ 0.100 emits
`openapi: 3.1.0` by default). Both the web and mobile clients are generated
or hand-written against this contract, so the schema is the source of truth.

## Authentication

Most endpoints require a short-lived **bearer access token** in the
`Authorization` header:

```
Authorization: Bearer <access_token>
```

Access tokens are obtained from `POST /auth/register`, `POST /auth/login`,
`POST /auth/refresh`, or the Google OAuth flow under `/auth/google`. They are
rotated using a long-lived refresh token, which the server stores in a
`HttpOnly` cookie (`sem_refresh_token`) — clients should not read or store
that cookie themselves.

A small number of read-only endpoints (event discovery and event detail)
accept an *optional* bearer token: anonymous callers get a public view,
authenticated callers may get an enriched view (e.g. private events they are
invited to).

## Conventions

* **Error envelope** — every non-2xx response returns
  `{ "detail": "<message>" }`. Validation failures (HTTP 422) return
  `{ "detail": [ { "loc": [...], "msg": "...", "type": "..." } ] }` per
  Pydantic's standard format.
* **Pagination** — list endpoints accept `page` (≥ 1, default 1) and
  `page_size` (1–100, default 20). Responses include `total` and the page
  metadata.
* **Identifiers** — all resource IDs are UUIDs.
* **Timestamps** — ISO 8601 in UTC.
* **Rate limiting** — auth endpoints are throttled per IP; exceeding the
  limit returns HTTP 429 with a `Retry-After` header.
"""

TAGS_METADATA = [
    {
        "name": "auth",
        "description": (
            "Registration, login, token refresh/rotation, logout, email "
            "verification, and Google OAuth. Sets the `sem_refresh_token` "
            "HttpOnly cookie; access tokens are returned in the response body."
        ),
    },
    {
        "name": "events",
        "description": (
            "Event lifecycle: discovery (search/filter/sort), detail view, "
            "create / update / status change / delete, and event images. "
            "Discovery accepts an optional bearer token for visibility-aware "
            "results."
        ),
    },
    {
        "name": "categories",
        "description": (
            "Predefined and user-suggested categories used to tag events. "
            "Custom categories require admin approval before they appear in "
            "discovery filters."
        ),
    },
    {
        "name": "comments",
        "description": "Threaded comments on a specific event.",
    },
    {
        "name": "invites",
        "description": (
            "Private-event invitations and access requests — host issues "
            "invites or approves/denies guest access requests."
        ),
    },
    {
        "name": "notifications",
        "description": (
            "Per-user notification feed: list, unread count, mark single / "
            "all as read."
        ),
    },
    {
        "name": "bookmarks",
        "description": "Save / unsave an event for the authenticated user.",
    },
    {
        "name": "attendances",
        "description": (
            "Per-user attendance status on an event "
            "(`going` / `interested` / `not_going`)."
        ),
    },
    {
        "name": "users",
        "description": (
            "Profile read/update, host ratings & reviews, and the "
            "authenticated user's bookmarks list."
        ),
    },
]


app = FastAPI(
    title="Social Event Mapper API",
    version="0.1.0",
    summary="OpenAPI 3.1 contract for the Social Event Mapper backend.",
    description=API_DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    contact={
        "name": "bounswe2026group9",
        "url": "https://github.com/bounswe/bounswe2026group9",
    },
    license_info={
        "name": "MIT",
        "url": "https://github.com/bounswe/bounswe2026group9/blob/main/LICENSE",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# --- Per-endpoint rate limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# --- Structured 5xx logging (NFR-07) ---
# Catch-all handler so any uncaught exception in a router/service ends up
# as a single JSON log line with the request's method/path and the
# exception class. The 500 response shape stays identical to FastAPI's
# default — clients see no behavioural change, only the operator does.
@app.exception_handler(Exception)
async def _log_unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    _logger.error(
        "unhandled_exception",
        extra={
            "action": "http.unhandled_exception",
            "request_method": request.method,
            "request_path": request.url.path,
        },
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


app.include_router(auth.router)
app.include_router(events.router)
app.include_router(categories.router)
app.include_router(comments.router)
app.include_router(invites.router)
app.include_router(notifications.router)
app.include_router(bookmarks.router)
app.include_router(attendances.router)
app.include_router(_qr_router)
app.include_router(users.router)


@app.get(
    "/health",
    tags=["meta"],
    summary="Liveness & DB connectivity probe",
    description=(
        "Used by the container platform's health check. Returns `status=ok` "
        "and a `database` field of `connected` or `error`."
    ),
)
def health_check():
    from app.database import get_supabase
    try:
        db = get_supabase()
        db.table("users").select("id").limit(1).execute()
        db_status = "connected"
    except Exception:
        db_status = "error"
    return {"status": "ok", "database": db_status}
