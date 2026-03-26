"""Tests for Event CRUD endpoints"""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.database import get_supabase
from app.main import app
from app.services.auth import create_access_token

client = TestClient(app)

db = get_supabase()


# --- Helpers ---

def _auth_header(user_id: str) -> dict:
    token = create_access_token(user_id, "test@test.com")
    return {"Authorization": f"Bearer {token}"}


def _create_test_user(suffix: str = "") -> dict:
    """Create a test user and return it."""
    import uuid
    unique = uuid.uuid4().hex[:8]
    user_data = {
        "username": f"eventtest_{unique}{suffix}",
        "email": f"eventtest_{unique}{suffix}@example.com",
        "hashed_password": "fakehash",
        "role": "registered",
        "auth_provider": "local",
        "email_verified": True,
        "is_active": True,
    }
    result = db.table("users").insert(user_data).execute()
    return result.data[0]


def _get_category_ids(count: int = 1) -> list[str]:
    """Get existing predefined category IDs."""
    result = (
        db.table("categories")
        .select("id")
        .eq("is_predefined", True)
        .limit(count)
        .execute()
    )
    return [row["id"] for row in result.data]


def _valid_event_body(category_ids: list[str] | None = None, **overrides) -> dict:
    """Build a valid event creation request body."""
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


def _create_published_event(user_id: str, cat_ids: list[str], **overrides) -> dict:
    """Create a draft event, upload an image, then publish it. Returns event detail."""
    import io

    from PIL import Image as PILImage

    body = _valid_event_body(cat_ids, status="draft", **overrides)
    resp = client.post("/events", json=body, headers=_auth_header(user_id))
    event_id = resp.json()["id"]

    # Upload image
    img = PILImage.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    client.post(
        f"/events/{event_id}/images",
        files={"file": ("test.jpg", buf, "image/jpeg")},
        headers=_auth_header(user_id),
    )

    # Publish
    client.patch(
        f"/events/{event_id}/status",
        json={"status": "published"},
        headers=_auth_header(user_id),
    )
    return client.get(f"/events/{event_id}", headers=_auth_header(user_id)).json()


def _cleanup_event(event_id: str):
    """Delete an event and all related data."""
    db.table("equipment_requirements").delete().eq("event_id", event_id).execute()
    db.table("venue_metadata").delete().eq("event_id", event_id).execute()
    db.table("event_categories").delete().eq("event_id", event_id).execute()
    db.table("event_locations").delete().eq("event_id", event_id).execute()
    db.table("events").delete().eq("id", event_id).execute()


def _cleanup_user(user_id: str):
    """Delete a test user and all related data."""
    db.table("users").delete().eq("id", user_id).execute()


# --- Tests ---

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

    def test_create_event_published_rejected(self):
        """Cannot publish directly on create — images must be uploaded first."""
        user = _create_test_user("pub")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids, status="published")

        resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        assert resp.status_code == 400
        assert "Cannot publish directly" in resp.json()["detail"]

        _cleanup_user(user["id"])

    def test_create_event_with_venue_metadata(self):
        user = _create_test_user("venue")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids, venue_metadata={
            "price": "free",
            "language": "Turkish",
            "wheelchair_access": True,
        })

        resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        assert resp.status_code == 201

        data = resp.json()
        assert data["venue_metadata"] is not None
        assert data["venue_metadata"]["price"] == "free"
        assert data["venue_metadata"]["wheelchair_access"] is True

        _cleanup_event(data["id"])
        _cleanup_user(user["id"])

    def test_create_event_with_equipment(self):
        user = _create_test_user("equip")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids, equipment_requirements=[
            {"item_name": "Yoga Mat", "is_required": True},
            {"item_name": "Water Bottle", "is_required": False},
        ])

        resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        assert resp.status_code == 201

        data = resp.json()
        assert len(data["equipment_requirements"]) == 2

        _cleanup_event(data["id"])
        _cleanup_user(user["id"])

    def test_create_event_multiple_locations(self):
        user = _create_test_user("multiloc")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids, locations=[
            {"name": "Start Point", "latitude": 41.0, "longitude": 28.9, "is_primary": True, "order_index": 0},
            {"name": "End Point", "latitude": 41.1, "longitude": 29.0, "is_primary": False, "order_index": 1},
        ])

        resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        assert resp.status_code == 201
        assert len(resp.json()["locations"]) == 2

        _cleanup_event(resp.json()["id"])
        _cleanup_user(user["id"])

    def test_create_event_invalid_datetime(self):
        user = _create_test_user("baddate")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids,
            start_datetime=(datetime.now(UTC) + timedelta(days=2)).isoformat(),
            end_datetime=(datetime.now(UTC) + timedelta(days=1)).isoformat(),
        )

        resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        assert resp.status_code == 400
        assert "end_datetime" in resp.json()["detail"]

        _cleanup_user(user["id"])

    def test_create_event_invalid_category(self):
        user = _create_test_user("badcat")
        body = _valid_event_body(["00000000-0000-0000-0000-000000000000"])

        resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        assert resp.status_code == 400
        assert "category" in resp.json()["detail"].lower()

        _cleanup_user(user["id"])

    def test_create_event_duplicate(self):
        user = _create_test_user("dup")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids, title="Duplicate Event")

        resp1 = client.post("/events", json=body, headers=_auth_header(user["id"]))
        assert resp1.status_code == 201

        resp2 = client.post("/events", json=body, headers=_auth_header(user["id"]))
        assert resp2.status_code == 409

        _cleanup_event(resp1.json()["id"])
        _cleanup_user(user["id"])

    def test_create_event_no_auth(self):
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids)

        resp = client.post("/events", json=body)
        assert resp.status_code == 401

    def test_create_event_missing_title(self):
        user = _create_test_user("notitle")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids)
        del body["title"]

        resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        assert resp.status_code == 422

        _cleanup_user(user["id"])

    def test_create_event_no_locations(self):
        user = _create_test_user("noloc")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids, locations=[])

        resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        assert resp.status_code == 422

        _cleanup_user(user["id"])

    def test_create_event_no_categories(self):
        user = _create_test_user("nocat")
        body = _valid_event_body([])

        resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        assert resp.status_code == 422

        _cleanup_user(user["id"])


# --- Faz 2: GET /events/{id} ---

class TestGetEvent:

    def test_get_event_full_detail(self):
        """Registered user gets full detail of a public event."""
        user = _create_test_user("getfull")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)
        event_id = event["id"]

        resp = client.get(f"/events/{event_id}", headers=_auth_header(user["id"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == event_id
        assert data["title"] == "Test Event"
        assert "locations" in data
        assert "categories" in data
        assert "description" in data

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_get_event_guest_limited(self):
        """Guest (no auth) gets limited preview."""
        user = _create_test_user("getguest")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)
        event_id = event["id"]

        resp = client.get(f"/events/{event_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Test Event"
        assert "description" not in data
        assert "locations" not in data

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_get_private_event_host_sees_full(self):
        """Host can see full detail of their own private event."""
        user = _create_test_user("privhost")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids, visibility="private")

        create_resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        event_id = create_resp.json()["id"]

        resp = client.get(f"/events/{event_id}", headers=_auth_header(user["id"]))
        assert resp.status_code == 200
        assert "description" in resp.json()
        assert "locations" in resp.json()

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_get_private_event_other_user_limited(self):
        """Non-host gets limited preview of private event."""
        host = _create_test_user("privowner")
        other = _create_test_user("privother")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(host["id"], cat_ids, visibility="private")
        event_id = event["id"]

        resp = client.get(f"/events/{event_id}", headers=_auth_header(other["id"]))
        assert resp.status_code == 200
        assert "description" not in resp.json()
        assert "locations" not in resp.json()

        _cleanup_event(event_id)
        _cleanup_user(host["id"])
        _cleanup_user(other["id"])

    def test_get_event_not_found(self):
        user = _create_test_user("notfound")
        resp = client.get("/events/00000000-0000-0000-0000-000000000000", headers=_auth_header(user["id"]))
        assert resp.status_code == 404

        _cleanup_user(user["id"])

    def test_get_event_auto_end(self):
        """Event with past end_datetime is auto-ended on read."""
        user = _create_test_user("autoend")
        cat_ids = _get_category_ids(1)

        # Insert directly into DB to bypass datetime validation (event in the past)
        event_data = {
            "host_id": user["id"],
            "title": "Past Event",
            "description": "Already ended",
            "start_datetime": (datetime.now(UTC) - timedelta(hours=3)).isoformat(),
            "end_datetime": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "visibility": "public",
            "status": "published",
        }
        result = db.table("events").insert(event_data).execute()
        event_id = result.data[0]["id"]
        db.table("event_locations").insert({
            "event_id": event_id, "name": "Test", "latitude": 41.0,
            "longitude": 29.0, "is_primary": True, "order_index": 0,
        }).execute()
        db.table("event_categories").insert({
            "event_id": event_id, "category_id": cat_ids[0],
        }).execute()

        resp = client.get(f"/events/{event_id}", headers=_auth_header(user["id"]))
        assert resp.status_code == 200
        assert resp.json()["status"] == "ended"

        _cleanup_event(event_id)
        _cleanup_user(user["id"])


# --- Faz 2: PUT /events/{id} ---

class TestUpdateEvent:

    def _create_draft_event(self, user_id: str) -> str:
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids, status="draft")
        resp = client.post("/events", json=body, headers=_auth_header(user_id))
        return resp.json()["id"]

    def test_update_title(self):
        user = _create_test_user("uptitle")
        event_id = self._create_draft_event(user["id"])

        resp = client.put(
            f"/events/{event_id}",
            json={"title": "Updated Title"},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_update_published_becomes_updated(self):
        user = _create_test_user("uppub")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)
        event_id = event["id"]

        resp = client.put(
            f"/events/{event_id}",
            json={"description": "New description"},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "updated"

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_update_not_host_forbidden(self):
        host = _create_test_user("uphost")
        other = _create_test_user("upother")
        event_id = self._create_draft_event(host["id"])

        resp = client.put(
            f"/events/{event_id}",
            json={"title": "Hacked"},
            headers=_auth_header(other["id"]),
        )
        assert resp.status_code == 403

        _cleanup_event(event_id)
        _cleanup_user(host["id"])
        _cleanup_user(other["id"])

    def test_update_cancelled_event_fails(self):
        user = _create_test_user("upcancel")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)
        event_id = event["id"]

        # Cancel the event directly in DB
        db.table("events").update({"status": "cancelled"}).eq("id", event_id).execute()

        resp = client.put(
            f"/events/{event_id}",
            json={"title": "Nope"},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 400

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_update_time_after_start_fails(self):
        """Cannot change time/location after event has started."""
        user = _create_test_user("upstarted")

        # Insert event that already started
        event_data = {
            "host_id": user["id"],
            "title": "Started Event",
            "description": "Already running",
            "start_datetime": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "end_datetime": (datetime.now(UTC) + timedelta(hours=2)).isoformat(),
            "visibility": "public",
            "status": "published",
        }
        result = db.table("events").insert(event_data).execute()
        event_id = result.data[0]["id"]
        loc_data = {"event_id": event_id, "name": "Loc", "latitude": 41.0, "longitude": 29.0, "is_primary": True, "order_index": 0}
        db.table("event_locations").insert(loc_data).execute()

        resp = client.put(
            f"/events/{event_id}",
            json={"start_datetime": (datetime.now(UTC) + timedelta(days=1)).isoformat()},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 400
        assert "started" in resp.json()["detail"].lower()

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_update_no_auth(self):
        resp = client.put("/events/some-id", json={"title": "x"})
        assert resp.status_code == 401


# --- Faz 3: PATCH /events/{id}/status ---

class TestChangeEventStatus:

    def test_draft_to_published_no_image_rejected(self):
        """Cannot publish without at least one image."""
        user = _create_test_user("d2p")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids, status="draft")
        create_resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        event_id = create_resp.json()["id"]

        resp = client.patch(
            f"/events/{event_id}/status",
            json={"status": "published"},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 400
        assert "at least one image" in resp.json()["detail"]

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_draft_to_published_with_image(self):
        """Publish succeeds when image exists."""
        user = _create_test_user("d2pi")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids, status="draft")
        create_resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        event_id = create_resp.json()["id"]

        # Upload a test image
        import io

        from PIL import Image as PILImage
        img = PILImage.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        client.post(
            f"/events/{event_id}/images",
            files={"file": ("test.jpg", buf, "image/jpeg")},
            headers=_auth_header(user["id"]),
        )

        resp = client.patch(
            f"/events/{event_id}/status",
            json={"status": "published"},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_published_to_cancelled(self):
        user = _create_test_user("p2c")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)
        event_id = event["id"]

        resp = client.patch(
            f"/events/{event_id}/status",
            json={"status": "cancelled"},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_published_to_ended(self):
        user = _create_test_user("p2e")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)
        event_id = event["id"]

        resp = client.patch(
            f"/events/{event_id}/status",
            json={"status": "ended"},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ended"

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_invalid_transition_cancelled_to_published(self):
        user = _create_test_user("c2p")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)
        event_id = event["id"]

        # Cancel first
        client.patch(f"/events/{event_id}/status", json={"status": "cancelled"}, headers=_auth_header(user["id"]))

        # Try to republish
        resp = client.patch(
            f"/events/{event_id}/status",
            json={"status": "published"},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 400

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_invalid_transition_draft_to_cancelled(self):
        user = _create_test_user("d2c")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids, status="draft")
        create_resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        event_id = create_resp.json()["id"]

        resp = client.patch(
            f"/events/{event_id}/status",
            json={"status": "cancelled"},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 400

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_status_change_not_host(self):
        host = _create_test_user("stathost")
        other = _create_test_user("statother")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids, status="draft")
        create_resp = client.post("/events", json=body, headers=_auth_header(host["id"]))
        event_id = create_resp.json()["id"]

        resp = client.patch(
            f"/events/{event_id}/status",
            json={"status": "published"},
            headers=_auth_header(other["id"]),
        )
        assert resp.status_code == 403

        _cleanup_event(event_id)
        _cleanup_user(host["id"])
        _cleanup_user(other["id"])


# --- Faz 3: DELETE /events/{id} ---

class TestDeleteEvent:

    def test_delete_cancelled_event(self):
        user = _create_test_user("delcancel")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)
        event_id = event["id"]

        # Cancel first
        client.patch(f"/events/{event_id}/status", json={"status": "cancelled"}, headers=_auth_header(user["id"]))

        resp = client.delete(f"/events/{event_id}", headers=_auth_header(user["id"]))
        assert resp.status_code == 200
        assert resp.json()["message"] == "Event deleted successfully"

        # Verify deleted
        get_resp = client.get(f"/events/{event_id}", headers=_auth_header(user["id"]))
        assert get_resp.status_code == 404

        _cleanup_user(user["id"])

    def test_delete_ended_event(self):
        user = _create_test_user("delended")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)
        event_id = event["id"]

        # End first
        client.patch(f"/events/{event_id}/status", json={"status": "ended"}, headers=_auth_header(user["id"]))

        resp = client.delete(f"/events/{event_id}", headers=_auth_header(user["id"]))
        assert resp.status_code == 200

        _cleanup_user(user["id"])

    def test_delete_published_event_fails(self):
        user = _create_test_user("delpub")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)
        event_id = event["id"]

        resp = client.delete(f"/events/{event_id}", headers=_auth_header(user["id"]))
        assert resp.status_code == 400

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_delete_not_host(self):
        host = _create_test_user("delhost")
        other = _create_test_user("delother")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(host["id"], cat_ids)
        event_id = event["id"]

        # Cancel first
        client.patch(f"/events/{event_id}/status", json={"status": "cancelled"}, headers=_auth_header(host["id"]))

        resp = client.delete(f"/events/{event_id}", headers=_auth_header(other["id"]))
        assert resp.status_code == 403

        _cleanup_event(event_id)
        _cleanup_user(host["id"])
        _cleanup_user(other["id"])

    def test_delete_no_auth(self):
        resp = client.delete("/events/some-id")
        assert resp.status_code == 401


# --- Additional tests for review findings ---

class TestAgeRestriction:

    def test_underage_user_blocked(self):
        """User under 18 cannot view age-restricted event."""
        from datetime import date
        host = _create_test_user("agehost")
        import uuid
        unique = uuid.uuid4().hex[:8]
        young_dob = date(date.today().year - 15, 1, 1).isoformat()
        young_user = db.table("users").insert({
            "username": f"young_{unique}",
            "email": f"young_{unique}@example.com",
            "hashed_password": "fakehash",
            "role": "registered",
            "auth_provider": "local",
            "email_verified": True,
            "is_active": True,
            "date_of_birth": young_dob,
        }).execute().data[0]

        cat_ids = _get_category_ids(1)
        event = _create_published_event(host["id"], cat_ids, is_age_restricted=True)
        event_id = event["id"]

        resp = client.get(f"/events/{event_id}", headers=_auth_header(young_user["id"]))
        assert resp.status_code == 403
        assert "18" in resp.json()["detail"]

        _cleanup_event(event_id)
        _cleanup_user(host["id"])
        _cleanup_user(young_user["id"])

    def test_no_dob_blocked_from_age_restricted(self):
        """User without date_of_birth cannot view age-restricted event."""
        host = _create_test_user("agenodob_host")
        import uuid
        unique = uuid.uuid4().hex[:8]
        no_dob_user = db.table("users").insert({
            "username": f"nodob_{unique}",
            "email": f"nodob_{unique}@example.com",
            "hashed_password": "fakehash",
            "role": "registered",
            "auth_provider": "local",
            "email_verified": True,
            "is_active": True,
        }).execute().data[0]

        cat_ids = _get_category_ids(1)
        event = _create_published_event(host["id"], cat_ids, is_age_restricted=True)
        event_id = event["id"]

        resp = client.get(f"/events/{event_id}", headers=_auth_header(no_dob_user["id"]))
        assert resp.status_code == 403
        assert "date of birth" in resp.json()["detail"].lower()

        _cleanup_event(event_id)
        _cleanup_user(host["id"])
        _cleanup_user(no_dob_user["id"])

    def test_host_exempt_from_age_restriction(self):
        """Host can always view their own age-restricted event."""
        host = _create_test_user("ageexempt")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(host["id"], cat_ids, is_age_restricted=True)
        event_id = event["id"]

        resp = client.get(f"/events/{event_id}", headers=_auth_header(host["id"]))
        assert resp.status_code == 200
        assert "description" in resp.json()

        _cleanup_event(event_id)
        _cleanup_user(host["id"])


class TestUpdatedStatusTransitions:

    def test_updated_to_cancelled(self):
        user = _create_test_user("u2c")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)
        event_id = event["id"]

        # Update to get "updated" status
        client.put(f"/events/{event_id}", json={"title": "Changed"}, headers=_auth_header(user["id"]))

        resp = client.patch(
            f"/events/{event_id}/status",
            json={"status": "cancelled"},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_updated_to_ended(self):
        user = _create_test_user("u2e")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)
        event_id = event["id"]

        # Update to get "updated" status
        client.put(f"/events/{event_id}", json={"title": "Changed"}, headers=_auth_header(user["id"]))

        resp = client.patch(
            f"/events/{event_id}/status",
            json={"status": "ended"},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ended"

        _cleanup_event(event_id)
        _cleanup_user(user["id"])


class TestInvalidUUID:

    def test_get_invalid_uuid(self):
        user = _create_test_user("baduuid")
        resp = client.get("/events/not-a-uuid", headers=_auth_header(user["id"]))
        assert resp.status_code == 422
        _cleanup_user(user["id"])

    def test_delete_invalid_uuid(self):
        user = _create_test_user("baduuid2")
        resp = client.delete("/events/not-a-uuid", headers=_auth_header(user["id"]))
        assert resp.status_code == 422
        _cleanup_user(user["id"])


class TestCreateEventFutureDate:

    def test_create_event_past_start_fails(self):
        user = _create_test_user("paststart")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids,
            start_datetime=(datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            end_datetime=(datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        )
        resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        assert resp.status_code == 400
        assert "future" in resp.json()["detail"].lower()

        _cleanup_user(user["id"])


class TestClearAttendeeLimit:

    def test_clear_attendee_limit(self):
        user = _create_test_user("clearlimit")
        cat_ids = _get_category_ids(1)
        body = _valid_event_body(cat_ids, attendee_limit=50)
        create_resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        event_id = create_resp.json()["id"]
        assert create_resp.json()["attendee_limit"] == 50

        resp = client.put(
            f"/events/{event_id}",
            json={"clear_attendee_limit": True},
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 200
        assert resp.json()["attendee_limit"] is None

        _cleanup_event(event_id)
        _cleanup_user(user["id"])
