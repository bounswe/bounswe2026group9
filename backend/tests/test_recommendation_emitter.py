"""Contract test for the recommendation emitter end-to-end SQL path.

Phase 2 retains a single integration scenario that exercises the SQL-heavy
internal helpers (_find_candidates, _drop_users_already_engaged,
_drop_users_already_notified, _drop_users_over_daily_cap) — those still
hit Supabase directly until the next DI pass. The public surface +
early-return / orchestration branches are unit-tested in
tests/test_recommendation_emitter_unit.py.
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
def _create_published_event(host_id: str, category_ids: list[str], mock_upload) -> str:  # noqa: ARG001
    start = datetime.now(UTC) + timedelta(days=5)
    end = start + timedelta(hours=2)
    body = {
        "title": f"New Event {uuid.uuid4().hex[:6]}",
        "description": "Test event",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "visibility": "public",
        "is_age_restricted": False,
        "status": "draft",
        "category_ids": category_ids,
        "locations": [{"name": "Venue", "latitude": 41.0, "longitude": 29.0, "is_primary": True, "order_index": 0}],
    }
    create = client.post("/events", json=body, headers=_auth_header(host_id))
    event_id = create.json()["id"]
    client.post(
        f"/events/{event_id}/images",
        files={"file": ("img.jpg", _make_image_bytes(), "image/jpeg")},
        headers=_auth_header(host_id),
    )
    client.patch(
        f"/events/{event_id}/status",
        json={"status": "published"},
        headers=_auth_header(host_id),
    )
    return event_id


def _insert_ended_event(host_id: str, category_id: str) -> str:
    end_dt = datetime.now(UTC) - timedelta(days=7)
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
        "event_id": event_id, "name": "Past venue",
        "latitude": 41.0, "longitude": 29.0,
        "is_primary": True, "order_index": 0,
    }).execute()
    db.table("event_categories").insert({
        "event_id": event_id, "category_id": category_id,
    }).execute()
    return event_id


def _add_attendance(user_id: str, event_id: str, att_status: str = "going") -> None:
    db.table("attendances").insert({
        "user_id": user_id, "event_id": event_id, "status": att_status,
    }).execute()


def _get_recs(user_id: str) -> list[dict]:
    return db.table("notifications").select(
        "id,event_id,type,message",
    ).eq("user_id", user_id).eq("type", "event_recommended").execute().data or []


# --- Contract test ---


class TestRecommendationEmitter:
    def test_match_emits_notification(self):
        """End-to-end: matching past attendance + new public publish → recommendation."""
        cat_a, _ = _two_category_ids()
        host = _create_user()
        listener = _create_user()

        # Listener attended an ended event in cat_a → matches new cat_a event.
        past = _insert_ended_event(host["id"], cat_a)
        _add_attendance(listener["id"], past, "going")

        new_event = _create_published_event(host["id"], [cat_a])

        recs = _get_recs(listener["id"])
        assert len(recs) == 1
        assert recs[0]["event_id"] == new_event
