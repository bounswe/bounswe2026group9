"""Tests for the event_recommended notification emitter."""

import io
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image as PILImage

from app.database import get_supabase
from app.main import app
from app.services.auth import create_access_token
from app.services.recommendation_emitter import (
    MAX_RECOMMENDATIONS_PER_DAY,
    emit_event_recommendations,
)
from tests_support import build_test_identity

client = TestClient(app)
db = get_supabase()

MOCK_STORAGE_URL = "https://example.com/storage/v1/object/public/event-images/test.jpg"


# --- Helpers --------------------------------------------------------------

def _auth_header(user_id: str) -> dict:
    token = create_access_token(user_id, "test@test.com")
    return {"Authorization": f"Bearer {token}"}


def _create_user(prefix: str = "rectest") -> dict:
    username, email = build_test_identity(prefix)
    resp = client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "testpass123",
        "date_of_birth": "2000-01-15",
    })
    assert resp.status_code == 201, resp.json()
    return resp.json()["user"]


def _two_category_ids() -> tuple[str, str]:
    result = db.table("categories").select("id").eq("is_predefined", True).limit(2).execute()
    rows = result.data or []
    assert len(rows) >= 2, "need at least two predefined categories for tests"
    return rows[0]["id"], rows[1]["id"]


def _make_image_bytes() -> bytes:
    img = PILImage.new("RGB", (100, 100), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
def _create_published_event(
    host_id: str, category_ids: list[str], mock_upload, *, visibility: str = "public",  # noqa: ARG001
) -> str:
    start = datetime.now(UTC) + timedelta(days=5)
    end = start + timedelta(hours=2)
    body = {
        "title": f"New Event {uuid.uuid4().hex[:6]}",
        "description": "Test event",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "visibility": visibility,
        "is_age_restricted": False,
        "status": "draft",
        "category_ids": category_ids,
        "locations": [{"name": "Venue", "latitude": 41.0, "longitude": 29.0, "is_primary": True, "order_index": 0}],
    }
    create = client.post("/events", json=body, headers=_auth_header(host_id))
    assert create.status_code == 201, create.json()
    event_id = create.json()["id"]
    img = client.post(
        f"/events/{event_id}/images",
        files={"file": ("img.jpg", _make_image_bytes(), "image/jpeg")},
        headers=_auth_header(host_id),
    )
    assert img.status_code == 201
    pub = client.patch(
        f"/events/{event_id}/status",
        json={"status": "published"},
        headers=_auth_header(host_id),
    )
    assert pub.status_code == 200, pub.json()
    return event_id


def _insert_ended_event(host_id: str, category_id: str, *, days_ago: int = 7) -> str:
    """Insert an ended public event directly via DB (bypasses publish validators)."""
    end_dt = datetime.now(UTC) - timedelta(days=days_ago)
    start_dt = end_dt - timedelta(hours=2)
    event = db.table("events").insert({
        "host_id": host_id,
        "title": f"Past Event {uuid.uuid4().hex[:6]}",
        "description": "Historical event",
        "start_datetime": start_dt.isoformat(),
        "end_datetime": end_dt.isoformat(),
        "visibility": "public",
        "is_age_restricted": False,
        "status": "ended",
    }).execute().data[0]
    event_id = event["id"]
    db.table("event_locations").insert({
        "event_id": event_id,
        "name": "Past venue",
        "latitude": 41.0,
        "longitude": 29.0,
        "is_primary": True,
        "order_index": 0,
    }).execute()
    db.table("event_categories").insert({
        "event_id": event_id,
        "category_id": category_id,
    }).execute()
    return event_id


def _add_attendance(user_id: str, event_id: str, att_status: str = "going") -> None:
    db.table("attendances").insert({
        "user_id": user_id,
        "event_id": event_id,
        "status": att_status,
    }).execute()


def _add_bookmark(user_id: str, event_id: str) -> None:
    db.table("bookmarks").insert({"user_id": user_id, "event_id": event_id}).execute()


def _get_recs(user_id: str) -> list[dict]:
    res = db.table("notifications").select(
        "id,event_id,type,message,is_read,created_at",
    ).eq("user_id", user_id).eq("type", "event_recommended").execute()
    return res.data or []


def _cleanup_notifications(user_id: str) -> None:
    db.table("notifications").delete().eq("user_id", user_id).execute()


# --- Tests ----------------------------------------------------------------

class TestRecommendationEmitter:

    def test_match_emits_notification(self):
        cat_a, _ = _two_category_ids()
        host = _create_user()
        listener = _create_user()

        # Listener attended an ended event in cat_a
        past = _insert_ended_event(host["id"], cat_a)
        _add_attendance(listener["id"], past, "going")

        # Host publishes a new event in cat_a → listener should be recommended
        _cleanup_notifications(listener["id"])
        new_event = _create_published_event(host["id"], [cat_a])

        recs = _get_recs(listener["id"])
        assert len(recs) == 1
        assert recs[0]["event_id"] == new_event

    def test_no_history_no_notification(self):
        cat_a, _ = _two_category_ids()
        host = _create_user()
        bystander = _create_user()

        _cleanup_notifications(bystander["id"])
        _create_published_event(host["id"], [cat_a])

        assert _get_recs(bystander["id"]) == []

    def test_host_excluded_from_own_event(self):
        cat_a, _ = _two_category_ids()
        host = _create_user()

        # Host attended a previous event in cat_a
        past = _insert_ended_event(host["id"], cat_a)
        _add_attendance(host["id"], past, "going")

        _cleanup_notifications(host["id"])
        _create_published_event(host["id"], [cat_a])

        assert _get_recs(host["id"]) == []

    def test_private_event_no_recommendations(self):
        cat_a, _ = _two_category_ids()
        host = _create_user()
        listener = _create_user()

        past = _insert_ended_event(host["id"], cat_a)
        _add_attendance(listener["id"], past, "going")

        _cleanup_notifications(listener["id"])
        _create_published_event(host["id"], [cat_a], visibility="private")

        assert _get_recs(listener["id"]) == []

    def test_already_bookmarked_skipped(self):
        cat_a, _ = _two_category_ids()
        host = _create_user()
        listener = _create_user()

        past = _insert_ended_event(host["id"], cat_a)
        _add_attendance(listener["id"], past, "going")

        # Pre-bookmark the new event then call emitter directly
        new_id = _create_published_event(host["id"], [cat_a])
        # The publish above already fired the emitter once; reset and re-run
        _cleanup_notifications(listener["id"])
        _add_bookmark(listener["id"], new_id)

        emit_event_recommendations(db, new_id, host["id"])
        assert _get_recs(listener["id"]) == []

    def test_daily_cap(self):
        cat_a, _ = _two_category_ids()
        host = _create_user()
        listener = _create_user()

        past = _insert_ended_event(host["id"], cat_a)
        _add_attendance(listener["id"], past, "going")

        _cleanup_notifications(listener["id"])
        # Pre-fill cap-1 recommendations (older events still trigger emitter)
        for _ in range(MAX_RECOMMENDATIONS_PER_DAY):
            db.table("notifications").insert({
                "user_id": listener["id"],
                "event_id": None,
                "type": "event_recommended",
                "message": "preexisting",
                "is_read": False,
            }).execute()

        # Now publish a fresh event — listener already at cap, should not gain a 4th
        _create_published_event(host["id"], [cat_a])

        recs = _get_recs(listener["id"])
        assert len(recs) == MAX_RECOMMENDATIONS_PER_DAY

    def test_no_category_overlap(self):
        cat_a, cat_b = _two_category_ids()
        host = _create_user()
        listener = _create_user()

        past = _insert_ended_event(host["id"], cat_a)
        _add_attendance(listener["id"], past, "going")

        _cleanup_notifications(listener["id"])
        # New event uses cat_b, listener attended cat_a → no match
        _create_published_event(host["id"], [cat_b])

        assert _get_recs(listener["id"]) == []

    def test_attendance_on_non_ended_event_does_not_match(self):
        cat_a, _ = _two_category_ids()
        host = _create_user()
        listener = _create_user()

        # Make a published (not yet ended) event in cat_a, listener is going
        past = _create_published_event(host["id"], [cat_a])
        _add_attendance(listener["id"], past, "going")

        _cleanup_notifications(listener["id"])
        # Publish another event in cat_a — listener has only "going" on a still-active event,
        # not an ended one, so no recommendation should fire
        _create_published_event(host["id"], [cat_a])

        assert _get_recs(listener["id"]) == []
