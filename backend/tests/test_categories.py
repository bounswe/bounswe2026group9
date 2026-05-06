"""Contract tests for /categories endpoints.

Phase 2 retains one happy-path integration test per HTTP endpoint.
Branch coverage (search filtering, duplicate detection, approval gating)
lives in tests/test_category_unit.py.
"""

import uuid

from fastapi.testclient import TestClient

from app.database import get_supabase
from app.main import app
from app.services.auth import create_access_token
from tests_support import build_test_identity

client = TestClient(app)
db = get_supabase()


def _auth_header(user_id: str) -> dict:
    token = create_access_token(user_id, "test@test.com")
    return {"Authorization": f"Bearer {token}"}


def _create_test_user() -> dict:
    username, email = build_test_identity("cattest")
    result = db.table("users").insert({
        "username": username, "email": email,
        "hashed_password": "fakehash", "role": "registered",
        "auth_provider": "local", "email_verified": True, "is_active": True,
    }).execute()
    return result.data[0]


# --- Contract tests (one happy path per endpoint) ---


class TestListCategories:
    """GET /categories"""

    def test_list_returns_predefined_alphabetically(self):
        resp = client.get("/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 15  # seeded predefined set
        names = [cat["name"] for cat in data]
        assert names == sorted(names)


class TestCreateCategory:
    """POST /categories"""

    def test_create_custom_category_pending_approval(self):
        user = _create_test_user()
        cat_name = f"TestCategory_{uuid.uuid4().hex[:8]}"

        resp = client.post(
            "/categories",
            json={"name": cat_name},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == cat_name
        assert data["is_predefined"] is False
        assert data["is_approved"] is False

        # Custom category is not visible in listing until approved.
        list_resp = client.get(f"/categories?search={cat_name}")
        assert list_resp.json() == []

        db.table("categories").delete().eq("id", data["id"]).execute()
        db.table("users").delete().eq("id", user["id"]).execute()
