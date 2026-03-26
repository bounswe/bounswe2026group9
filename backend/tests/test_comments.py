"""Tests for comment endpoints — create, list, delete."""

import io
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image as PILImage

from app.database import get_supabase
from app.main import app
from app.services.auth import create_access_token

client = TestClient(app)
db = get_supabase()

MOCK_STORAGE_URL = "https://example.com/storage/v1/object/public/event-images/test.jpg"


# --- Helpers ---

def _auth_header(user_id: str) -> dict:
    token = create_access_token(user_id, "test@test.com")
    return {"Authorization": f"Bearer {token}"}


def _create_test_user(prefix: str = "cmttest") -> dict:
    unique = uuid.uuid4().hex[:8]
    resp = client.post("/auth/register", json={
        "username": f"{prefix}_{unique}",
        "email": f"{prefix}_{unique}@example.com",
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


def _create_draft_event(host_id: str) -> dict:
    cat_id = _get_category_id()
    start = datetime.now(UTC) + timedelta(days=5)
    end = start + timedelta(hours=2)
    body = {
        "title": f"Draft Event {uuid.uuid4().hex[:6]}",
        "description": "Draft event for testing",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "visibility": "public",
        "is_age_restricted": False,
        "status": "draft",
        "category_ids": [cat_id],
        "locations": [{"name": "Test Venue", "latitude": 41.0, "longitude": 29.0, "is_primary": True, "order_index": 0}],
    }
    resp = client.post("/events", json=body, headers=_auth_header(host_id))
    return resp.json()


# --- Create Comment Tests ---

class TestCreateComment:
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

    def test_create_comment_no_auth(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])

        resp = client.post(
            f"/events/{event['id']}/comments",
            json={"text": "No auth comment"},
        )
        assert resp.status_code == 401

    def test_create_comment_empty_text(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])

        resp = client.post(
            f"/events/{event['id']}/comments",
            json={"text": ""},
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 422

    def test_create_comment_on_draft_event(self):
        host = _create_test_user()
        event = _create_draft_event(host["id"])

        resp = client.post(
            f"/events/{event['id']}/comments",
            json={"text": "Commenting on draft"},
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 400
        assert "Cannot comment" in resp.json()["detail"]

    def test_create_comment_on_cancelled_event(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])
        client.patch(
            f"/events/{event['id']}/status",
            json={"status": "cancelled"},
            headers=_auth_header(host["id"]),
        )

        resp = client.post(
            f"/events/{event['id']}/comments",
            json={"text": "Commenting on cancelled"},
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 400

    def test_create_comment_on_nonexistent_event(self):
        user = _create_test_user()
        fake_id = str(uuid.uuid4())

        resp = client.post(
            f"/events/{fake_id}/comments",
            json={"text": "Ghost event"},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 404

    def test_host_can_comment_own_event(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])

        resp = client.post(
            f"/events/{event['id']}/comments",
            json={"text": "Host commenting"},
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 201


# --- List Comments Tests ---

class TestListComments:
    def test_list_comments_empty(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])

        resp = client.get(f"/events/{event['id']}/comments")
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

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

    def test_list_comments_newest_first(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])

        client.post(
            f"/events/{event['id']}/comments",
            json={"text": "First"},
            headers=_auth_header(host["id"]),
        )
        client.post(
            f"/events/{event['id']}/comments",
            json={"text": "Second"},
            headers=_auth_header(host["id"]),
        )

        resp = client.get(f"/events/{event['id']}/comments")
        items = resp.json()["items"]
        assert items[0]["text"] == "Second"
        assert items[1]["text"] == "First"

    def test_list_comments_pagination(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])

        for i in range(5):
            client.post(
                f"/events/{event['id']}/comments",
                json={"text": f"Comment {i}"},
                headers=_auth_header(host["id"]),
            )

        resp = client.get(f"/events/{event['id']}/comments?page=1&page_size=2")
        data = resp.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["total_pages"] == 3

    def test_list_comments_no_auth_required(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])
        client.post(
            f"/events/{event['id']}/comments",
            json={"text": "Public comment"},
            headers=_auth_header(host["id"]),
        )

        resp = client.get(f"/events/{event['id']}/comments")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_list_comments_nonexistent_event(self):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/events/{fake_id}/comments")
        assert resp.status_code == 404

    def test_list_comments_includes_user_info(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])
        client.post(
            f"/events/{event['id']}/comments",
            json={"text": "Check user info"},
            headers=_auth_header(host["id"]),
        )

        resp = client.get(f"/events/{event['id']}/comments")
        item = resp.json()["items"][0]
        assert "id" in item["user"]
        assert "username" in item["user"]


# --- Delete Comment Tests ---

class TestDeleteComment:
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

    def test_host_can_delete_others_comment(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])
        commenter = _create_test_user()

        resp = client.post(
            f"/events/{event['id']}/comments",
            json={"text": "Host will delete this"},
            headers=_auth_header(commenter["id"]),
        )
        comment_id = resp.json()["id"]

        resp = client.delete(
            f"/events/{event['id']}/comments/{comment_id}",
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 200

    def test_other_user_cannot_delete(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])
        commenter = _create_test_user()
        other = _create_test_user()

        resp = client.post(
            f"/events/{event['id']}/comments",
            json={"text": "Protected comment"},
            headers=_auth_header(commenter["id"]),
        )
        comment_id = resp.json()["id"]

        resp = client.delete(
            f"/events/{event['id']}/comments/{comment_id}",
            headers=_auth_header(other["id"]),
        )
        assert resp.status_code == 403

    def test_delete_nonexistent_comment(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])
        fake_id = str(uuid.uuid4())

        resp = client.delete(
            f"/events/{event['id']}/comments/{fake_id}",
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 404

    def test_delete_no_auth(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])

        resp = client.post(
            f"/events/{event['id']}/comments",
            json={"text": "No auth delete"},
            headers=_auth_header(host["id"]),
        )
        comment_id = resp.json()["id"]

        resp = client.delete(f"/events/{event['id']}/comments/{comment_id}")
        assert resp.status_code == 401

    def test_delete_comment_wrong_event(self):
        host = _create_test_user()
        event1 = _create_published_event(host["id"])
        event2 = _create_published_event(host["id"])

        resp = client.post(
            f"/events/{event1['id']}/comments",
            json={"text": "Event 1 comment"},
            headers=_auth_header(host["id"]),
        )
        comment_id = resp.json()["id"]

        resp = client.delete(
            f"/events/{event2['id']}/comments/{comment_id}",
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 404
