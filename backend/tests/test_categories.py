"""Tests for Category endpoints."""

from fastapi.testclient import TestClient

from app.database import get_supabase
from app.main import app
from app.services.auth import create_access_token

client = TestClient(app)
db = get_supabase()


def _auth_header(user_id: str) -> dict:
    token = create_access_token(user_id, "test@test.com")
    return {"Authorization": f"Bearer {token}"}


def _create_test_user() -> dict:
    import uuid
    unique = uuid.uuid4().hex[:8]
    result = db.table("users").insert({
        "username": f"cattest_{unique}",
        "email": f"cattest_{unique}@example.com",
        "hashed_password": "fakehash",
        "role": "registered",
        "auth_provider": "local",
        "email_verified": True,
        "is_active": True,
    }).execute()
    return result.data[0]


def _cleanup_user(user_id: str):
    db.table("users").delete().eq("id", user_id).execute()


def _cleanup_category(category_id: str):
    db.table("categories").delete().eq("id", category_id).execute()


class TestListCategories:

    def test_list_predefined(self):
        resp = client.get("/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 15  # 15 seeded predefined categories
        assert all(cat["is_predefined"] or cat["is_approved"] for cat in data)

    def test_list_sorted_by_name(self):
        resp = client.get("/categories")
        names = [cat["name"] for cat in resp.json()]
        assert names == sorted(names)

    def test_search_categories(self):
        resp = client.get("/categories?search=Music")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any("Music" in cat["name"] for cat in data)

    def test_search_no_results(self):
        resp = client.get("/categories?search=xyznonexistent")
        assert resp.status_code == 200
        assert resp.json() == []


class TestCreateCategory:

    def test_create_custom_category(self):
        user = _create_test_user()
        import uuid
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

        _cleanup_category(data["id"])
        _cleanup_user(user["id"])

    def test_create_duplicate_fails(self):
        user = _create_test_user()

        resp = client.post(
            "/categories",
            json={"name": "Music"},  # Already exists as predefined
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 409

        _cleanup_user(user["id"])

    def test_create_no_auth(self):
        resp = client.post("/categories", json={"name": "NoAuth"})
        assert resp.status_code == 403

    def test_create_empty_name(self):
        user = _create_test_user()
        resp = client.post(
            "/categories",
            json={"name": ""},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 422
        _cleanup_user(user["id"])

    def test_custom_not_in_listing_until_approved(self):
        """Custom category is not visible in listing until approved."""
        user = _create_test_user()
        import uuid
        cat_name = f"Pending_{uuid.uuid4().hex[:8]}"

        create_resp = client.post(
            "/categories",
            json={"name": cat_name},
            headers=_auth_header(user["id"]),
        )
        cat_id = create_resp.json()["id"]

        list_resp = client.get(f"/categories?search={cat_name}")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 0  # Not approved, not in listing

        _cleanup_category(cat_id)
        _cleanup_user(user["id"])
