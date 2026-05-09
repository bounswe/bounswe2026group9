"""Contract tests for /auth endpoints.

Phase 2 retains one happy-path integration test per HTTP endpoint —
service-level branching (validation, lockout, deactivation, token rotation,
verification edge cases) lives in tests/test_auth_unit.py.
"""

from unittest.mock import patch

from tests_support import build_test_email

# ==================== Register / Login / Me / Refresh / Logout ====================


class TestRegister:
    """POST /auth/register"""

    def test_register_success(self, client, test_user_data):
        response = client.post("/auth/register", json=test_user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["username"] == test_user_data["username"]
        assert data["user"]["email"] == test_user_data["email"]
        assert data["user"]["email_verified"] is False
        assert data["user"]["role"] == "registered"
        assert "access_token" in data


class TestLogin:
    """POST /auth/login"""

    def test_login_success(self, client, registered_user):
        response = client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == registered_user["email"]
        assert "access_token" in data


class TestMe:
    """GET /auth/me"""

    def test_me_with_valid_token(self, client, registered_user):
        response = client.get("/auth/me", headers={
            "Authorization": f"Bearer {registered_user['access_token']}",
        })
        assert response.status_code == 200
        assert response.json()["email"] == registered_user["email"]


class TestRefresh:
    """POST /auth/refresh"""

    def test_refresh_with_cookie(self, client, registered_user):
        client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        response = client.post("/auth/refresh", json={})
        assert response.status_code == 200
        assert "access_token" in response.json()


class TestLogout:
    """POST /auth/logout"""

    def test_logout(self, client, registered_user):
        client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        response = client.post("/auth/logout", json={})
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"


# ==================== Email Verification ====================


class TestEmailVerification:
    """GET /auth/verify-email + POST /auth/resend-verification"""

    def test_verify_with_valid_token(
        self, client, registered_user, db, captured_verification_tokens,
    ):
        user_id = registered_user["user"]["id"]
        token = captured_verification_tokens.get(user_id)
        assert token, "Verification token should have been captured during register"

        response = client.get(f"/auth/verify-email?token={token}")
        assert response.status_code == 200
        assert response.json()["message"] == "Email verified successfully"

        user = db.table("users").select("email_verified").eq(
            "id", user_id,
        ).execute().data[0]
        assert user["email_verified"] is True

    def test_resend_verification(self, client, registered_user):
        response = client.post("/auth/resend-verification", headers={
            "Authorization": f"Bearer {registered_user['access_token']}",
        })
        assert response.status_code == 200


# ==================== Google OAuth ====================


class TestGoogleOAuth:
    """GET /auth/google/callback — Google OAuth flow."""

    MOCK_GOOGLE_USER = {
        "id": "google_123456",
        "email": "",
        "verified_email": True,
    }
    MOCK_GOOGLE_TOKENS = {
        "access_token": "mock_google_access",
        "token_type": "Bearer",
    }

    def test_new_user_created_via_google(self, client, db):
        google_user = {**self.MOCK_GOOGLE_USER, "email": build_test_email("googleuser")}
        db.table("users").delete().eq("email", google_user["email"]).execute()

        state = "test_state_123"
        client.cookies.set("oauth_state", state)

        with patch("app.routers.auth.exchange_code_for_tokens", return_value=self.MOCK_GOOGLE_TOKENS), \
             patch("app.routers.auth.get_google_user_info", return_value=google_user):
            response = client.get(
                f"/auth/google/callback?code=mock_code&state={state}",
                follow_redirects=False,
            )

        assert response.status_code == 307  # redirect to frontend

        result = db.table("users").select("auth_provider,google_id,email_verified").eq(
            "email", google_user["email"],
        ).execute()
        assert len(result.data) == 1
        user = result.data[0]
        assert user["auth_provider"] == "google"
        assert user["google_id"] == "google_123456"
        assert user["email_verified"] is True

        db.table("users").delete().eq("email", google_user["email"]).execute()
