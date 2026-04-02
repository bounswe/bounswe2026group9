import os
from unittest.mock import patch

os.environ["TESTING"] = "1"  # Disable rate limiting during tests

import pytest
from fastapi.testclient import TestClient

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


@pytest.fixture(autouse=True)
def cleanup_test_users(db):
    """Clean up test users created by the current CI/local test run."""
    yield
    db.table("users").delete().like("email", cleanup_email_pattern()).execute()
