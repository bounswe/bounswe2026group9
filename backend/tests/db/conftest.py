"""Shared fixtures for the hermetic-database test lane.

These fixtures live in ``tests/db/`` so the existing legacy integration
suite (which still talks to a remote Supabase) is unaffected. The
session-scoped ``pg_container`` boots ``postgres:16-alpine``, runs
every non-cron migration through ``apply_migrations``, and yields the
DSN. The session-scoped ``supabase_stack`` adds a PostgREST sidecar so
``supabase-py`` can talk to the hermetic stack via REST.

``apply_migrations`` is idempotent, so the second time the conftest
loads in the same session the container start dominates and the SQL
replay is a fast no-op.
"""
from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from tests.db.migrate import apply_migrations
from tests.db.postgrest import StackEndpoints, boot_supabase_stack

# Marker so the rest of the test tree can opt in/out without dragging
# Docker into every CI shard. CI sets ``PG_CONTAINER=1`` only on the
# lane that owns the hermetic suite.
PG_CONTAINER_FLAG = "PG_CONTAINER"


def _testcontainers_available() -> bool:
    try:
        import docker  # noqa: F401
        from testcontainers.postgres import PostgresContainer  # noqa: F401
    except Exception:  # pragma: no cover
        return False
    return True


def _docker_daemon_reachable() -> bool:
    try:
        import docker

        docker.from_env().ping()
    except Exception:  # pragma: no cover
        return False
    return True


def _skip_unless_docker() -> None:
    if not _testcontainers_available():
        pytest.skip("testcontainers + docker SDK required")
    if os.getenv(PG_CONTAINER_FLAG) == "0":
        pytest.skip(f"{PG_CONTAINER_FLAG}=0 — hermetic lane disabled")
    if not _docker_daemon_reachable():
        pytest.skip("docker daemon not reachable")


@pytest.fixture(scope="session")
def pg_container() -> Iterator[str]:
    """Boot a Postgres testcontainer + apply every non-cron migration.

    Yields the DSN of the live container (libpq form, e.g.
    ``postgresql://test:test@127.0.0.1:55432/test``). Skips when
    Docker is unavailable so contributors without a daemon can still
    run the legacy lane.
    """
    _skip_unless_docker()

    from testcontainers.postgres import PostgresContainer

    container = PostgresContainer(
        image="postgres:16-alpine",
        username="test",
        password="test",
        dbname="test",
    )
    container.start()
    try:
        # testcontainers ≥4 returns a SQLAlchemy-style URL
        # (postgresql+psycopg2://). psycopg.connect needs the libpq form.
        url = container.get_connection_url().replace("+psycopg2", "")
        apply_migrations(url)
        yield url
    finally:
        container.stop()


@pytest.fixture(scope="session")
def supabase_stack() -> Iterator[StackEndpoints]:
    """Boot Postgres + PostgREST so ``supabase-py`` can hit the stack.

    The stack survives the whole pytest session — container startup is
    slow (~5 s) and the schema is ready-only after migrations land. Per
    test isolation is the consumer's problem (see ``pg_isolation`` for
    the TRUNCATE-per-test pattern).
    """
    _skip_unless_docker()

    endpoints, containers, network = boot_supabase_stack()
    try:
        apply_migrations(endpoints.db_dsn)
        # PostgREST caches the schema on startup, before our migrations
        # run, so it doesn't see the public.* tables yet. NOTIFY pgrst
        # to reload the schema cache; PostgREST 12 listens on this
        # channel by default.
        import psycopg

        with psycopg.connect(endpoints.db_dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("NOTIFY pgrst, 'reload schema'")
        yield endpoints
    finally:
        for c in reversed(containers):
            try:
                c.stop()
            except Exception:  # pragma: no cover
                pass
        try:
            network.remove()
        except Exception:  # pragma: no cover
            pass


@pytest.fixture()
def pg_isolation(supabase_stack: StackEndpoints) -> Iterator[None]:
    """TRUNCATE every public table after the test runs.

    PostgREST opens its own DB connections, so a per-test BEGIN/ROLLBACK
    in the test process doesn't isolate writes that go through the REST
    surface. Truncating the public tables (excluding the migration
    ledger) between tests gives the same effect at higher cost. Cheap
    enough at this dataset size (<10 tables, all small) that we don't
    need to optimise further.
    """
    yield
    import psycopg

    with psycopg.connect(supabase_stack.db_dsn) as conn:
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


@pytest.fixture()
def hermetic_supabase_client(supabase_stack: StackEndpoints):
    """Hand back a configured ``supabase.Client`` pointed at the stack.

    Tests that exercise the service layer typically don't construct
    the client themselves — they import it indirectly through the
    FastAPI app. For tests that *do* want to drive the client directly
    (e.g. a quick repository smoke test), this fixture saves the
    ``create_client(url, key)`` ceremony.
    """
    from supabase import create_client

    return create_client(supabase_stack.base_url, supabase_stack.service_role_key)
