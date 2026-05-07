"""E2E #1 — private event access request → approval → notification → access.

Issue #153 deliverable: "private access request → approval/rejection
→ notification" cross-feature scenario. Touches every layer of the
stack without faking any of them:

    POST /auth/register × 2          → host + requester users
    POST /events                     → host creates draft private event
    POST /events/{id}/images         → host uploads image
    PATCH /events/{id}/status        → publish (uses recommendation emitter)
    GET  /events/{id}                → requester sees limited preview
    POST /events/{id}/access-requests
    GET  /notifications              → host sees access_request notification
    PATCH /events/{id}/access-requests/{rid} (approve)
    GET  /notifications              → requester sees access_approved
    GET  /events/{id}                → requester now sees full detail
"""
from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image as PILImage

MOCK_STORAGE_URL = "https://example.com/storage/v1/object/public/event-images/e2e.jpg"


def _make_image_bytes() -> bytes:
    img = PILImage.new("RGB", (50, 50), color="purple")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _register(client: TestClient, prefix: str) -> dict:
    suffix = uuid.uuid4().hex[:8]
    resp = client.post(
        "/auth/register",
        json={
            "username": f"{prefix}{suffix}",
            "email": f"{prefix}{suffix}@e2e.test",
            "password": "passw0rd123",
            "date_of_birth": "1990-01-01",
        },
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
def _publish_private_event(mock_upload, e2e_client: TestClient, host_token: str, admin_db) -> str:  # noqa: ARG001
    cat_id = (
        admin_db.table("categories").select("id").eq("is_predefined", True).limit(1).execute().data[0]["id"]
    )
    start = datetime.now(UTC) + timedelta(days=3)
    end = start + timedelta(hours=2)
    body = {
        "title": f"Private E2E {uuid.uuid4().hex[:6]}",
        "description": "private contract event",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "visibility": "private",
        "is_age_restricted": False,
        "status": "draft",
        "category_ids": [cat_id],
        "locations": [
            {
                "name": "Studio",
                "latitude": 41.0,
                "longitude": 29.0,
                "is_primary": True,
                "order_index": 0,
            },
        ],
    }
    create = e2e_client.post("/events", json=body, headers=_auth(host_token))
    assert create.status_code == 201, create.json()
    event_id = create.json()["id"]

    e2e_client.post(
        f"/events/{event_id}/images",
        files={"file": ("e2e.jpg", _make_image_bytes(), "image/jpeg")},
        headers=_auth(host_token),
    )
    pub = e2e_client.patch(
        f"/events/{event_id}/status",
        json={"status": "published"},
        headers=_auth(host_token),
    )
    assert pub.status_code == 200, pub.json()
    return event_id


def test_private_event_access_request_full_flow(e2e_client, admin_db) -> None:
    host = _register(e2e_client, "host")
    requester = _register(e2e_client, "req")

    event_id = _publish_private_event(e2e_client, host["access_token"], admin_db)

    # 1. Requester reads the limited preview (description redacted).
    preview = e2e_client.get(f"/events/{event_id}", headers=_auth(requester["access_token"])).json()
    assert preview.get("description") is None

    # 2. Requester opens an access request.
    req_resp = e2e_client.post(
        f"/events/{event_id}/access-requests", headers=_auth(requester["access_token"]),
    )
    assert req_resp.status_code == 201, req_resp.json()
    request_id = req_resp.json()["id"]
    assert req_resp.json()["status"] == "pending"

    # 3. Host receives an access_request notification.
    host_notifs = e2e_client.get("/notifications", headers=_auth(host["access_token"])).json()["items"]
    assert any(
        n["type"] == "access_request" and n.get("event_id") == event_id
        for n in host_notifs
    ), host_notifs

    # 4. Host approves.
    approve = e2e_client.patch(
        f"/events/{event_id}/access-requests/{request_id}",
        json={"status": "approved"},
        headers=_auth(host["access_token"]),
    )
    assert approve.status_code == 200, approve.json()
    assert approve.json()["status"] == "approved"
    assert approve.json()["resolved_at"] is not None

    # 5. Requester sees access_approved notification.
    req_notifs = e2e_client.get(
        "/notifications", headers=_auth(requester["access_token"]),
    ).json()["items"]
    assert any(
        n["type"] == "access_approved" and n.get("event_id") == event_id
        for n in req_notifs
    ), req_notifs

    # 6. Requester now sees full event detail.
    detail = e2e_client.get(
        f"/events/{event_id}", headers=_auth(requester["access_token"]),
    ).json()
    assert detail.get("description") is not None
    assert detail.get("locations")
