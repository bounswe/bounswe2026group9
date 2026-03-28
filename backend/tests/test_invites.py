"""Tests for invite & access request endpoints."""

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


def _create_test_user(prefix: str = "invtest") -> dict:
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
def _create_private_published_event(host_id: str, mock_upload) -> dict:  # noqa: ARG001
    cat_id = _get_category_id()
    start = datetime.now(UTC) + timedelta(days=5)
    end = start + timedelta(hours=2)
    body = {
        "title": f"Private Event {uuid.uuid4().hex[:6]}",
        "description": "Private event for invite testing",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "visibility": "private",
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


@patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
def _create_public_published_event(host_id: str, mock_upload) -> dict:  # noqa: ARG001
    cat_id = _get_category_id()
    start = datetime.now(UTC) + timedelta(days=5)
    end = start + timedelta(hours=2)
    body = {
        "title": f"Public Event {uuid.uuid4().hex[:6]}",
        "description": "Public event",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "visibility": "public",
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


# --- Create Invite Tests ---

class TestCreateInvite:
    def test_create_invite_success(self):
        host = _create_test_user()
        event = _create_private_published_event(host["id"])

        resp = client.post(
            f"/events/{event['id']}/invites",
            json={},
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["event_id"] == event["id"]
        assert "token" in data
        assert "invite_url" in data
        assert data["use_count"] == 0

    def test_create_invite_with_options(self):
        host = _create_test_user()
        event = _create_private_published_event(host["id"])

        resp = client.post(
            f"/events/{event['id']}/invites",
            json={"max_uses": 5, "expires_in_hours": 48},
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["max_uses"] == 5
        assert data["expires_at"] is not None

    def test_create_invite_non_host_forbidden(self):
        host = _create_test_user()
        other = _create_test_user()
        event = _create_private_published_event(host["id"])

        resp = client.post(
            f"/events/{event['id']}/invites",
            json={},
            headers=_auth_header(other["id"]),
        )
        assert resp.status_code == 403

    def test_create_invite_public_event_rejected(self):
        host = _create_test_user()
        event = _create_public_published_event(host["id"])

        resp = client.post(
            f"/events/{event['id']}/invites",
            json={},
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 400
        assert "private" in resp.json()["detail"].lower()

    def test_create_invite_no_auth(self):
        host = _create_test_user()
        event = _create_private_published_event(host["id"])

        resp = client.post(f"/events/{event['id']}/invites", json={})
        assert resp.status_code == 401


# --- Accept Invite Tests ---

class TestAcceptInvite:
    def test_accept_invite_success(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_private_published_event(host["id"])

        # Create invite
        invite_resp = client.post(
            f"/events/{event['id']}/invites",
            json={},
            headers=_auth_header(host["id"]),
        )
        token = invite_resp.json()["token"]

        # Accept invite
        resp = client.post(
            f"/events/{event['id']}/invites/{token}/accept",
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 200
        assert "granted" in resp.json()["message"].lower()

    def test_accept_invite_grants_event_access(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_private_published_event(host["id"])

        # Before invite: limited preview
        resp = client.get(f"/events/{event['id']}", headers=_auth_header(user["id"]))
        assert "description" not in resp.json() or resp.json().get("description") is None

        # Create and accept invite
        invite_resp = client.post(
            f"/events/{event['id']}/invites",
            json={},
            headers=_auth_header(host["id"]),
        )
        token = invite_resp.json()["token"]
        client.post(
            f"/events/{event['id']}/invites/{token}/accept",
            headers=_auth_header(user["id"]),
        )

        # After invite: full detail
        resp = client.get(f"/events/{event['id']}", headers=_auth_header(user["id"]))
        assert resp.json().get("description") is not None

    def test_accept_invite_invalid_token(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_private_published_event(host["id"])

        resp = client.post(
            f"/events/{event['id']}/invites/fake_token_123/accept",
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 404

    def test_accept_invite_already_granted(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_private_published_event(host["id"])

        invite_resp = client.post(
            f"/events/{event['id']}/invites",
            json={},
            headers=_auth_header(host["id"]),
        )
        token = invite_resp.json()["token"]

        # Accept once
        client.post(
            f"/events/{event['id']}/invites/{token}/accept",
            headers=_auth_header(user["id"]),
        )

        # Accept again
        resp = client.post(
            f"/events/{event['id']}/invites/{token}/accept",
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 400
        assert "already" in resp.json()["detail"].lower()

    def test_accept_invite_host_rejected(self):
        host = _create_test_user()
        event = _create_private_published_event(host["id"])

        invite_resp = client.post(
            f"/events/{event['id']}/invites",
            json={},
            headers=_auth_header(host["id"]),
        )
        token = invite_resp.json()["token"]

        resp = client.post(
            f"/events/{event['id']}/invites/{token}/accept",
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 400
        assert "host" in resp.json()["detail"].lower()

    def test_accept_invite_max_uses_reached(self):
        host = _create_test_user()
        event = _create_private_published_event(host["id"])

        # Create invite with max_uses=1
        invite_resp = client.post(
            f"/events/{event['id']}/invites",
            json={"max_uses": 1},
            headers=_auth_header(host["id"]),
        )
        token = invite_resp.json()["token"]

        # First user accepts
        user1 = _create_test_user()
        client.post(
            f"/events/{event['id']}/invites/{token}/accept",
            headers=_auth_header(user1["id"]),
        )

        # Second user tries
        user2 = _create_test_user()
        resp = client.post(
            f"/events/{event['id']}/invites/{token}/accept",
            headers=_auth_header(user2["id"]),
        )
        assert resp.status_code == 400
        assert "maximum" in resp.json()["detail"].lower()


# --- List Invites Tests ---

class TestListInvites:
    def test_list_invites_as_host(self):
        host = _create_test_user()
        event = _create_private_published_event(host["id"])

        client.post(f"/events/{event['id']}/invites", json={}, headers=_auth_header(host["id"]))
        client.post(f"/events/{event['id']}/invites", json={}, headers=_auth_header(host["id"]))

        resp = client.get(f"/events/{event['id']}/invites", headers=_auth_header(host["id"]))
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 2

    def test_list_invites_non_host_forbidden(self):
        host = _create_test_user()
        other = _create_test_user()
        event = _create_private_published_event(host["id"])

        resp = client.get(f"/events/{event['id']}/invites", headers=_auth_header(other["id"]))
        assert resp.status_code == 403


# --- Access Request Tests ---

class TestAccessRequests:
    def test_create_access_request_success(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_private_published_event(host["id"])

        resp = client.post(
            f"/events/{event['id']}/access-requests",
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["user_id"] == user["id"]

    def test_create_access_request_notifies_host(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_private_published_event(host["id"])

        resp = client.post(
            f"/events/{event['id']}/access-requests",
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 201

        notif_resp = client.get("/notifications", headers=_auth_header(host["id"]))
        assert notif_resp.status_code == 200
        notifications = notif_resp.json()["items"]
        assert any(
            n["type"] == "access_request"
            and n["event_id"] == event["id"]
            and user["username"] in n["message"]
            and event["title"] in n["message"]
            for n in notifications
        )

    def test_create_access_request_duplicate_blocked(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_private_published_event(host["id"])

        client.post(f"/events/{event['id']}/access-requests", headers=_auth_header(user["id"]))
        resp = client.post(f"/events/{event['id']}/access-requests", headers=_auth_header(user["id"]))
        assert resp.status_code == 400
        assert "already" in resp.json()["detail"].lower()

    def test_create_access_request_public_event_rejected(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_public_published_event(host["id"])

        resp = client.post(
            f"/events/{event['id']}/access-requests",
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 400
        assert "private" in resp.json()["detail"].lower()

    def test_create_access_request_host_rejected(self):
        host = _create_test_user()
        event = _create_private_published_event(host["id"])

        resp = client.post(
            f"/events/{event['id']}/access-requests",
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 400
        assert "host" in resp.json()["detail"].lower()

    def test_list_pending_requests_as_host(self):
        host = _create_test_user()
        user1 = _create_test_user()
        user2 = _create_test_user()
        event = _create_private_published_event(host["id"])

        client.post(f"/events/{event['id']}/access-requests", headers=_auth_header(user1["id"]))
        client.post(f"/events/{event['id']}/access-requests", headers=_auth_header(user2["id"]))

        resp = client.get(f"/events/{event['id']}/access-requests", headers=_auth_header(host["id"]))
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 2

    def test_list_requests_non_host_forbidden(self):
        host = _create_test_user()
        other = _create_test_user()
        event = _create_private_published_event(host["id"])

        resp = client.get(f"/events/{event['id']}/access-requests", headers=_auth_header(other["id"]))
        assert resp.status_code == 403


# --- Approve/Deny Tests ---

class TestAccessDecision:
    def test_approve_request(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_private_published_event(host["id"])

        req_resp = client.post(f"/events/{event['id']}/access-requests", headers=_auth_header(user["id"]))
        request_id = req_resp.json()["id"]

        resp = client.patch(
            f"/events/{event['id']}/access-requests/{request_id}",
            json={"status": "approved"},
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"
        assert resp.json()["resolved_at"] is not None

    def test_approve_grants_event_access(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_private_published_event(host["id"])

        # Before approval: limited
        resp = client.get(f"/events/{event['id']}", headers=_auth_header(user["id"]))
        assert "description" not in resp.json() or resp.json().get("description") is None

        # Request and approve
        req_resp = client.post(f"/events/{event['id']}/access-requests", headers=_auth_header(user["id"]))
        request_id = req_resp.json()["id"]
        client.patch(
            f"/events/{event['id']}/access-requests/{request_id}",
            json={"status": "approved"},
            headers=_auth_header(host["id"]),
        )

        # After approval: full detail
        resp = client.get(f"/events/{event['id']}", headers=_auth_header(user["id"]))
        assert resp.json().get("description") is not None

    def test_deny_request(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_private_published_event(host["id"])

        req_resp = client.post(f"/events/{event['id']}/access-requests", headers=_auth_header(user["id"]))
        request_id = req_resp.json()["id"]

        resp = client.patch(
            f"/events/{event['id']}/access-requests/{request_id}",
            json={"status": "rejected"},
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    def test_deny_keeps_limited_access(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_private_published_event(host["id"])

        req_resp = client.post(f"/events/{event['id']}/access-requests", headers=_auth_header(user["id"]))
        request_id = req_resp.json()["id"]
        client.patch(
            f"/events/{event['id']}/access-requests/{request_id}",
            json={"status": "rejected"},
            headers=_auth_header(host["id"]),
        )

        resp = client.get(f"/events/{event['id']}", headers=_auth_header(user["id"]))
        assert "description" not in resp.json() or resp.json().get("description") is None

    def test_decide_non_host_forbidden(self):
        host = _create_test_user()
        user = _create_test_user()
        other = _create_test_user()
        event = _create_private_published_event(host["id"])

        req_resp = client.post(f"/events/{event['id']}/access-requests", headers=_auth_header(user["id"]))
        request_id = req_resp.json()["id"]

        resp = client.patch(
            f"/events/{event['id']}/access-requests/{request_id}",
            json={"status": "approved"},
            headers=_auth_header(other["id"]),
        )
        assert resp.status_code == 403

    def test_decide_already_resolved(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_private_published_event(host["id"])

        req_resp = client.post(f"/events/{event['id']}/access-requests", headers=_auth_header(user["id"]))
        request_id = req_resp.json()["id"]

        # Approve
        client.patch(
            f"/events/{event['id']}/access-requests/{request_id}",
            json={"status": "approved"},
            headers=_auth_header(host["id"]),
        )

        # Try to deny after approval
        resp = client.patch(
            f"/events/{event['id']}/access-requests/{request_id}",
            json={"status": "rejected"},
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 400
        assert "resolved" in resp.json()["detail"].lower()
