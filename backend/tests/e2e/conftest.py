"""Fixtures dedicated to the end-to-end suite.

The E2E lane piggybacks on the hermetic stack from ``tests/db/`` so
each scenario boots Postgres + PostgREST once and runs against a
clean schema. Every scenario uses the live FastAPI ``TestClient`` so
the path covers the full router → service → repository → DB chain
without faking any layer.

Why a separate conftest
=======================

The existing ``tests/conftest.py`` autouse fixtures (cleanup_test_users,
disable_email_sending) assume the legacy lane's setup. The E2E suite
gets its own fixture chain so:
  - it can require the hermetic stack unconditionally (skip otherwise)
  - per-test isolation is ``TRUNCATE`` rather than email-pattern delete
  - email sending stays mocked so the verification flow can complete
    without SMTP

Tests in ``tests/e2e/`` should call ``e2e_client``, not the top-level
``client`` fixture, so the bootstrap order is deterministic.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def _require_pg_container() -> None:
    if os.getenv("PG_CONTAINER") != "1":
        pytest.skip("E2E suite requires PG_CONTAINER=1 (hermetic lane)")


@pytest.fixture(scope="session", autouse=True)
def _silence_real_email() -> Iterator[None]:
    """E2E flows hit the auth/register endpoint, which would otherwise
    try to send real verification email. The ``email_verified=True``
    pattern below is fine for E2E because the scenarios don't exercise
    the verification path itself; that's covered by the unit suite."""
    with (
        patch("app.routers.auth.send_verification_email", return_value=False),
        patch("app.routers.auth.store_verification_token", return_value=None),
    ):
        yield


@pytest.fixture
def e2e_client() -> TestClient:
    """A fresh TestClient — the underlying app singleton is shared but
    cookies/headers are isolated per test by virtue of using a new
    ``TestClient`` instance."""
    from app.main import app

    return TestClient(app)


@pytest.fixture
def admin_db():
    """Direct DB handle for E2E setup that has to bypass authz (e.g.
    seeding ``ended`` events for rating eligibility, or marking a user's
    email as verified). Returns the supabase-py client pointed at the
    local stack — same client the app uses, so writes are real."""
    from app.database import get_supabase

    return get_supabase()
