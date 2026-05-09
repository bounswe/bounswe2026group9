"""Contract tests for QR check-in endpoints.

Phase 2 retains one happy-path integration test per HTTP endpoint. Branch
coverage (token rotation, lifecycle gates, tampered payloads, manual
check-in, attendee-list authz) lives in tests/test_attendance_unit.py.
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


def _auth(user_id: str) -> dict:
    token = create_access_token(user_id, "test@example.com")
    return {"Authorization": f"Bearer {token}"}


def _register(prefix: str = "qrtest") -> dict:
    username, email = build_test_identity(prefix)
    resp = client.post("/auth/register", json={
        "username": username, "email": email,
        "password": "testpass123", "date_of_birth": "2000-01-15",
    })
    assert resp.status_code == 201, resp.json()
    return resp.json()["user"]


def _get_category_id() -> str:
    return db.table("categories").select("id").eq("is_predefined", True).limit(1).execute().data[0]["id"]


def _make_image() -> bytes:
    img = PILImage.new("RGB", (100, 100), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
def _create_published_event(host_id: str, mock_upload) -> str:  # noqa: ARG001
    cat_id = _get_category_id()
    start = datetime.now(UTC) + timedelta(days=5)
    end = start + timedelta(hours=2)
    body = {
        "title": f"QR Test Event {uuid.uuid4().hex[:6]}",
        "description": "Check-in test event",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "visibility": "public", "status": "draft", "is_age_restricted": False,
        "category_ids": [cat_id],
        "locations": [{"name": "Venue", "latitude": 41.0, "longitude": 29.0}],
    }
    create_resp = client.post("/events", headers=_auth(host_id), json=body)
    event_id = create_resp.json()["id"]
    client.post(
        f"/events/{event_id}/images",
        headers=_auth(host_id),
        files={"file": ("test.jpg", io.BytesIO(_make_image()), "image/jpeg")},
    )
    client.patch(
        f"/events/{event_id}/status",
        headers=_auth(host_id),
        json={"status": "published"},
    )
    return event_id


def _go(attendee_id: str, event_id: str) -> None:
    resp = client.post(
        f"/events/{event_id}/attendance",
        headers=_auth(attendee_id),
        json={"status": "going"},
    )
    assert resp.status_code == 200, resp.json()


# --- Contract tests (one happy path per endpoint) ---


class TestGetMyQr:
    """GET /attendances/me/{event_id}/qr"""

    def test_qr_returned_after_going(self):
        host = _register()
        attendee = _register()
        event_id = _create_published_event(host["id"])
        _go(attendee["id"], event_id)

        resp = client.get(f"/attendances/me/{event_id}/qr", headers=_auth(attendee["id"]))
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert len(data["token"]) > 10


class TestCheckIn:
    """POST /events/{event_id}/check-in — host-driven scan + manual paths."""

    def test_valid_qr_scan_marks_checked_in(self):
        host = _register()
        attendee = _register()
        event_id = _create_published_event(host["id"])
        _go(attendee["id"], event_id)

        qr_token = client.get(
            f"/attendances/me/{event_id}/qr", headers=_auth(attendee["id"]),
        ).json()["token"]

        resp = client.post(
            f"/events/{event_id}/check-in",
            headers=_auth(host["id"]),
            json={"token": qr_token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == attendee["id"]
        assert data["checked_in_at"] is not None

        # Idempotency contract: second scan with same token rejects.
        again = client.post(
            f"/events/{event_id}/check-in",
            headers=_auth(host["id"]),
            json={"token": qr_token},
        )
        assert again.status_code == 409


class TestAttendeeList:
    """GET /events/{event_id}/attendees"""

    def test_host_can_list_attendees(self):
        host = _register()
        a1 = _register()
        a2 = _register()
        event_id = _create_published_event(host["id"])
        _go(a1["id"], event_id)
        _go(a2["id"], event_id)

        resp = client.get(f"/events/{event_id}/attendees", headers=_auth(host["id"]))
        assert resp.status_code == 200
        ids = {row["user_id"] for row in resp.json()}
        assert a1["id"] in ids
        assert a2["id"] in ids
        assert all(row["checked_in_at"] is None for row in resp.json())
