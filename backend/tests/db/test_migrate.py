"""Smoke test for `tests/db/migrate.py` against a real Postgres.

Boots the session-scoped `pg_container`, asserts every non-skipped
migration is recorded in `_test_migrations`, and that re-running the
runner is a no-op. Validates the seam the rest of the hermetic lane
will lean on.
"""
from __future__ import annotations

import psycopg
import pytest

from tests.db.migrate import DEFAULT_SKIP, apply_migrations


def _stems_in_repo() -> list[str]:
    from pathlib import Path

    sql_dir = Path(__file__).resolve().parents[2] / "sql"
    return sorted(p.stem for p in sql_dir.glob("*.sql"))


def test_first_run_applies_every_non_skipped_migration(pg_container: str) -> None:
    # Fixture has already run once at startup; querying the ledger should
    # show the same count as the on-disk file list minus the skip prefixes.
    expected = [
        s for s in _stems_in_repo()
        if not any(s.startswith(p) for p in DEFAULT_SKIP)
    ]

    with psycopg.connect(pg_container) as conn, conn.cursor() as cur:
        cur.execute("SELECT name FROM _test_migrations ORDER BY name")
        recorded = [row[0] for row in cur.fetchall()]

    assert recorded == expected


def test_second_run_is_a_no_op(pg_container: str) -> None:
    applied_again = apply_migrations(pg_container)
    assert applied_again == [], (
        "Re-running the migrator on a populated DB must apply nothing."
    )


def test_unaccent_extension_is_available(pg_container: str) -> None:
    """Migration 016 requires unaccent; alpine image must have it."""
    with psycopg.connect(pg_container) as conn, conn.cursor() as cur:
        cur.execute("SELECT unaccent('Beşiktaş')")
        assert cur.fetchone()[0].lower().startswith("besik")


def test_search_events_text_function_callable(pg_container: str) -> None:
    """The function defined by 016 should be invocable on an empty DB."""
    with psycopg.connect(pg_container) as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM search_events_text('anything')")
        assert cur.fetchall() == []


def test_bootstrap_roles_exist(pg_container: str) -> None:
    """`anon`, `authenticated`, `service_role` are precreated by the migrator."""
    with psycopg.connect(pg_container) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT rolname FROM pg_roles WHERE rolname IN "
            "('anon', 'authenticated', 'service_role')"
        )
        names = {row[0] for row in cur.fetchall()}
    assert names == {"anon", "authenticated", "service_role"}


@pytest.mark.parametrize("table_name", [
    "users",
    "events",
    "event_locations",
    "event_categories",
    "event_segments",
    "comments",
    "notifications",
    "bookmarks",
    "attendances",
    "ratings",
    "event_invites",
    "refresh_tokens",
])
def test_core_tables_exist(pg_container: str, table_name: str) -> None:
    """Spot-check that the core schema landed without an error path."""
    with psycopg.connect(pg_container) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s",
            (table_name,),
        )
        assert cur.fetchone() is not None, f"missing public.{table_name}"
