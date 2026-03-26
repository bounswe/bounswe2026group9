"""Tests for notification emission on event update and cancellation."""

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


def _create_test_user(prefix: str = "emittest") -> dict:
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
def _create_published_event(host_id: str, mock_upload, *, visibility: str = "public") -> dict:  # noqa: ARG001
    cat_id = _get_category_id()
    start = datetime.now(UTC) + timedelta(days=5)
    end = start + timedelta(hours=2)
    body = {
        "title": f"Emit Test Event {uuid.uuid4().hex[:6]}",
        "description": "Event for emitter testing",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "visibility": visibility,
        "is_age_restricted": False,
        "status": "draft",
        "category_ids": [cat_id],
        "locations": [{"name": "Test Venue", "latitude": 41.0, "longitude": 29.0, "is_primary": True, "order_index": 0}],
    }
    create_resp = client.post("/events", json=body, headers=_auth_header(host_id))
    assert create_resp.status_code == 201, f"Event create failed: {create_resp.json()}"
    event_id = create_resp.json()["id"]
    img_resp = client.post(
        f"/events/{event_id}/images",
        files={"file": ("test.jpg", _make_image_bytes(), "image/jpeg")},
        headers=_auth_header(host_id),
    )
    assert img_resp.status_code == 201, f"Image upload failed: {img_resp.json()}"
    pub_resp = client.patch(
        f"/events/{event_id}/status",
        json={"status": "published"},
        headers=_auth_header(host_id),
    )
    assert pub_resp.status_code == 200, f"Publish failed: {pub_resp.json()}"
    return create_resp.json()


def _add_bookmark(user_id: str, event_id: str) -> None:
    """Insert bookmark directly into DB."""
    db.table("bookmarks").insert({
        "user_id": user_id,
        "event_id": event_id,
    }).execute()


def _add_attendance(user_id: str, event_id: str, att_status: str = "going") -> None:
    """Insert attendance directly into DB."""
    db.table("attendances").insert({
        "user_id": user_id,
        "event_id": event_id,
        "status": att_status,
    }).execute()


def _get_notifications(user_id: str) -> list[dict]:
    """Get all notifications for a user."""
    resp = client.get("/notifications", headers=_auth_header(user_id))
    assert resp.status_code == 200
    return resp.json()["items"]


def _cleanup_notifications(user_id: str) -> None:
    db.table("notifications").delete().eq("user_id", user_id).execute()


# --- Update Notification Tests ---

class TestUpdateNotification:
    def test_update_notifies_going_user(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_published_event(host["id"])

        _add_attendance(user["id"], event["id"], "going")

        client.put(
            f"/events/{event['id']}",
            json={"title": "Updated Title"},
            headers=_auth_header(host["id"]),
        )

        notifications = _get_notifications(user["id"])
        assert len(notifications) >= 1
        assert any(n["type"] == "event_updated" for n in notifications)

        _cleanup_notifications(user["id"])

    def test_update_notifies_interested_user(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_published_event(host["id"])

        _add_attendance(user["id"], event["id"], "interested")

        client.put(
            f"/events/{event['id']}",
            json={"description": "Updated description"},
            headers=_auth_header(host["id"]),
        )

        notifications = _get_notifications(user["id"])
        assert any(n["type"] == "event_updated" for n in notifications)

        _cleanup_notifications(user["id"])

    def test_update_notifies_bookmarked_user(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_published_event(host["id"])

        _add_bookmark(user["id"], event["id"])

        client.put(
            f"/events/{event['id']}",
            json={"title": "Bookmark update test"},
            headers=_auth_header(host["id"]),
        )

        notifications = _get_notifications(user["id"])
        assert any(n["type"] == "event_updated" for n in notifications)

        _cleanup_notifications(user["id"])

    def test_update_does_not_notify_host(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])

        # Host bookmarks own event (unusual but possible)
        _add_bookmark(host["id"], event["id"])

        client.put(
            f"/events/{event['id']}",
            json={"title": "Host self-update"},
            headers=_auth_header(host["id"]),
        )

        notifications = _get_notifications(host["id"])
        update_notifs = [n for n in notifications if n["type"] == "event_updated"]
        assert len(update_notifs) == 0

        _cleanup_notifications(host["id"])

    def test_update_no_attendees_no_error(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])

        # No bookmarks, no attendees — should not error
        resp = client.put(
            f"/events/{event['id']}",
            json={"title": "No audience update"},
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 200

    def test_no_duplicate_notification(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_published_event(host["id"])

        # User both bookmarked AND going
        _add_bookmark(user["id"], event["id"])
        _add_attendance(user["id"], event["id"], "going")

        client.put(
            f"/events/{event['id']}",
            json={"title": "Dedup test"},
            headers=_auth_header(host["id"]),
        )

        notifications = _get_notifications(user["id"])
        update_notifs = [n for n in notifications if n["type"] == "event_updated"]
        assert len(update_notifs) == 1  # Only one, not two

        _cleanup_notifications(user["id"])


# --- Cancellation Notification Tests ---

class TestCancelNotification:
    def test_cancel_notifies_going_user(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_published_event(host["id"])

        _add_attendance(user["id"], event["id"], "going")

        client.patch(
            f"/events/{event['id']}/status",
            json={"status": "cancelled"},
            headers=_auth_header(host["id"]),
        )

        notifications = _get_notifications(user["id"])
        assert any(n["type"] == "event_cancelled" for n in notifications)

        _cleanup_notifications(user["id"])

    def test_cancel_notifies_bookmarked_user(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_published_event(host["id"])

        _add_bookmark(user["id"], event["id"])

        client.patch(
            f"/events/{event['id']}/status",
            json={"status": "cancelled"},
            headers=_auth_header(host["id"]),
        )

        notifications = _get_notifications(user["id"])
        assert any(n["type"] == "event_cancelled" for n in notifications)

        _cleanup_notifications(user["id"])

    def test_cancel_does_not_notify_host(self):
        host = _create_test_user()
        event = _create_published_event(host["id"])

        _add_attendance(host["id"], event["id"], "going")

        client.patch(
            f"/events/{event['id']}/status",
            json={"status": "cancelled"},
            headers=_auth_header(host["id"]),
        )

        notifications = _get_notifications(host["id"])
        cancel_notifs = [n for n in notifications if n["type"] == "event_cancelled"]
        assert len(cancel_notifs) == 0

        _cleanup_notifications(host["id"])

    def test_end_does_not_notify(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_published_event(host["id"])

        _add_attendance(user["id"], event["id"], "going")

        client.patch(
            f"/events/{event['id']}/status",
            json={"status": "ended"},
            headers=_auth_header(host["id"]),
        )

        notifications = _get_notifications(user["id"])
        # ended should NOT trigger notification
        end_notifs = [n for n in notifications if n["type"] == "event_cancelled"]
        assert len(end_notifs) == 0

        _cleanup_notifications(user["id"])
