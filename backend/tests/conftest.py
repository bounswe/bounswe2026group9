from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.database import get_supabase
from app.main import app
from tests_support import build_test_identity, cleanup_username_patterns


@pytest.fixture()
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture()
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


@pytest.fixture(autouse=True)
def disable_email_sending():
    """Prevent real emails from being sent during tests."""
    with patch("app.routers.auth.send_verification_email", return_value=False):
        yield


@pytest.fixture(autouse=True)
def cleanup_test_users(db):
    """Clean up test users after each test (all test prefixes)."""
    yield
    for prefix in cleanup_username_patterns():
        db.table("users").delete().like("username", prefix).execute()
