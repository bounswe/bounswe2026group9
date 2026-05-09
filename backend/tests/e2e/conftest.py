"""Fixtures dedicated to the end-to-end suite.

The E2E lane uses the same database mode as the job that invokes it:
the default PR lane points at the shared TEST_SUPABASE_* project, while
the opt-in hermetic lane can still set ``PG_CONTAINER=1`` and get the
local Postgres + PostgREST stack from the top-level conftest. Every
scenario uses the live FastAPI ``TestClient`` so the path covers the
full router → service → repository → DB chain without faking any layer.

Why a separate conftest
=======================

The existing ``tests/conftest.py`` autouse fixtures handle cleanup for
both modes: email-pattern cleanup on the shared Supabase project and
TRUNCATE cleanup when ``PG_CONTAINER=1``. The E2E suite only adds a
fresh client fixture and keeps email sending mocked so the verification
flow can complete without SMTP.

Tests in ``tests/e2e/`` should call ``e2e_client``, not the top-level
``client`` fixture, so the bootstrap order is deterministic.
"""
from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


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
    email as verified). Returns the same supabase-py client the app uses,
    whether the active lane is shared Supabase or the hermetic stack."""
    from app.database import get_supabase

    return get_supabase()
