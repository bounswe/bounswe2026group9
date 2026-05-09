import time
from unittest.mock import MagicMock

import pytest
from jose import JWTError

from app.services.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


@pytest.fixture
def db() -> MagicMock:
    """Override the conftest session-scoped ``db`` so this file doesn't
    contact a real Supabase. The autouse ``cleanup_test_users`` fixture
    requests ``db`` and would otherwise resolve the real client at
    ``SUPABASE_URL=fake``, which fails before any test runs."""
    return MagicMock(name="supabase_client")


class TestPassword:
    def test_hash_and_verify(self):
        password = "securepass123"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correctpass")
        assert not verify_password("wrongpass", hashed)

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("samepass")
        h2 = hash_password("samepass")
        assert h1 != h2  # bcrypt uses random salt


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token("user-123", "test@example.com")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    def test_invalid_token_raises(self):
        with pytest.raises(JWTError):
            decode_access_token("invalid.token.here")

    def test_expired_token_raises(self):
        from app.config import settings

        original = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        settings.ACCESS_TOKEN_EXPIRE_MINUTES = 0
        token = create_access_token("user-123", "test@example.com")
        settings.ACCESS_TOKEN_EXPIRE_MINUTES = original
        time.sleep(1)
        with pytest.raises(JWTError):
            decode_access_token(token)
