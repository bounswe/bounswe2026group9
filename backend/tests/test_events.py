"""Contract tests for /events endpoints.

Phase 2 of `backend/TESTING_ROADMAP.md` retains one happy-path integration
test per HTTP endpoint as a contract pin against real Supabase. Validation,
authorization, lifecycle, and edge-case coverage moved to the unit suites:

    - tests/test_event_validators_unit.py  (validators + helpers)
    - tests/test_event_crud_unit.py        (create/update/status/delete)
    - tests/test_event_read_unit.py        (detail/list/geojson/similar)

Endpoints covered elsewhere:
    - GET /events, GET /events/geojson, GET /events/{id}/similar → test_discovery.py
    - POST/DELETE /events/{id}/images                            → test_images.py
    - POST /events/{id}/check-in, GET /events/{id}/attendees     → test_checkin.py
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.database import get_supabase
from app.main import app
from app.services.auth import create_access_token
from tests_support import build_test_identity

client = TestClient(app)
db = get_supabase()
MOCK_STORAGE_URL = "https://example.com/storage/v1/object/public/event-images/test.jpg"


# --- Helpers ---

def _auth_header(user_id: str) -> dict:
    token = create_access_token(user_id, "test@test.com")
    return {"Authorization": f"Bearer {token}"}


def _create_test_user(suffix: str = "") -> dict:
    username, email = build_test_identity("eventtest", suffix=suffix)
    user_data = {
        "username": username,
        "email": email,
        "hashed_password": "fakehash",
        "role": "registered",
        "auth_provider": "local",
        "email_verified": True,
        "is_active": True,
    }
    result = db.table("users").insert(user_data).execute()
    return result.data[0]


def _get_category_ids(count: int = 1) -> list[str]:
    result = (
        db.table("categories")
        .select("id")
        .eq("is_predefined", True)
        .limit(count)
        .execute()
    )
    return [row["id"] for row in result.data]


def _valid_event_body(category_ids: list[str] | None = None, **overrides) -> dict:
    body = {
        "title": "Test Event",
        "description": "A test event description",
        "start_datetime": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "end_datetime": (datetime.now(UTC) + timedelta(days=1, hours=2)).isoformat(),
        "visibility": "public",
        "is_age_restricted": False,
        "status": "draft",
        "category_ids": category_ids or [],
        "locations": [
            {
                "name": "Test Venue",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "is_primary": True,
                "order_index": 0,
            }
        ],
    }
    body.update(overrides)
    return body


@patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
def _create_published_event(user_id: str, cat_ids: list[str], mock_upload, **overrides) -> dict:  # noqa: ARG001
    """Create a draft event, upload an image, then publish it."""
    import io

    from PIL import Image as PILImage

    body = _valid_event_body(cat_ids, status="draft", **overrides)
    resp = client.post("/events", json=body, headers=_auth_header(user_id))
    assert resp.status_code == 201, f"Event create failed: {resp.json()}"
    event_id = resp.json()["id"]

    img = PILImage.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    image_resp = client.post(
        f"/events/{event_id}/images",
        files={"file": ("test.jpg", buf, "image/jpeg")},
        headers=_auth_header(user_id),
    )
    assert image_resp.status_code == 201, f"Image upload failed: {image_resp.json()}"

    publish_resp = client.patch(
        f"/events/{event_id}/status",
        json={"status": "published"},
        headers=_auth_header(user_id),
    )
    assert publish_resp.status_code == 200, f"Publish failed: {publish_resp.json()}"
    return publish_resp.json()


def _cleanup_event(event_id: str):
    db.table("event_segments").delete().eq("event_id", event_id).execute()
    db.table("equipment_requirements").delete().eq("event_id", event_id).execute()
    db.table("venue_metadata").delete().eq("event_id", event_id).execute()
    db.table("event_categories").delete().eq("event_id", event_id).execute()
    db.table("event_locations").delete().eq("event_id", event_id).execute()
    db.table("events").delete().eq("id", event_id).execute()


def _cleanup_user(user_id: str):
    db.table("users").delete().eq("id", user_id).execute()


def _two_locations_body(category_ids: list[str], **overrides) -> dict:
    body = _valid_event_body(category_ids, **overrides)
    body["locations"] = [
        {"name": "Stop A", "latitude": 41.0, "longitude": 29.0, "is_primary": True, "order_index": 0},
        {"name": "Stop B", "latitude": 41.1, "longitude": 29.1, "is_primary": False, "order_index": 1},
    ]
    return body


def _seg_payload(*, location_index: int = 0, order_index: int = 0,
                 start_offset_min: int = 30, duration_min: int = 30,
                 description: str | None = None,
                 anchor: datetime | None = None) -> dict:
    if anchor is None:
        anchor = datetime.now(UTC) + timedelta(days=1)
    start = anchor + timedelta(minutes=start_offset_min)
    end = start + timedelta(minutes=duration_min)
    return {
        "location_index": location_index,
        "order_index": order_index,
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "description": description,
    }


# --- Contract tests (one happy path per endpoint) ---

class TestCreateEvent:
    """POST /events"""

    def test_create_event_draft(self):
        user = _create_test_user("draft")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids, status="draft")

        resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        assert resp.status_code == 201

        data = resp.json()
        assert data["title"] == "Test Event"
        assert data["status"] == "draft"
        assert data["host_id"] == user["id"]
        assert len(data["locations"]) == 1
        assert len(data["categories"]) == 1

        _cleanup_event(data["id"])
        _cleanup_user(user["id"])


class TestGetEvent:
    """GET /events/{id}"""

    def test_get_event_full_detail(self):
        user = _create_test_user("getfull")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)

        resp = client.get(f"/events/{event['id']}", headers=_auth_header(user["id"]))
        assert resp.status_code == 200

        data = resp.json()
        assert data["id"] == event["id"]
        assert data["title"] == "Test Event"
        assert "locations" in data
        assert "categories" in data
        assert "description" in data

        _cleanup_event(event["id"])
        _cleanup_user(user["id"])


class TestUpdateEvent:
    """PUT /events/{id}"""

    def test_update_title(self):
        user = _create_test_user("uptitle")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids, status="draft")
        event_id = client.post(
            "/events", json=body, headers=_auth_header(user["id"]),
        ).json()["id"]

        resp = client.put(
            f"/events/{event_id}",
            json={"title": "Updated Title"},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

        _cleanup_event(event_id)
        _cleanup_user(user["id"])


class TestChangeEventStatus:
    """PATCH /events/{id}/status"""

    def test_published_to_cancelled(self):
        user = _create_test_user("p2c")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)

        resp = client.patch(
            f"/events/{event['id']}/status",
            json={"status": "cancelled"},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

        _cleanup_event(event["id"])
        _cleanup_user(user["id"])


class TestDeleteEvent:
    """DELETE /events/{id}"""

    def test_delete_cancelled_event(self):
        user = _create_test_user("delcancel")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)

        client.patch(
            f"/events/{event['id']}/status",
            json={"status": "cancelled"},
            headers=_auth_header(user["id"]),
        )

        resp = client.delete(f"/events/{event['id']}", headers=_auth_header(user["id"]))
        assert resp.status_code == 200

        # Verify the row is gone
        get_resp = client.get(f"/events/{event['id']}")
        assert get_resp.status_code == 404

        _cleanup_user(user["id"])


class TestEventSegments:
    """POST /events with segments — itinerary persistence contract."""

    def test_create_event_with_segments(self):
        user = _create_test_user("segcreate")
        cat_ids = _get_category_ids(1)
        body = _two_locations_body(cat_ids, segments=[
            _seg_payload(location_index=0, order_index=0,
                         start_offset_min=30, duration_min=30, description="Welcome"),
            _seg_payload(location_index=1, order_index=1,
                         start_offset_min=60, duration_min=30, description="Move to Stop B"),
        ])

        resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        assert resp.status_code == 201, resp.json()

        data = resp.json()
        assert len(data["segments"]) == 2
        assert data["segments"][0]["order_index"] == 0
        assert data["segments"][1]["order_index"] == 1
        location_ids = {loc["id"] for loc in data["locations"]}
        for seg in data["segments"]:
            assert seg["location_id"] in location_ids

        _cleanup_event(data["id"])
        _cleanup_user(user["id"])
