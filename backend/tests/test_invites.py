"""Contract tests for invite & access request endpoints.

Phase 2 retains one happy-path integration test per HTTP endpoint. Branch
coverage (forbidden/duplicate/lifecycle gates, notification emission,
token-acceptance edge cases) lives in tests/test_invite_unit.py.
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


def _create_test_user(prefix: str = "invtest") -> dict:
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
    event_id = create_resp.json()["id"]
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
    return create_resp.json()


# --- Contract tests (one happy path per endpoint) ---


class TestCreateInvite:
    """POST /events/{event_id}/invites"""

    def test_create_invite_success(self):
        host = _create_test_user()
        event = _create_private_published_event(host["id"])

        resp = client.post(
            f"/events/{event['id']}/invites",
            json={"max_uses": 5, "expires_in_hours": 48},
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["event_id"] == event["id"]
        assert data["max_uses"] == 5
        assert data["expires_at"] is not None
        assert "token" in data
        assert "invite_url" in data


class TestListInvites:
    """GET /events/{event_id}/invites"""

    def test_list_invites_as_host(self):
        host = _create_test_user()
        event = _create_private_published_event(host["id"])

        client.post(f"/events/{event['id']}/invites", json={}, headers=_auth_header(host["id"]))
        client.post(f"/events/{event['id']}/invites", json={}, headers=_auth_header(host["id"]))

        resp = client.get(f"/events/{event['id']}/invites", headers=_auth_header(host["id"]))
        assert resp.status_code == 200
        assert len(resp.json()["items"]) == 2


class TestAcceptInvite:
    """POST /events/{event_id}/invites/{token}/accept"""

    def test_accept_invite_grants_event_access(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_private_published_event(host["id"])

        # Before invite: limited preview
        before = client.get(f"/events/{event['id']}", headers=_auth_header(user["id"])).json()
        assert before.get("description") is None

        invite_resp = client.post(
            f"/events/{event['id']}/invites",
            json={},
            headers=_auth_header(host["id"]),
        )
        token = invite_resp.json()["token"]

        accept_resp = client.post(
            f"/events/{event['id']}/invites/{token}/accept",
            headers=_auth_header(user["id"]),
        )
        assert accept_resp.status_code == 200

        # After invite: full detail
        after = client.get(f"/events/{event['id']}", headers=_auth_header(user["id"])).json()
        assert after.get("description") is not None


class TestCreateAccessRequest:
    """POST /events/{event_id}/access-requests"""

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


class TestListAccessRequests:
    """GET /events/{event_id}/access-requests"""

    def test_list_pending_requests_as_host(self):
        host = _create_test_user()
        requester = _create_test_user()
        event = _create_private_published_event(host["id"])

        client.post(f"/events/{event['id']}/access-requests", headers=_auth_header(requester["id"]))

        resp = client.get(f"/events/{event['id']}/access-requests", headers=_auth_header(host["id"]))
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == "pending"


class TestDecideAccessRequest:
    """PATCH /events/{event_id}/access-requests/{request_id}"""

    def test_approve_grants_event_access(self):
        host = _create_test_user()
        user = _create_test_user()
        event = _create_private_published_event(host["id"])

        req_resp = client.post(
            f"/events/{event['id']}/access-requests", headers=_auth_header(user["id"]),
        )
        request_id = req_resp.json()["id"]

        resp = client.patch(
            f"/events/{event['id']}/access-requests/{request_id}",
            json={"status": "approved"},
            headers=_auth_header(host["id"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"
        assert resp.json()["resolved_at"] is not None

        # Approved → user now sees full detail
        detail = client.get(f"/events/{event['id']}", headers=_auth_header(user["id"])).json()
        assert detail.get("description") is not None
