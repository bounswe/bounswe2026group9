"""Apply ``sql/*.sql`` migrations to a Postgres URL in lexical order.

Replaces the current "paste SQL into the Supabase dashboard" workflow with
a Python runner that's idempotent and CI-friendly. The runner is the
seam through which the testcontainers fixture seeds a hermetic database;
production migrations still go through Supabase by design.

Idempotency model
=================

Each migration's stem (``001_create_tables``) is recorded in
``_test_migrations(name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ)``.
Re-running the migrator is a no-op once every file has been applied
once. There is no down-migration concept — tests get a brand-new
container on every run, so we never need to roll back.

Skipping Supabase-only files
============================

A handful of migrations (``003_pg_cron_auto_end.sql``,
``008_token_cleanup_cron.sql``) lean on the ``pg_cron`` extension that
Supabase ships but stock Postgres does not. Pass ``skip=`` to drop
those by stem prefix (e.g. ``("003_", "008_")``); the scheduled-job
behaviour they wire up is independently unit-tested in the service
layer.

Bootstrap roles
===============

A handful of migrations also ``GRANT ... TO anon, authenticated,
service_role`` because Supabase pre-creates those roles. Plain Postgres
does not, so we create them with ``NOLOGIN`` before applying anything.
"""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import psycopg

# Migrations that depend on the pg_cron extension Supabase manages but
# upstream Postgres does not ship by default. Their behaviour is
# scheduled-job glue that we cover at the service layer instead.
DEFAULT_SKIP = ("003_", "008_")

# Roles Supabase pre-creates and a few of our migrations grant against.
# Stock Postgres has no equivalent; create them as login-less roles so
# the GRANT statements succeed without changing semantics in production.
_BOOTSTRAP_ROLES_SQL = """
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    CREATE ROLE anon NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    CREATE ROLE authenticated NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    CREATE ROLE service_role NOLOGIN;
  END IF;
END $$;
"""

_LEDGER_SQL = """
CREATE TABLE IF NOT EXISTS _test_migrations (
  name        TEXT        PRIMARY KEY,
  applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


def _migration_files(migrations_dir: Path) -> list[Path]:
    return sorted(p for p in migrations_dir.glob("*.sql"))


def _is_skipped(stem: str, skip: Iterable[str]) -> bool:
    return any(stem.startswith(prefix) for prefix in skip)


def apply_migrations(
    dsn: str,
    *,
    migrations_dir: Path | None = None,
    skip: Iterable[str] = DEFAULT_SKIP,
) -> list[str]:
    """Apply every ``*.sql`` under ``migrations_dir`` against ``dsn``.

    Returns the ordered list of migration stems that were applied this
    run (already-applied entries are skipped silently). Each migration
    runs inside its own transaction; failure aborts only that file and
    re-raises so the caller can surface the file name.
    """
    if migrations_dir is None:
        migrations_dir = Path(__file__).resolve().parents[2] / "sql"

    files = _migration_files(migrations_dir)
    if not files:
        return []

    applied: list[str] = []
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(_BOOTSTRAP_ROLES_SQL)
            cur.execute(_LEDGER_SQL)

        for path in files:
            stem = path.stem  # e.g. "001_create_tables"
            if _is_skipped(stem, skip):
                continue

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM _test_migrations WHERE name = %s",
                    (stem,),
                )
                if cur.fetchone() is not None:
                    continue

            sql = path.read_text(encoding="utf-8")
            try:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(sql)
                        cur.execute(
                            "INSERT INTO _test_migrations (name) VALUES (%s)",
                            (stem,),
                        )
            except psycopg.Error as exc:  # pragma: no cover - exercised in tests
                raise RuntimeError(f"migration {stem} failed: {exc}") from exc

            applied.append(stem)

    return applied
