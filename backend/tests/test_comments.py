"""Contract tests for /events/{event_id}/comments endpoints.

Phase 2 retains one happy-path integration test per HTTP endpoint. Branch
coverage (404/403/lifecycle gates, nesting depth, reply assembly,
soft-delete invariants) lives in tests/test_comment_unit.py.
"""

import io
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image as PILImage

from app.database import get_supabase
from app.main import app
from app.services.auth import create_access_token
from tests_support import build_test_identity

client = TestClient(app)
db = get_supabase()
MOCK_STORAGE_URL = "https://example.com/storage/v1/object/public/event-images/test.jpg"


def _auth_header(user_id: str) -> dict:
    token = create_access_token(user_id, "test@test.com")
    return {"Authorization": f"Bearer {token}"}


def _create_test_user(prefix: str = "cmttest") -> dict:
    username, email = build_test_identity(prefix)
    resp = client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "testpass123",
        "date_of_birth": "2000-01-15",
    })
    assert resp.status_code == 201, f"User registration failed: {resp.json()}"
    return resp.json()["user"]


def _get_category_id() -> str:
    result = db.table("categories").select("id").eq("is_predefined", True).limit(1).execute()
    return result.data[0]["id"]


def _make_image_bytes() -> bytes:
    img = PILImage.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
def _create_published_event(host_id: str, mock_upload) -> dict:  # noqa: ARG001
    cat_id = _get_category_id()
    start = datetime.now(UTC) + timedelta(days=5)
    end = start + timedelta(hours=2)
    body = {
        "title": f"Comment Test Event {uuid.uuid4().hex[:6]}",
        "description": "Event for comment testing",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "visibility": "public",
        "is_age_restricted": False,
        "status": "draft",
        "category_ids": [cat_id],
        "locations": [{"name": "Test Venue", "latitude": 41.0, "longitude": 29.0, "is_primary": True, "order_index": 0}],
    }
    resp = client.post("/events", json=body, headers=_auth_header(host_id))
    event_id = resp.json()["id"]
    client.post(
        f"/events/{event_id}/images",
        files={"file": ("test.jpg", _make_image_bytes(), "image/jpeg")},
        headers=_auth_header(host_id),
    )
    client.patch(
        f"/events/{event_id}/status",
        json={"status": "published"},
        headers=_auth_header(host_id),
    )
    return resp.json()


# --- Contract tests (one happy path per endpoint) ---


class TestCreateComment:
    """POST /events/{event_id}/comments"""

    def test_create_comment_success(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])
        commenter = _create_test_user()

        resp = client.post(
            f"/events/{event['id']}/comments",
            json={"text": "Great event!"},
            headers=_auth_header(commenter["id"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["text"] == "Great event!"
        assert data["user"]["id"] == commenter["id"]
        assert data["user"]["username"] == commenter["username"]
        assert data["event_id"] == event["id"]


class TestListComments:
    """GET /events/{event_id}/comments"""

    def test_list_comments_with_data(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])
        commenter = _create_test_user()

        for i in range(3):
            client.post(
                f"/events/{event['id']}/comments",
                json={"text": f"Comment {i}"},
                headers=_auth_header(commenter["id"]),
            )

        resp = client.get(f"/events/{event['id']}/comments")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3
        # Newest-first contract: response is descending by created_at
        assert data["items"][0]["text"] == "Comment 2"


class TestDeleteComment:
    """DELETE /events/{event_id}/comments/{comment_id}"""

    def test_owner_can_delete(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])
        commenter = _create_test_user()

        resp = client.post(
            f"/events/{event['id']}/comments",
            json={"text": "To be deleted"},
            headers=_auth_header(commenter["id"]),
        )
        comment_id = resp.json()["id"]

        resp = client.delete(
            f"/events/{event['id']}/comments/{comment_id}",
            headers=_auth_header(commenter["id"]),
        )
        assert resp.status_code == 200
        assert "deleted" in resp.json()["message"].lower()
