"""E2E #3 — full event lifecycle with itinerary segments.

Issue #153 deliverable: "full event lifecycle with itinerary
(create → publish → edit segments → end)". Touches every endpoint
that itinerary handling threads through:

    POST  /events                       (with segments)
    POST  /events/{id}/images
    PATCH /events/{id}/status (published)
    PUT   /events/{id}                  (replace segments)
    GET   /events/{id}                  (verify new segments)
    PATCH /events/{id}/status (ended)
    GET   /events/{id}                  (verify ended state)
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
    img = PILImage.new("RGB", (50, 50), color="cyan")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _register(client: TestClient, prefix: str) -> dict:
    suffix = uuid.uuid4().hex[:8]
    resp = client.post(
        "/auth/register",
        json={
            "username": f"{prefix}{suffix}",
            "email": f"{prefix}{suffix}@example.com",
            "password": "passw0rd123",
            "date_of_birth": "1990-01-01",
        },
    )
    assert resp.status_code == 201, resp.json()
    return resp.json()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
def test_itinerary_lifecycle(mock_upload, e2e_client, admin_db) -> None:  # noqa: ARG001
    host = _register(e2e_client, "ithost")
    cat_id = (
        admin_db.table("categories").select("id").eq("is_predefined", True).limit(1).execute().data[0]["id"]
    )

    start = datetime.now(UTC) + timedelta(days=3)
    end = start + timedelta(hours=4)
    seg1_start = start + timedelta(minutes=30)
    seg1_end = start + timedelta(minutes=90)
    seg2_start = start + timedelta(minutes=120)
    seg2_end = start + timedelta(minutes=180)

    # 1. Create draft with two segments.
    body = {
        "title": f"Itinerary E2E {uuid.uuid4().hex[:6]}",
        "description": "two-stop walk",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "visibility": "public",
        "is_age_restricted": False,
        "status": "draft",
        "category_ids": [cat_id],
        "locations": [
            {"name": "Stop A", "latitude": 41.0, "longitude": 29.0, "is_primary": True, "order_index": 0},
            {"name": "Stop B", "latitude": 41.1, "longitude": 29.1, "is_primary": False, "order_index": 1},
        ],
        "segments": [
            {
                "location_index": 0, "order_index": 0,
                "start_datetime": seg1_start.isoformat(),
                "end_datetime": seg1_end.isoformat(),
                "description": "Welcome at Stop A",
            },
            {
                "location_index": 1, "order_index": 1,
                "start_datetime": seg2_start.isoformat(),
                "end_datetime": seg2_end.isoformat(),
                "description": "Walk to Stop B",
            },
        ],
    }
    create = e2e_client.post("/events", json=body, headers=_auth(host["access_token"]))
    assert create.status_code == 201, create.json()
    event_id = create.json()["id"]
    assert len(create.json()["segments"]) == 2

    # 2. Upload image + publish.
    e2e_client.post(
        f"/events/{event_id}/images",
        files={"file": ("e2e.jpg", _make_image_bytes(), "image/jpeg")},
        headers=_auth(host["access_token"]),
    )
    pub = e2e_client.patch(
        f"/events/{event_id}/status",
        json={"status": "published"},
        headers=_auth(host["access_token"]),
    )
    assert pub.status_code == 200, pub.json()
    assert pub.json()["status"] == "published"

    # 3. Edit segments — swap descriptions, keep timing.
    new_segments = [
        {
            "location_index": 0, "order_index": 0,
            "start_datetime": seg1_start.isoformat(),
            "end_datetime": seg1_end.isoformat(),
            "description": "Updated welcome",
        },
        {
            "location_index": 1, "order_index": 1,
            "start_datetime": seg2_start.isoformat(),
            "end_datetime": seg2_end.isoformat(),
            "description": "Updated walk",
        },
    ]
    edit = e2e_client.put(
        f"/events/{event_id}",
        json={"segments": new_segments},
        headers=_auth(host["access_token"]),
    )
    assert edit.status_code == 200, edit.json()
    assert edit.json()["status"] == "updated"  # published → updated on real change

    # 4. GET shows the new descriptions.
    detail = e2e_client.get(
        f"/events/{event_id}", headers=_auth(host["access_token"]),
    ).json()
    descriptions = sorted(s["description"] for s in detail["segments"])
    assert descriptions == ["Updated walk", "Updated welcome"]

    # 5. End the event (host triggers).
    ended = e2e_client.patch(
        f"/events/{event_id}/status",
        json={"status": "ended"},
        headers=_auth(host["access_token"]),
    )
    assert ended.status_code == 200, ended.json()
    assert ended.json()["status"] == "ended"

    # 6. Final GET — status is ended; segments survive (history).
    final = e2e_client.get(
        f"/events/{event_id}", headers=_auth(host["access_token"]),
    ).json()
    assert final["status"] == "ended"
    assert len(final["segments"]) == 2
