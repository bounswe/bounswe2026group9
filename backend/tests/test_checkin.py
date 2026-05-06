"""Integration tests for QR check-in — issue #231.

Coverage:
  - QR issued on Going (200)
  - QR returns 404 when caller is not going
  - QR backfill: attendance without a token gets one on first GET
  - host-only check-in: 403 for non-host
  - valid QR scan → 200 + checked_in_at set
  - duplicate scan → 409
  - tampered payload → 400
  - wrong-event payload → 400
  - missing both token and user_id → 400
  - manual check-in by user_id → 200
  - attendee list (host-only): 200 + 403 for non-host
  - un-Going removes the token (QR becomes invalid)
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


# ── Helpers ────────────────────────────────────────────────────────────────────

def _auth(user_id: str) -> dict:
    token = create_access_token(user_id, "test@example.com")
    return {"Authorization": f"Bearer {token}"}


def _register(prefix: str = "qrtest") -> dict:
    username, email = build_test_identity(prefix)
    resp = client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": "testpass123",
        "date_of_birth": "2000-01-15",
    })
    assert resp.status_code == 201, resp.json()
    return resp.json()["user"]


def _get_category_id() -> str:
    result = db.table("categories").select("id").eq("is_predefined", True).limit(1).execute()
    return result.data[0]["id"]


def _make_image() -> bytes:
    img = PILImage.new("RGB", (100, 100), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
def _create_published_event(host_id: str, mock_upload, *, days: int = 5) -> str:  # noqa: ARG001
    """Create and publish an event; return its id."""
    cat_id = _get_category_id()
    start = datetime.now(UTC) + timedelta(days=days)
    end = start + timedelta(hours=2)
    body = {
        "title": f"QR Test Event {uuid.uuid4().hex[:6]}",
        "description": "Check-in test event",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "visibility": "public",
        "status": "draft",
        "is_age_restricted": False,
        "category_ids": [cat_id],
        "locations": [{"name": "Venue", "latitude": 41.0, "longitude": 29.0}],
    }
    create_resp = client.post("/events", headers=_auth(host_id), json=body)
    assert create_resp.status_code == 201, create_resp.json()
    event_id = create_resp.json()["id"]

    img_bytes = _make_image()
    client.post(
        f"/events/{event_id}/images",
        headers=_auth(host_id),
        files={"file": ("test.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )

    pub = client.patch(
        f"/events/{event_id}/status",
        headers=_auth(host_id),
        json={"status": "published"},
    )
    assert pub.status_code == 200, pub.json()
    return event_id


def _go(attendee_id: str, event_id: str) -> None:
    resp = client.post(
        f"/events/{event_id}/attendance",
        headers=_auth(attendee_id),
        json={"status": "going"},
    )
    assert resp.status_code == 200, resp.json()


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestGetMyQr:
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

    def test_qr_404_when_not_going(self):
        host = _register()
        attendee = _register()
        event_id = _create_published_event(host["id"])

        resp = client.get(f"/attendances/me/{event_id}/qr", headers=_auth(attendee["id"]))
        assert resp.status_code == 404

    def test_qr_401_without_auth(self):
        host = _register()
        event_id = _create_published_event(host["id"])

        resp = client.get(f"/attendances/me/{event_id}/qr")
        assert resp.status_code == 401

    def test_qr_backfill_for_tokenless_attendance(self):
        """Attendances that pre-date the QR migration get a token on first GET."""
        host = _register()
        attendee = _register()
        event_id = _create_published_event(host["id"])
        _go(attendee["id"], event_id)

        # Directly null-out the token to simulate a pre-migration row.
        db.table("attendances").update({"check_in_token": None}).eq(
            "user_id", attendee["id"]
        ).eq("event_id", event_id).execute()

        resp = client.get(f"/attendances/me/{event_id}/qr", headers=_auth(attendee["id"]))
        assert resp.status_code == 200
        assert resp.json()["token"]


class TestCheckIn:
    def test_valid_qr_scan(self):
        host = _register()
        attendee = _register()
        event_id = _create_published_event(host["id"])
        _go(attendee["id"], event_id)

        qr_token = client.get(
            f"/attendances/me/{event_id}/qr", headers=_auth(attendee["id"])
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

    def test_duplicate_scan_returns_409(self):
        host = _register()
        attendee = _register()
        event_id = _create_published_event(host["id"])
        _go(attendee["id"], event_id)

        qr_token = client.get(
            f"/attendances/me/{event_id}/qr", headers=_auth(attendee["id"])
        ).json()["token"]

        client.post(
            f"/events/{event_id}/check-in",
            headers=_auth(host["id"]),
            json={"token": qr_token},
        )
        second = client.post(
            f"/events/{event_id}/check-in",
            headers=_auth(host["id"]),
            json={"token": qr_token},
        )
        assert second.status_code == 409

    def test_tampered_payload_returns_400(self):
        host = _register()
        attendee = _register()
        event_id = _create_published_event(host["id"])
        _go(attendee["id"], event_id)

        qr_token = client.get(
            f"/attendances/me/{event_id}/qr", headers=_auth(attendee["id"])
        ).json()["token"]

        tampered = qr_token[:-4] + "xxxx"
        resp = client.post(
            f"/events/{event_id}/check-in",
            headers=_auth(host["id"]),
            json={"token": tampered},
        )
        assert resp.status_code == 400

    def test_wrong_event_payload_returns_400(self):
        host = _register()
        attendee = _register()
        event_a = _create_published_event(host["id"])
        event_b = _create_published_event(host["id"])
        _go(attendee["id"], event_a)

        token_for_a = client.get(
            f"/attendances/me/{event_a}/qr", headers=_auth(attendee["id"])
        ).json()["token"]

        # Submit event_a's token against event_b.
        resp = client.post(
            f"/events/{event_b}/check-in",
            headers=_auth(host["id"]),
            json={"token": token_for_a},
        )
        assert resp.status_code == 400

    def test_non_host_returns_403(self):
        host = _register()
        attendee = _register()
        other = _register()
        event_id = _create_published_event(host["id"])
        _go(attendee["id"], event_id)

        qr_token = client.get(
            f"/attendances/me/{event_id}/qr", headers=_auth(attendee["id"])
        ).json()["token"]

        resp = client.post(
            f"/events/{event_id}/check-in",
            headers=_auth(other["id"]),
            json={"token": qr_token},
        )
        assert resp.status_code == 403

    def test_manual_checkin_by_user_id(self):
        host = _register()
        attendee = _register()
        event_id = _create_published_event(host["id"])
        _go(attendee["id"], event_id)

        resp = client.post(
            f"/events/{event_id}/check-in",
            headers=_auth(host["id"]),
            json={"user_id": attendee["id"]},
        )
        assert resp.status_code == 200
        assert resp.json()["user_id"] == attendee["id"]

    def test_missing_both_fields_returns_400(self):
        host = _register()
        event_id = _create_published_event(host["id"])

        resp = client.post(
            f"/events/{event_id}/check-in",
            headers=_auth(host["id"]),
            json={},
        )
        assert resp.status_code == 400

    def test_not_going_returns_404(self):
        host = _register()
        other = _register()
        event_id = _create_published_event(host["id"])

        # other never RSVP'd
        resp = client.post(
            f"/events/{event_id}/check-in",
            headers=_auth(host["id"]),
            json={"user_id": other["id"]},
        )
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self):
        host = _register()
        event_id = _create_published_event(host["id"])
        resp = client.post(f"/events/{event_id}/check-in", json={"user_id": host["id"]})
        assert resp.status_code == 401


class TestUnGoingInvalidatesToken:
    def test_qr_unavailable_after_un_going(self):
        host = _register()
        attendee = _register()
        event_id = _create_published_event(host["id"])
        _go(attendee["id"], event_id)

        qr_token = client.get(
            f"/attendances/me/{event_id}/qr", headers=_auth(attendee["id"])
        ).json()["token"]

        # Un-Go
        client.delete(f"/events/{event_id}/attendance", headers=_auth(attendee["id"]))

        # The old token should now fail check-in (attendance row is gone)
        resp = client.post(
            f"/events/{event_id}/check-in",
            headers=_auth(host["id"]),
            json={"token": qr_token},
        )
        assert resp.status_code == 404

        # And /qr should return 404 too
        qr_resp = client.get(
            f"/attendances/me/{event_id}/qr", headers=_auth(attendee["id"])
        )
        assert qr_resp.status_code == 404


class TestEventLifecycleGuards:
    """Lock down the `event["status"] not in ("published","updated")` guard
    in `services/attendance.check_in`. Without these tests the guard could
    silently regress and let scans through against cancelled/ended events.
    """

    def test_check_in_blocks_cancelled_event(self):
        host = _register()
        attendee = _register()
        event_id = _create_published_event(host["id"])
        _go(attendee["id"], event_id)
        qr_token = client.get(
            f"/attendances/me/{event_id}/qr", headers=_auth(attendee["id"])
        ).json()["token"]

        # Host cancels the event after RSVPs are in.
        cancel = client.patch(
            f"/events/{event_id}/status",
            headers=_auth(host["id"]),
            json={"status": "cancelled"},
        )
        assert cancel.status_code == 200

        resp = client.post(
            f"/events/{event_id}/check-in",
            headers=_auth(host["id"]),
            json={"token": qr_token},
        )
        assert resp.status_code == 400, resp.json()
        assert "active" in resp.json()["detail"].lower()

    def test_check_in_blocks_ended_event(self):
        host = _register()
        attendee = _register()
        event_id = _create_published_event(host["id"])
        _go(attendee["id"], event_id)
        qr_token = client.get(
            f"/attendances/me/{event_id}/qr", headers=_auth(attendee["id"])
        ).json()["token"]

        # Mark the event as ended directly via the status endpoint to avoid
        # waiting on the pg_cron auto_end job.
        end = client.patch(
            f"/events/{event_id}/status",
            headers=_auth(host["id"]),
            json={"status": "ended"},
        )
        assert end.status_code == 200

        resp = client.post(
            f"/events/{event_id}/check-in",
            headers=_auth(host["id"]),
            json={"token": qr_token},
        )
        assert resp.status_code == 400, resp.json()
        assert "active" in resp.json()["detail"].lower()


class TestReGoingTokenRotation:
    """When a user un-Goes and Goes again, a fresh token is issued and the
    previous token must not validate. The first half is already covered by
    `TestUnGoingInvalidatesToken`; this pins the rotation half explicitly.
    """

    def test_re_going_invalidates_old_token(self):
        host = _register()
        attendee = _register()
        event_id = _create_published_event(host["id"])

        # First Going + token snapshot.
        _go(attendee["id"], event_id)
        old_token = client.get(
            f"/attendances/me/{event_id}/qr", headers=_auth(attendee["id"])
        ).json()["token"]

        # Un-Go → row deleted → token invalidated.
        client.delete(f"/events/{event_id}/attendance", headers=_auth(attendee["id"]))

        # Re-Go → new attendance row + new token.
        _go(attendee["id"], event_id)
        new_token = client.get(
            f"/attendances/me/{event_id}/qr", headers=_auth(attendee["id"])
        ).json()["token"]
        assert new_token != old_token, "re-Going must rotate the token"

        # Old token resolves to no row in the new attendance, so it 404s.
        old_scan = client.post(
            f"/events/{event_id}/check-in",
            headers=_auth(host["id"]),
            json={"token": old_token},
        )
        assert old_scan.status_code == 404, old_scan.json()

        # New token works.
        new_scan = client.post(
            f"/events/{event_id}/check-in",
            headers=_auth(host["id"]),
            json={"token": new_token},
        )
        assert new_scan.status_code == 200, new_scan.json()


class TestAttendeeList:
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
        # Before any check-in all checked_in_at are null
        assert all(row["checked_in_at"] is None for row in resp.json())

    def test_host_list_shows_checkin_timestamp(self):
        host = _register()
        attendee = _register()
        event_id = _create_published_event(host["id"])
        _go(attendee["id"], event_id)

        qr_token = client.get(
            f"/attendances/me/{event_id}/qr", headers=_auth(attendee["id"])
        ).json()["token"]
        client.post(
            f"/events/{event_id}/check-in",
            headers=_auth(host["id"]),
            json={"token": qr_token},
        )

        resp = client.get(f"/events/{event_id}/attendees", headers=_auth(host["id"]))
        row = next(r for r in resp.json() if r["user_id"] == attendee["id"])
        assert row["checked_in_at"] is not None

    def test_non_host_cannot_list_attendees(self):
        host = _register()
        other = _register()
        event_id = _create_published_event(host["id"])

        resp = client.get(f"/events/{event_id}/attendees", headers=_auth(other["id"]))
        assert resp.status_code == 403

    def test_unauthenticated_cannot_list_attendees(self):
        host = _register()
        event_id = _create_published_event(host["id"])
        resp = client.get(f"/events/{event_id}/attendees")
        assert resp.status_code == 401
