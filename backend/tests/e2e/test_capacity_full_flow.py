"""E2E #2 — capacity enforcement → "Full" status surfaced in discovery.

Issue #153 deliverable: "capacity enforcement → 'Full' status". Two
attendees fill the 2-seat capacity, a third tries to attend and is
rejected with a server-side cap, then ``GET /events`` shows the event
with ``is_full=True`` so the discovery UI can render the badge.

Touches: events, attendances, discovery list — three different
routers, end to end.
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
    img = PILImage.new("RGB", (50, 50), color="orange")
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
def _publish_event(
    mock_upload, e2e_client: TestClient, host_token: str, admin_db, *, attendee_limit: int,  # noqa: ARG001
) -> tuple[str, str]:
    """Returns (event_id, title) — the title is unique enough to plug
    straight into the discovery search query, which is text-based."""
    cat_id = (
        admin_db.table("categories").select("id").eq("is_predefined", True).limit(1).execute().data[0]["id"]
    )
    start = datetime.now(UTC) + timedelta(days=3)
    end = start + timedelta(hours=2)
    title = f"CapacityE2E_{uuid.uuid4().hex[:12]}"  # unique → narrows discovery search
    body = {
        "title": title,
        "description": "capacity contract event",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "visibility": "public",
        "is_age_restricted": False,
        "status": "draft",
        "attendee_limit": attendee_limit,
        "category_ids": [cat_id],
        "locations": [
            {"name": "Hall", "latitude": 41.0, "longitude": 29.0, "is_primary": True, "order_index": 0},
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
    return event_id, title


def test_capacity_enforcement_surfaces_full_in_discovery(e2e_client, admin_db) -> None:
    host = _register(e2e_client, "caphost")
    a1 = _register(e2e_client, "capa1")
    a2 = _register(e2e_client, "capa2")
    a3 = _register(e2e_client, "capa3")

    event_id, title = _publish_event(
        e2e_client, host["access_token"], admin_db, attendee_limit=2,
    )

    # First two attendees fill the seats.
    for attendee in (a1, a2):
        resp = e2e_client.post(
            f"/events/{event_id}/attendance",
            json={"status": "going"},
            headers=_auth(attendee["access_token"]),
        )
        assert resp.status_code == 200, resp.json()

    # Third attendee should be blocked — the service rejects the going
    # attempt once the seats are taken.
    third = e2e_client.post(
        f"/events/{event_id}/attendance",
        json={"status": "going"},
        headers=_auth(a3["access_token"]),
    )
    assert third.status_code in (400, 409), third.json()

    # Discovery contract: the event must surface in the listing for the
    # search query (matches the unique title) and carry is_full=True so
    # the frontend can render the "Full" badge. Anything weaker (e.g. a
    # guarded `if items:`) silently lets a regression through.
    listing = e2e_client.get(f"/events?search={title}").json()
    items = [item for item in listing["items"] if item["id"] == event_id]
    assert items, f"event not found in discovery listing for unique title: {listing}"
    item = items[0]
    assert item["is_full"] is True
    assert item["going_count"] == 2

    detail = e2e_client.get(
        f"/events/{event_id}", headers=_auth(host["access_token"]),
    ).json()
    assert detail["is_full"] is True
    assert detail["going_count"] == 2
