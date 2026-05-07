"""Top-level pytest fixtures.

Two modes, selected by the ``PG_CONTAINER`` env var:

- ``PG_CONTAINER`` unset / != "1" — *legacy lane*. Tests talk to a
  shared remote Supabase project. ``cleanup_test_users`` runs after
  every test to limit cross-test pollution. This is the lane the
  default Backend CI workflow exercises today.
- ``PG_CONTAINER=1`` — *hermetic lane*. A session-scoped Postgres +
  PostgREST stack boots via testcontainers; ``app.database._client``
  is repointed at the local stack, and per-test isolation switches
  to ``TRUNCATE public.*`` so each test starts on a clean schema. The
  ``backend-ci-hermetic.yml`` workflow runs CI in this mode.

Switching modes requires no test-side changes — every existing
fixture (``client``, ``db``, ``registered_user``) keeps the same
contract. The only thing that varies is which database the fixtures
end up pointing at and how isolation is enforced.
"""
import os
from collections.abc import Iterator
from unittest.mock import patch

os.environ["TESTING"] = "1"  # Disable rate limiting during tests

import pytest
from fastapi.testclient import TestClient

# `app.*` import lazily so the hermetic-lane bootstrap below has a
# chance to override settings before the database singleton is built.
from app.database import get_supabase
from app.main import app
from app.services.email import store_verification_token as _real_store_verification_token
from tests_support import build_test_identity, cleanup_email_pattern

# Global dict to capture raw verification tokens before they are hashed.
# Key: user_id, Value: raw token string.
_captured_verification_tokens: dict[str, str] = {}


def _capturing_store_verification_token(user_id: str, token: str) -> None:
    """Wrapper that captures the raw token, then delegates to the real function."""
    _captured_verification_tokens[user_id] = token
    _real_store_verification_token(user_id, token)


def _hermetic_lane_active() -> bool:
    return os.getenv("PG_CONTAINER") == "1"


# ---------------------------------------------------------------------------
# Hermetic-lane bootstrap (session scoped, autouse, opt-in via PG_CONTAINER=1)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _hermetic_stack_session() -> Iterator[None]:
    """Boot Postgres + PostgREST and repoint the supabase singleton at it.

    Runs once per session. Skips silently when the hermetic lane is not
    requested so the legacy lane is unchanged. Also short-circuits if
    Docker isn't reachable — falls back to whatever ``SUPABASE_URL``
    points at, which mirrors today's behaviour.
    """
    if not _hermetic_lane_active():
        yield
        return

    try:
        import docker

        docker.from_env().ping()
    except Exception:  # pragma: no cover
        pytest.skip("PG_CONTAINER=1 set but docker daemon unreachable")

    from supabase import create_client

    from app import database
    from app.config import settings
    from tests.db.migrate import apply_migrations
    from tests.db.postgrest import boot_supabase_stack

    # Start PostgREST only after migrations land. Relying on NOTIFY-based
    # schema reload makes the first E2E request race the cache refresh in CI.
    endpoints, containers, network = boot_supabase_stack(
        migrate_before_postgrest=apply_migrations,
    )

    # Patch settings + the lazy singleton so every code path that reads
    # them ends up at the local stack.
    settings.SUPABASE_URL = endpoints.base_url
    settings.SUPABASE_KEY = endpoints.service_role_key
    database._client = create_client(endpoints.base_url, endpoints.service_role_key)

    try:
        # Stash the DSN so per-test isolation can TRUNCATE through psycopg
        # without re-reading env vars in the inner fixture.
        os.environ["_HERMETIC_DB_DSN"] = endpoints.db_dsn
        yield
    finally:
        os.environ.pop("_HERMETIC_DB_DSN", None)
        for c in reversed(containers):
            try:
                c.stop()
            except Exception:  # pragma: no cover
                pass
        try:
            network.remove()
        except Exception:  # pragma: no cover
            pass


# ---------------------------------------------------------------------------
# Shared fixtures (legacy + hermetic)
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture(scope="session")
def db():
    """Supabase client for direct DB operations in tests."""
    return get_supabase()


@pytest.fixture()
def test_user_data():
    """Generate unique user data for each test."""
    username, email = build_test_identity("testuser")
    return {
        "username": username,
        "email": email,
        "password": "testpass123",
        "date_of_birth": "2000-01-15",
    }


@pytest.fixture()
def registered_user(client, test_user_data):
    """Register a user and return user data + access token."""
    response = client.post("/auth/register", json=test_user_data)
    data = response.json()
    return {
        "user": data["user"],
        "access_token": data["access_token"],
        "password": test_user_data["password"],
        "email": test_user_data["email"],
    }


@pytest.fixture(autouse=True, scope="session")
def disable_email_sending():
    """Prevent real emails and capture raw verification tokens before hashing."""
    with (
        patch("app.routers.auth.send_verification_email", return_value=False),
        patch("app.routers.auth.store_verification_token", side_effect=_capturing_store_verification_token),
    ):
        yield


@pytest.fixture()
def captured_verification_tokens():
    """Access raw (pre-hash) verification tokens captured during this test."""
    return _captured_verification_tokens


# ---------------------------------------------------------------------------
# Per-test isolation (legacy: cleanup_test_users; hermetic: TRUNCATE)
# ---------------------------------------------------------------------------


def _truncate_public_tables(dsn: str) -> None:
    import psycopg

    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename <> '_test_migrations'
                """
            )
            tables = [row[0] for row in cur.fetchall()]
            if tables:
                joined = ", ".join(f'public."{t}"' for t in tables)
                cur.execute(f"TRUNCATE {joined} RESTART IDENTITY CASCADE")
        conn.commit()


@pytest.fixture(autouse=True)
def cleanup_test_users(db):
    """Per-test cleanup.

    Hermetic lane: TRUNCATE every public table (except the migration
    ledger) so each test starts on an empty schema. PostgREST opens
    its own DB connections, so a per-test BEGIN/ROLLBACK in this
    process can't isolate writes that go through REST.

    Legacy lane: drop user rows whose email matches the run's
    ``cleanup_email_pattern`` so cross-test pollution stays bounded
    on the shared Supabase project.
    """
    yield
    if _hermetic_lane_active():
        dsn = os.environ.get("_HERMETIC_DB_DSN")
        if dsn:
            _truncate_public_tables(dsn)
        return

    db.table("users").delete().like("email", cleanup_email_pattern()).execute()
