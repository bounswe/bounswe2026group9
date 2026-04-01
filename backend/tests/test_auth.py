from tests_support import build_test_email, build_test_identity

# ==================== Register ====================


class TestRegister:
    def test_register_success(self, client, test_user_data):
        response = client.post("/auth/register", json=test_user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["username"] == test_user_data["username"]
        assert data["user"]["email"] == test_user_data["email"]
        assert data["user"]["email_verified"] is False
        assert data["user"]["role"] == "registered"
        assert "access_token" in data

    def test_duplicate_email(self, client, test_user_data):
        client.post("/auth/register", json=test_user_data)
        # Same email, different username
        test_user_data["username"] = build_test_identity("differentuser")[0]
        response = client.post("/auth/register", json=test_user_data)
        assert response.status_code == 409
        assert "Email already registered" in response.json()["detail"]

    def test_duplicate_username(self, client, test_user_data):
        client.post("/auth/register", json=test_user_data)
        # Same username, different email
        test_user_data["email"] = build_test_email("different")
        response = client.post("/auth/register", json=test_user_data)
        assert response.status_code == 409
        assert "Username already taken" in response.json()["detail"]

    def test_short_password(self, client, test_user_data):
        test_user_data["password"] = "123"
        response = client.post("/auth/register", json=test_user_data)
        assert response.status_code == 422

    def test_invalid_email(self, client, test_user_data):
        test_user_data["email"] = "notanemail"
        response = client.post("/auth/register", json=test_user_data)
        assert response.status_code == 422

    def test_short_username(self, client, test_user_data):
        test_user_data["username"] = "ab"
        response = client.post("/auth/register", json=test_user_data)
        assert response.status_code == 422


# ==================== Login ====================


class TestLogin:
    def test_login_success(self, client, registered_user):
        response = client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == registered_user["email"]
        assert "access_token" in data

    def test_wrong_password(self, client, registered_user):
        response = client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    def test_nonexistent_email(self, client):
        response = client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": "whatever",
        })
        assert response.status_code == 401

    def test_account_lockout(self, client, registered_user):
        for _ in range(5):
            client.post("/auth/login", json={
                "email": registered_user["email"],
                "password": "wrongpassword",
            })
        # 6th attempt should be locked
        response = client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert response.status_code == 429
        assert "locked" in response.json()["detail"].lower()

    def test_deactivated_account(self, client, registered_user, db):
        db.table("users").update({"is_active": False}).eq(
            "id", registered_user["user"]["id"]
        ).execute()
        response = client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert response.status_code == 403


# ==================== Me / Refresh / Logout ====================


class TestTokenFlow:
    def test_me_with_valid_token(self, client, registered_user):
        response = client.get("/auth/me", headers={
            "Authorization": f"Bearer {registered_user['access_token']}"
        })
        assert response.status_code == 200
        assert response.json()["email"] == registered_user["email"]

    def test_me_with_invalid_token(self, client):
        response = client.get("/auth/me", headers={
            "Authorization": "Bearer invalidtoken"
        })
        assert response.status_code == 401

    def test_me_without_token(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_refresh_with_cookie(self, client, registered_user):
        # Login sets cookie, then refresh
        client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        response = client.post("/auth/refresh", json={})
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_refresh_old_token_revoked(self, client, registered_user, db):
        # Login to get a refresh token
        login_resp = client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        assert login_resp.status_code == 200

        # Grab the old refresh token from DB (most recent for this user)
        user_id = registered_user["user"]["id"]
        tokens = db.table("refresh_tokens").select("token").eq(
            "user_id", user_id
        ).eq("revoked", False).execute()
        old_token = tokens.data[-1]["token"]

        # Refresh — this rotates the token (old revoked, new issued)
        refresh_resp = client.post("/auth/refresh", json={"refresh_token": old_token})
        assert refresh_resp.status_code == 200

        # Try old token again — should be revoked
        retry_resp = client.post("/auth/refresh", json={"refresh_token": old_token})
        assert retry_resp.status_code == 401

    def test_logout(self, client, registered_user):
        # Login to set cookie
        client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        response = client.post("/auth/logout", json={})
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"

    def test_refresh_after_logout_fails(self, client, registered_user):
        client.post("/auth/login", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        })
        client.post("/auth/logout", json={})
        response = client.post("/auth/refresh", json={})
        assert response.status_code == 401


# ==================== Email Verification ====================


class TestEmailVerification:
    def test_verify_with_valid_token(self, client, registered_user, db):
        # Get verification token from DB
        result = db.table("email_verification_tokens").select("token").eq(
            "user_id", registered_user["user"]["id"]
        ).execute()
        assert result.data, "Verification token should exist after register"
        token = result.data[0]["token"]

        response = client.get(f"/auth/verify-email?token={token}")
        assert response.status_code == 200
        assert response.json()["message"] == "Email verified successfully"

        # Confirm user is now verified
        user = db.table("users").select("email_verified").eq(
            "id", registered_user["user"]["id"]
        ).execute().data[0]
        assert user["email_verified"] is True

    def test_verify_with_invalid_token(self, client):
        response = client.get("/auth/verify-email?token=invalidtoken123")
        assert response.status_code == 400

    def test_resend_verification(self, client, registered_user):
        response = client.post("/auth/resend-verification", headers={
            "Authorization": f"Bearer {registered_user['access_token']}"
        })
        assert response.status_code == 200

    def test_resend_when_already_verified(self, client, registered_user, db):
        db.table("users").update({"email_verified": True}).eq(
            "id", registered_user["user"]["id"]
        ).execute()
        response = client.post("/auth/resend-verification", headers={
            "Authorization": f"Bearer {registered_user['access_token']}"
        })
        assert response.status_code == 400
        assert "already verified" in response.json()["detail"].lower()
