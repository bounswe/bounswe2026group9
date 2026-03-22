"""Integration tests: multi-step auth flows."""

from unittest.mock import patch

# ==================== Full Auth Flow ====================


class TestFullAuthFlow:
    """Register → login → me → refresh → logout → verify refresh fails."""

    def test_complete_flow(self, client, test_user_data):
        # 1. Register
        reg = client.post("/auth/register", json=test_user_data)
        assert reg.status_code == 201
        access_token = reg.json()["access_token"]

        # 2. Login with same credentials
        login = client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        })
        assert login.status_code == 200
        access_token = login.json()["access_token"]

        # 3. Me with login token
        me = client.get("/auth/me", headers={
            "Authorization": f"Bearer {access_token}"
        })
        assert me.status_code == 200
        assert me.json()["username"] == test_user_data["username"]

        # 4. Refresh — get new token
        refresh = client.post("/auth/refresh", json={})
        assert refresh.status_code == 200
        new_token = refresh.json()["access_token"]
        assert new_token != access_token

        # 5. Me still works with new token
        me2 = client.get("/auth/me", headers={
            "Authorization": f"Bearer {new_token}"
        })
        assert me2.status_code == 200

        # 6. Logout
        logout = client.post("/auth/logout", json={})
        assert logout.status_code == 200

        # 7. Refresh after logout fails
        refresh2 = client.post("/auth/refresh", json={})
        assert refresh2.status_code == 401


# ==================== Refresh Token Rotation ====================


class TestRefreshTokenRotation:
    def test_rotation_issues_new_token(self, client, test_user_data):
        # Register
        client.post("/auth/register", json=test_user_data)

        # Login
        client.post("/auth/login", json={
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        })

        # First refresh
        r1 = client.post("/auth/refresh", json={})
        assert r1.status_code == 200
        token1 = r1.json()["access_token"]

        # Second refresh — should still work (cookie updated)
        r2 = client.post("/auth/refresh", json={})
        assert r2.status_code == 200
        token2 = r2.json()["access_token"]

        assert token1 != token2


# ==================== Email Verification Flow ====================


class TestEmailVerificationFlow:
    def test_register_verify_confirm(self, client, test_user_data, db):
        # Register (email not verified)
        reg = client.post("/auth/register", json=test_user_data)
        user_id = reg.json()["user"]["id"]
        assert reg.json()["user"]["email_verified"] is False

        # Get token from DB
        result = db.table("email_verification_tokens").select("token").eq(
            "user_id", user_id
        ).execute()
        token = result.data[0]["token"]

        # Verify
        verify = client.get(f"/auth/verify-email?token={token}")
        assert verify.status_code == 200

        # Confirm in DB
        user = db.table("users").select("email_verified").eq(
            "id", user_id
        ).execute().data[0]
        assert user["email_verified"] is True

        # Using same token again should fail (deleted)
        verify2 = client.get(f"/auth/verify-email?token={token}")
        assert verify2.status_code == 400

    def test_resend_then_verify(self, client, test_user_data, db):
        # Register
        reg = client.post("/auth/register", json=test_user_data)
        user_id = reg.json()["user"]["id"]
        access_token = reg.json()["access_token"]

        # Resend verification
        resend = client.post("/auth/resend-verification", headers={
            "Authorization": f"Bearer {access_token}"
        })
        assert resend.status_code == 200

        # Get new token from DB and verify
        result = db.table("email_verification_tokens").select("token").eq(
            "user_id", user_id
        ).execute()
        token = result.data[0]["token"]

        verify = client.get(f"/auth/verify-email?token={token}")
        assert verify.status_code == 200

        # Resend again should fail — already verified
        resend2 = client.post("/auth/resend-verification", headers={
            "Authorization": f"Bearer {access_token}"
        })
        assert resend2.status_code == 400

    def test_expired_verification_token(self, client, test_user_data, db):
        # Register
        reg = client.post("/auth/register", json=test_user_data)
        user_id = reg.json()["user"]["id"]

        # Expire the token manually
        db.table("email_verification_tokens").update({
            "expires_at": "2020-01-01T00:00:00Z"
        }).eq("user_id", user_id).execute()

        result = db.table("email_verification_tokens").select("token").eq(
            "user_id", user_id
        ).execute()
        token = result.data[0]["token"]

        # Should fail — expired
        verify = client.get(f"/auth/verify-email?token={token}")
        assert verify.status_code == 400


# ==================== Google OAuth Flow (mocked) ====================


class TestGoogleOAuth:
    MOCK_GOOGLE_USER = {
        "id": "google_123456",
        "email": "googleuser@gmail.com",
        "verified_email": True,
    }
    MOCK_GOOGLE_TOKENS = {
        "access_token": "mock_google_access",
        "token_type": "Bearer",
    }

    def _mock_oauth_callback(self, client, db):
        """Helper: simulate Google OAuth callback with mocked Google APIs."""
        state = "test_state_123"
        client.cookies.set("oauth_state", state)

        with patch("app.routers.auth.exchange_code_for_tokens", return_value=self.MOCK_GOOGLE_TOKENS), \
             patch("app.routers.auth.get_google_user_info", return_value=self.MOCK_GOOGLE_USER):
            response = client.get(
                f"/auth/google/callback?code=mock_code&state={state}",
                follow_redirects=False,
            )
        return response

    def test_new_user_created(self, client, db):
        # Ensure user doesn't exist
        db.table("users").delete().eq("email", self.MOCK_GOOGLE_USER["email"]).execute()

        response = self._mock_oauth_callback(client, db)
        # Should redirect to frontend
        assert response.status_code == 307

        # User should exist in DB
        result = db.table("users").select("*").eq(
            "email", self.MOCK_GOOGLE_USER["email"]
        ).execute()
        assert len(result.data) == 1
        user = result.data[0]
        assert user["auth_provider"] == "google"
        assert user["google_id"] == "google_123456"
        assert user["email_verified"] is True

        # Cleanup
        db.table("users").delete().eq("email", self.MOCK_GOOGLE_USER["email"]).execute()

    def test_existing_user_linked(self, client, test_user_data, db):
        # Register local user with same email as mock Google user
        test_user_data["email"] = self.MOCK_GOOGLE_USER["email"]
        reg = client.post("/auth/register", json=test_user_data)
        user_id = reg.json()["user"]["id"]

        response = self._mock_oauth_callback(client, db)
        assert response.status_code == 307

        # User should now have google_id linked
        user = db.table("users").select("google_id, email_verified").eq(
            "id", user_id
        ).execute().data[0]
        assert user["google_id"] == "google_123456"
        assert user["email_verified"] is True

    def test_deactivated_user_rejected(self, client, test_user_data, db):
        # Register and deactivate
        test_user_data["email"] = self.MOCK_GOOGLE_USER["email"]
        reg = client.post("/auth/register", json=test_user_data)
        user_id = reg.json()["user"]["id"]
        db.table("users").update({"is_active": False}).eq("id", user_id).execute()

        response = self._mock_oauth_callback(client, db)
        assert response.status_code == 403
