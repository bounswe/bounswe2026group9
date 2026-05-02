"""Tests for GET /events — event discovery (search, filter, pagination)."""

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


# --- Helpers ---

def _auth_header(user_id: str) -> dict:
    token = create_access_token(user_id, "test@test.com")
    return {"Authorization": f"Bearer {token}"}


def _create_test_user(suffix: str = "") -> dict:
    username, email = build_test_identity("disctest", suffix=suffix)
    result = db.table("users").insert({
        "username": username,
        "email": email,
        "hashed_password": "fakehash",
        "role": "registered",
        "auth_provider": "local",
        "email_verified": True,
        "is_active": True,
    }).execute()
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


def _make_image_bytes() -> bytes:
    img = PILImage.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@patch("app.repositories.image.upload_to_storage", return_value=MOCK_STORAGE_URL)
def _create_published_event(
    user_id: str,
    cat_ids: list[str],
    mock_upload,  # noqa: ARG001
    *,
    title: str = "Discovery Test Event",
    description: str = "A test event for discovery",
    days_from_now: float = 1,
    visibility: str = "public",
) -> dict:
    """Create a draft event, upload a mock image, then publish it."""
    start = datetime.now(UTC) + timedelta(days=days_from_now)
    end = start + timedelta(hours=2)
    body = {
        "title": title,
        "description": description,
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "visibility": visibility,
        "is_age_restricted": False,
        "status": "draft",
        "category_ids": cat_ids,
        "locations": [{"name": "Test Venue", "latitude": 41.0, "longitude": 29.0, "is_primary": True, "order_index": 0}],
    }
    resp = client.post("/events", json=body, headers=_auth_header(user_id))
    event_id = resp.json()["id"]

    client.post(
        f"/events/{event_id}/images",
        files={"file": ("test.jpg", _make_image_bytes(), "image/jpeg")},
        headers=_auth_header(user_id),
    )
    client.patch(
        f"/events/{event_id}/status",
        json={"status": "published"},
        headers=_auth_header(user_id),
    )
    return client.get(f"/events/{event_id}", headers=_auth_header(user_id)).json()


def _cleanup_event(event_id: str) -> None:
    db.table("event_images").delete().eq("event_id", event_id).execute()
    db.table("equipment_requirements").delete().eq("event_id", event_id).execute()
    db.table("venue_metadata").delete().eq("event_id", event_id).execute()
    db.table("event_categories").delete().eq("event_id", event_id).execute()
    db.table("event_locations").delete().eq("event_id", event_id).execute()
    db.table("events").delete().eq("id", event_id).execute()


def _cleanup_user(user_id: str) -> None:
    db.table("users").delete().eq("id", user_id).execute()


# --- Tests ---

class TestListEventsBasic:
    """GET /events — basic listing."""

    def test_returns_200_without_auth(self):
        resp = client.get("/events")
        assert resp.status_code == 200

    def test_response_shape(self):
        resp = client.get("/events")
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data

    def test_published_event_appears_in_listing(self):
        user = _create_test_user("basic")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)

        resp = client.get("/events")
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert event["id"] in ids

        _cleanup_event(event["id"])
        _cleanup_user(user["id"])

    def test_draft_event_not_in_listing(self):
        user = _create_test_user("draft")
        cat_ids = _get_category_ids(1)
        start = (datetime.now(UTC) + timedelta(days=2)).isoformat()
        end = (datetime.now(UTC) + timedelta(days=2, hours=2)).isoformat()
        body = {
            "title": "Draft Hidden Event",
            "description": "Should not appear",
            "start_datetime": start,
            "end_datetime": end,
            "visibility": "public",
            "status": "draft",
            "category_ids": cat_ids,
            "locations": [{"name": "Loc", "latitude": 0.0, "longitude": 0.0, "is_primary": True, "order_index": 0}],
        }
        resp = client.post("/events", json=body, headers=_auth_header(user["id"]))
        event_id = resp.json()["id"]

        list_resp = client.get("/events")
        ids = [item["id"] for item in list_resp.json()["items"]]
        assert event_id not in ids

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_private_event_appears_with_limited_info(self):
        """Private published events show title/image/location but hide description."""
        user = _create_test_user("priv")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids, visibility="private")

        list_resp = client.get("/events")
        ids = [item["id"] for item in list_resp.json()["items"]]
        assert event["id"] in ids

        item = next(i for i in list_resp.json()["items"] if i["id"] == event["id"])
        assert item["description"] is None
        assert item["primary_image_url"] is not None  # image visible for discovery/map
        assert item["primary_location"] is not None   # location visible for map view

        _cleanup_event(event["id"])
        _cleanup_user(user["id"])

    def test_past_end_datetime_not_in_listing(self):
        """Events whose end_datetime has already passed must not appear in discovery."""
        user = _create_test_user("pastend")
        cat_ids = _get_category_ids(1)
        from datetime import UTC, datetime, timedelta
        result = db.table("events").insert({
            "host_id": user["id"],
            "title": "Past Event Should Not Appear",
            "description": "Should not appear",
            "start_datetime": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
            "end_datetime": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "visibility": "public",
            "status": "published",
            "is_age_restricted": False,
            "attendee_count": 0,
        }).execute()
        event_id = result.data[0]["id"]
        db.table("event_categories").insert({"event_id": event_id, "category_id": cat_ids[0]}).execute()

        resp = client.get("/events")
        ids = [i["id"] for i in resp.json()["items"]]
        assert event_id not in ids

        _cleanup_event(event_id)
        _cleanup_user(user["id"])

    def test_cancelled_event_not_in_listing(self):
        user = _create_test_user("cancel")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)

        client.patch(
            f"/events/{event['id']}/status",
            json={"status": "cancelled"},
            headers=_auth_header(user["id"]),
        )

        list_resp = client.get("/events")
        ids = [item["id"] for item in list_resp.json()["items"]]
        assert event["id"] not in ids

        _cleanup_event(event["id"])
        _cleanup_user(user["id"])

    def test_list_item_fields_present_auth_user(self):
        """Authenticated users receive full fields for public events."""
        user = _create_test_user("fields")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids, title="Fields Check Event")

        resp = client.get("/events", headers=_auth_header(user["id"]))
        items = resp.json()["items"]
        item = next((i for i in items if i["id"] == event["id"]), None)
        assert item is not None
        for field in ("id", "title", "description", "start_datetime", "end_datetime",
                      "visibility", "is_age_restricted", "attendee_count", "status", "categories"):
            assert field in item
        assert item["description"] is not None
        assert item["primary_location"] is not None
        assert item["primary_image_url"] == MOCK_STORAGE_URL

        _cleanup_event(event["id"])
        _cleanup_user(user["id"])

    def test_guest_sees_limited_info_auth_sees_full(self):
        """Guests get limited fields; authenticated users get full details."""
        user = _create_test_user("guestauth")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids)

        guest_resp = client.get("/events")
        auth_resp = client.get("/events", headers=_auth_header(user["id"]))

        assert guest_resp.status_code == 200
        assert auth_resp.status_code == 200

        guest_ids = [i["id"] for i in guest_resp.json()["items"]]
        auth_ids = [i["id"] for i in auth_resp.json()["items"]]
        assert event["id"] in guest_ids
        assert event["id"] in auth_ids

        guest_item = next(i for i in guest_resp.json()["items"] if i["id"] == event["id"])
        assert guest_item["description"] is None
        assert guest_item["primary_image_url"] is not None  # image always visible
        assert guest_item["primary_location"] is not None   # location visible for map browsing

        auth_item = next(i for i in auth_resp.json()["items"] if i["id"] == event["id"])
        assert auth_item["description"] is not None
        assert auth_item["primary_image_url"] == MOCK_STORAGE_URL
        assert auth_item["primary_location"] is not None

        _cleanup_event(event["id"])
        _cleanup_user(user["id"])


class TestListEventsSortOrder:
    """Results must be sorted by start_datetime ascending."""

    def test_sorted_by_start_datetime(self):
        user = _create_test_user("sort")
        cat_ids = _get_category_ids(1)

        e1 = _create_published_event(user["id"], cat_ids, title="Sort Event A", days_from_now=5)
        e2 = _create_published_event(user["id"], cat_ids, title="Sort Event B", days_from_now=3)
        e3 = _create_published_event(user["id"], cat_ids, title="Sort Event C", days_from_now=7)

        resp = client.get("/events")
        items = resp.json()["items"]
        event_ids_in_order = [i["id"] for i in items]

        # All three should be present
        pos_e1 = event_ids_in_order.index(e1["id"])
        pos_e2 = event_ids_in_order.index(e2["id"])
        pos_e3 = event_ids_in_order.index(e3["id"])
        # e2 (3 days) < e1 (5 days) < e3 (7 days)
        assert pos_e2 < pos_e1 < pos_e3

        for e in (e1, e2, e3):
            _cleanup_event(e["id"])
        _cleanup_user(user["id"])


class TestListEventsSearch:
    """Text search across title and description."""

    def test_search_by_title(self):
        user = _create_test_user("srchtitle")
        cat_ids = _get_category_ids(1)
        unique = uuid.uuid4().hex[:6]
        event = _create_published_event(user["id"], cat_ids, title=f"UniqueTitle{unique}")

        resp = client.get(f"/events?search=UniqueTitle{unique}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        ids = [i["id"] for i in data["items"]]
        assert event["id"] in ids

        _cleanup_event(event["id"])
        _cleanup_user(user["id"])

    def test_search_by_description(self):
        user = _create_test_user("srchdesc")
        cat_ids = _get_category_ids(1)
        unique = uuid.uuid4().hex[:6]
        event = _create_published_event(
            user["id"], cat_ids,
            title="Normal Title",
            description=f"UniqueDesc{unique} special description",
        )

        resp = client.get(f"/events?search=UniqueDesc{unique}")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert event["id"] in ids

        _cleanup_event(event["id"])
        _cleanup_user(user["id"])

    def test_search_no_results(self):
        resp = client.get("/events?search=xyznonexistent99999")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["items"] == []

    def test_search_is_case_insensitive(self):
        user = _create_test_user("srchcase")
        cat_ids = _get_category_ids(1)
        unique = uuid.uuid4().hex[:6]
        event = _create_published_event(user["id"], cat_ids, title=f"CaseSensitive{unique}")

        resp = client.get(f"/events?search=casesensitive{unique}")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert event["id"] in ids

        _cleanup_event(event["id"])
        _cleanup_user(user["id"])

    def test_search_excludes_non_matching(self):
        user = _create_test_user("srchexcl")
        cat_ids = _get_category_ids(1)
        unique_match = uuid.uuid4().hex[:6]
        unique_no = uuid.uuid4().hex[:6]
        ev_match = _create_published_event(user["id"], cat_ids, title=f"Match{unique_match}")
        ev_no = _create_published_event(user["id"], cat_ids, title=f"Nope{unique_no}")

        resp = client.get(f"/events?search=Match{unique_match}")
        ids = [i["id"] for i in resp.json()["items"]]
        assert ev_match["id"] in ids
        assert ev_no["id"] not in ids

        _cleanup_event(ev_match["id"])
        _cleanup_event(ev_no["id"])
        _cleanup_user(user["id"])


class TestListEventsCategoryFilter:
    """Filter by category_id."""

    def test_category_filter_returns_matching_events(self):
        user = _create_test_user("catfilt")
        cat_ids = _get_category_ids(2)
        if len(cat_ids) < 2:
            return  # Need at least 2 categories for this test

        cat_a, cat_b = cat_ids[0], cat_ids[1]
        ev_a = _create_published_event(user["id"], [cat_a], title="Cat A Event")
        ev_b = _create_published_event(user["id"], [cat_b], title="Cat B Event")

        resp = client.get(f"/events?category_id={cat_a}")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert ev_a["id"] in ids
        assert ev_b["id"] not in ids

        _cleanup_event(ev_a["id"])
        _cleanup_event(ev_b["id"])
        _cleanup_user(user["id"])

    def test_category_filter_no_match_returns_empty(self):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/events?category_id={fake_id}")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["items"] == []

    def test_invalid_category_uuid_rejected(self):
        resp = client.get("/events?category_id=not-a-uuid")
        assert resp.status_code == 422


class TestListEventsTemporalFilter:
    """Temporal filter: upcoming, today, this_week."""

    def test_upcoming_filter(self):
        user = _create_test_user("tmpup")
        cat_ids = _get_category_ids(1)
        future_event = _create_published_event(user["id"], cat_ids, title="Future Event", days_from_now=10)

        resp = client.get("/events?quick_filter=upcoming")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert future_event["id"] in ids

        _cleanup_event(future_event["id"])
        _cleanup_user(user["id"])

    def test_today_filter(self):
        resp = client.get("/events?quick_filter=today")
        assert resp.status_code == 200
        data = resp.json()
        # All returned events must start today (UTC)
        today = datetime.now(UTC).date()
        for item in data["items"]:
            start = datetime.fromisoformat(item["start_datetime"].replace("Z", "+00:00"))
            assert start.date() == today

    def test_this_week_filter(self):
        user = _create_test_user("tmpwk")
        cat_ids = _get_category_ids(1)
        event = _create_published_event(user["id"], cat_ids, title="This Week Event", days_from_now=3)

        resp = client.get("/events?quick_filter=this_week")
        assert resp.status_code == 200
        data = resp.json()
        ids = [i["id"] for i in data["items"]]
        assert event["id"] in ids

        _cleanup_event(event["id"])
        _cleanup_user(user["id"])

    def test_this_week_excludes_far_future(self):
        user = _create_test_user("tmpwkfar")
        cat_ids = _get_category_ids(1)
        far_event = _create_published_event(user["id"], cat_ids, title="Far Future Event", days_from_now=30)

        resp = client.get("/events?quick_filter=this_week")
        ids = [i["id"] for i in resp.json()["items"]]
        assert far_event["id"] not in ids

        _cleanup_event(far_event["id"])
        _cleanup_user(user["id"])

    def test_invalid_temporal_filter_rejected(self):
        resp = client.get("/events?quick_filter=yesterday")
        assert resp.status_code == 422


class TestListEventsPagination:
    """Pagination: page, page_size, total, total_pages."""

    def test_default_pagination(self):
        resp = client.get("/events")
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 20

    def test_custom_page_size(self):
        resp = client.get("/events?page_size=5")
        data = resp.json()
        assert data["page_size"] == 5
        assert len(data["items"]) <= 5

    def test_page_size_max_100(self):
        resp = client.get("/events?page_size=101")
        assert resp.status_code == 422

    def test_page_size_min_1(self):
        resp = client.get("/events?page_size=0")
        assert resp.status_code == 422

    def test_pagination_second_page(self):
        user = _create_test_user("paginate")
        cat_ids = _get_category_ids(1)
        events = [
            _create_published_event(user["id"], cat_ids, title=f"Page Event {i}", days_from_now=i + 1)
            for i in range(3)
        ]

        resp1 = client.get("/events?page=1&page_size=2")
        resp2 = client.get("/events?page=2&page_size=2")
        data1 = resp1.json()
        data2 = resp2.json()

        assert data1["page"] == 1
        assert data2["page"] == 2
        ids1 = {i["id"] for i in data1["items"]}
        ids2 = {i["id"] for i in data2["items"]}
        # No overlap between pages
        assert ids1.isdisjoint(ids2)

        for e in events:
            _cleanup_event(e["id"])
        _cleanup_user(user["id"])

    def test_total_pages_calculation(self):
        resp = client.get("/events?page_size=1")
        data = resp.json()
        if data["total"] > 0:
            assert data["total_pages"] == data["total"]

    def test_empty_page_beyond_total(self):
        resp = client.get("/events?page=9999&page_size=20")
        data = resp.json()
        assert resp.status_code == 200
        assert data["items"] == []

    def test_invalid_page_rejected(self):
        resp = client.get("/events?page=0")
        assert resp.status_code == 422


class TestListEventsCombinedFilters:
    """Search + category + temporal combined."""

    def test_search_and_category_combined(self):
        user = _create_test_user("combined")
        cat_ids = _get_category_ids(2)
        if len(cat_ids) < 2:
            return

        cat_a, cat_b = cat_ids[0], cat_ids[1]
        unique = uuid.uuid4().hex[:6]
        ev_match = _create_published_event(user["id"], [cat_a], title=f"Combo{unique}")
        ev_wrong_cat = _create_published_event(user["id"], [cat_b], title=f"Combo{unique}")
        ev_wrong_title = _create_published_event(user["id"], [cat_a], title="Different")

        resp = client.get(f"/events?search=Combo{unique}&category_id={cat_a}")
        ids = [i["id"] for i in resp.json()["items"]]
        assert ev_match["id"] in ids
        assert ev_wrong_cat["id"] not in ids
        assert ev_wrong_title["id"] not in ids

        for e in (ev_match, ev_wrong_cat, ev_wrong_title):
            _cleanup_event(e["id"])
        _cleanup_user(user["id"])

    def test_search_and_temporal_combined(self):
        user = _create_test_user("srchtmp")
        cat_ids = _get_category_ids(1)
        unique = uuid.uuid4().hex[:6]
        ev_near = _create_published_event(user["id"], cat_ids, title=f"SrchTmp{unique}", days_from_now=3)
        ev_far = _create_published_event(user["id"], cat_ids, title=f"SrchTmp{unique}", days_from_now=30)

        resp = client.get(f"/events?search=SrchTmp{unique}&quick_filter=this_week")
        ids = [i["id"] for i in resp.json()["items"]]
        assert ev_near["id"] in ids
        assert ev_far["id"] not in ids

        _cleanup_event(ev_near["id"])
        _cleanup_event(ev_far["id"])
        _cleanup_user(user["id"])

    def test_all_filters_combined(self):
        user = _create_test_user("allfilt")
        cat_ids = _get_category_ids(2)
        if len(cat_ids) < 2:
            return

        cat_a, cat_b = cat_ids[0], cat_ids[1]
        unique = uuid.uuid4().hex[:6]
        ev_target = _create_published_event(user["id"], [cat_a], title=f"AllFilt{unique}", days_from_now=2)
        ev_wrong_cat = _create_published_event(user["id"], [cat_b], title=f"AllFilt{unique}", days_from_now=2)
        ev_far = _create_published_event(user["id"], [cat_a], title=f"AllFilt{unique}", days_from_now=20)

        resp = client.get(f"/events?search=AllFilt{unique}&category_id={cat_a}&quick_filter=this_week&page=1&page_size=10")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert ev_target["id"] in ids
        assert ev_wrong_cat["id"] not in ids
        assert ev_far["id"] not in ids

        for e in (ev_target, ev_wrong_cat, ev_far):
            _cleanup_event(e["id"])
        _cleanup_user(user["id"])


class TestListEventsNewQuickFilters:
    """Quick filters added in final-milestone discovery (now / past / weekend)."""

    def test_past_filter_returns_ended_events(self):
        """quick_filter=past returns events whose end_datetime has passed."""
        user = _create_test_user("pastflt")
        cat_ids = _get_category_ids(1)
        # Direct DB insert to backdate end_datetime
        from datetime import UTC, datetime, timedelta
        result = db.table("events").insert({
            "host_id": user["id"],
            "title": "Past Filter Event",
            "description": "ended",
            "start_datetime": (datetime.now(UTC) - timedelta(days=2)).isoformat(),
            "end_datetime": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "visibility": "public",
            "status": "ended",
            "is_age_restricted": False,
            "attendee_count": 0,
        }).execute()
        ev_id = result.data[0]["id"]
        db.table("event_categories").insert({"event_id": ev_id, "category_id": cat_ids[0]}).execute()

        resp = client.get("/events?quick_filter=past")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert ev_id in ids

        # And the past event is NOT in default listing
        resp_default = client.get("/events")
        default_ids = [i["id"] for i in resp_default.json()["items"]]
        assert ev_id not in default_ids

        _cleanup_event(ev_id)
        _cleanup_user(user["id"])

    def test_now_filter_returns_currently_running(self):
        """quick_filter=now returns events where start <= now <= end."""
        user = _create_test_user("nowflt")
        cat_ids = _get_category_ids(1)
        from datetime import UTC, datetime, timedelta
        # Currently running event
        running = db.table("events").insert({
            "host_id": user["id"],
            "title": "Now Running",
            "description": "running",
            "start_datetime": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "end_datetime": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            "visibility": "public",
            "status": "published",
            "is_age_restricted": False,
            "attendee_count": 0,
        }).execute().data[0]
        db.table("event_categories").insert({"event_id": running["id"], "category_id": cat_ids[0]}).execute()
        # Future event (should not appear under "now")
        future = _create_published_event(user["id"], cat_ids, title="Future", days_from_now=3)

        resp = client.get("/events?quick_filter=now")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert running["id"] in ids
        assert future["id"] not in ids

        _cleanup_event(running["id"])
        _cleanup_event(future["id"])
        _cleanup_user(user["id"])


class TestListEventsCustomWindow:
    """start_after / end_before custom time window."""

    def test_quick_filter_mutex_with_custom_window(self):
        resp = client.get("/events?quick_filter=today&start_after=2030-01-01T00:00:00Z")
        assert resp.status_code == 422

    def test_start_after_filters_earlier_events(self):
        user = _create_test_user("after")
        cat_ids = _get_category_ids(1)
        ev_soon = _create_published_event(user["id"], cat_ids, title="Soon", days_from_now=1)
        ev_far = _create_published_event(user["id"], cat_ids, title="Far", days_from_now=10)

        cutoff = (datetime.now(UTC) + timedelta(days=5)).isoformat()
        resp = client.get("/events", params={"start_after": cutoff})
        assert resp.status_code == 200, resp.text
        ids = [i["id"] for i in resp.json()["items"]]
        assert ev_soon["id"] not in ids
        assert ev_far["id"] in ids

        _cleanup_event(ev_soon["id"])
        _cleanup_event(ev_far["id"])
        _cleanup_user(user["id"])

    def test_start_after_must_be_before_end_before(self):
        resp = client.get(
            "/events?start_after=2030-12-31T00:00:00Z&end_before=2030-01-01T00:00:00Z"
        )
        assert resp.status_code == 422


class TestListEventsAccessibility:
    """Accessibility filtering against venue_metadata."""

    def test_wheelchair_filter(self):
        user = _create_test_user("acca11y")
        cat_ids = _get_category_ids(1)
        ev_with = _create_published_event(user["id"], cat_ids, title="A11y Yes", days_from_now=2)
        ev_without = _create_published_event(user["id"], cat_ids, title="A11y No", days_from_now=2)
        # Insert venue metadata with wheelchair=true on one event
        db.table("venue_metadata").insert({
            "event_id": ev_with["id"],
            "wheelchair_access": True,
            "accessible_restroom": False,
            "elevator_available": False,
            "seating_available": False,
            "captions_support": False,
            "quiet_friendly": False,
        }).execute()

        resp = client.get("/events?wheelchair=true")
        ids = [i["id"] for i in resp.json()["items"]]
        assert ev_with["id"] in ids
        assert ev_without["id"] not in ids

        _cleanup_event(ev_with["id"])
        _cleanup_event(ev_without["id"])
        _cleanup_user(user["id"])


class TestListEventsLocation:
    """near_lat/near_lng/radius_km bounding-box and distance sort."""

    def test_near_lat_without_lng_rejected(self):
        resp = client.get("/events?near_lat=41.0")
        assert resp.status_code == 422

    def test_radius_without_location_rejected(self):
        resp = client.get("/events?radius_km=10")
        assert resp.status_code == 422

    def test_distance_sort_without_location_rejected(self):
        resp = client.get("/events?sort=distance")
        assert resp.status_code == 422

    def test_bounding_box_filter(self):
        user = _create_test_user("bbox")
        cat_ids = _get_category_ids(1)
        # Istanbul at (41.0, 29.0). _create_published_event uses these coords by default.
        ev_near = _create_published_event(user["id"], cat_ids, title="Near", days_from_now=2)
        # Override another event's location to a very distant place (Tokyo)
        ev_far = _create_published_event(user["id"], cat_ids, title="Far", days_from_now=2)
        db.table("event_locations").update({"latitude": 35.68, "longitude": 139.69}).eq("event_id", ev_far["id"]).execute()

        resp = client.get("/events?near_lat=41.0&near_lng=29.0&radius_km=100")
        ids = [i["id"] for i in resp.json()["items"]]
        assert ev_near["id"] in ids
        assert ev_far["id"] not in ids

        _cleanup_event(ev_near["id"])
        _cleanup_event(ev_far["id"])
        _cleanup_user(user["id"])

    def test_distance_sort_orders_closer_first(self):
        user = _create_test_user("distsort")
        cat_ids = _get_category_ids(1)
        ev_close = _create_published_event(user["id"], cat_ids, title="Close", days_from_now=2)
        ev_medium = _create_published_event(user["id"], cat_ids, title="Medium", days_from_now=2)
        # Move medium event ~30km away (still inside default 50km radius)
        db.table("event_locations").update({"latitude": 41.27, "longitude": 29.0}).eq("event_id", ev_medium["id"]).execute()

        resp = client.get("/events?near_lat=41.0&near_lng=29.0&sort=distance")
        ids = [i["id"] for i in resp.json()["items"]]
        # close before medium
        if ev_close["id"] in ids and ev_medium["id"] in ids:
            assert ids.index(ev_close["id"]) < ids.index(ev_medium["id"])

        _cleanup_event(ev_close["id"])
        _cleanup_event(ev_medium["id"])
        _cleanup_user(user["id"])


class TestListEventsDefaultArea:
    """use_default_area falls back to authenticated user's stored profile lat/lng."""

    def test_default_area_requires_auth(self):
        resp = client.get("/events?use_default_area=true")
        assert resp.status_code == 422

    def test_default_area_requires_stored_default(self):
        user = _create_test_user("nodefault")
        # User has no default_location_* set
        resp = client.get("/events?use_default_area=true", headers=_auth_header(user["id"]))
        assert resp.status_code == 422
        _cleanup_user(user["id"])

    def test_default_area_used_when_no_explicit_coords(self):
        user = _create_test_user("withdef")
        db.table("users").update({
            "default_location_name": "Istanbul",
            "default_location_lat": 41.0,
            "default_location_lng": 29.0,
        }).eq("id", user["id"]).execute()
        cat_ids = _get_category_ids(1)
        ev_near = _create_published_event(user["id"], cat_ids, title="DefArea", days_from_now=2)

        resp = client.get(
            "/events?use_default_area=true&radius_km=100",
            headers=_auth_header(user["id"]),
        )
        assert resp.status_code == 200, resp.text
        ids = [i["id"] for i in resp.json()["items"]]
        assert ev_near["id"] in ids

        _cleanup_event(ev_near["id"])
        _cleanup_user(user["id"])


class TestListEventsCaptionsRename:
    """The accessibility filter previously named `sign_language` is now `captions`.

    The old name was misleading — captions and sign-language interpretation
    are different features and the underlying DB column is `captions_support`.
    """

    def test_captions_filter_matches_captions_support_column(self):
        user = _create_test_user("captions")
        cat_ids = _get_category_ids(1)
        ev_with = _create_published_event(user["id"], cat_ids, title="WithCaptions", days_from_now=2)
        ev_without = _create_published_event(user["id"], cat_ids, title="NoCaptions", days_from_now=2)
        db.table("venue_metadata").insert({
            "event_id": ev_with["id"],
            "wheelchair_access": False,
            "accessible_restroom": False,
            "elevator_available": False,
            "seating_available": False,
            "captions_support": True,
            "quiet_friendly": False,
        }).execute()

        resp = client.get("/events?captions=true")
        assert resp.status_code == 200, resp.text
        ids = [i["id"] for i in resp.json()["items"]]
        assert ev_with["id"] in ids
        assert ev_without["id"] not in ids

        _cleanup_event(ev_with["id"])
        _cleanup_event(ev_without["id"])
        _cleanup_user(user["id"])

    def test_old_sign_language_param_no_longer_filters(self):
        """sign_language is no longer a recognised query parameter; passing it
        is silently ignored by FastAPI rather than rejected, but it must not
        accidentally apply the captions filter (the misleading old behaviour)."""
        user = _create_test_user("oldsl")
        cat_ids = _get_category_ids(1)
        ev = _create_published_event(user["id"], cat_ids, title="StillVisible", days_from_now=2)
        # Insert venue metadata with captions_support=False so if sign_language
        # were still mapping to captions_support, this event would be excluded.
        db.table("venue_metadata").insert({
            "event_id": ev["id"],
            "wheelchair_access": False,
            "accessible_restroom": False,
            "elevator_available": False,
            "seating_available": False,
            "captions_support": False,
            "quiet_friendly": False,
        }).execute()

        resp = client.get("/events?sign_language=true")
        assert resp.status_code == 200, resp.text
        ids = [i["id"] for i in resp.json()["items"]]
        assert ev["id"] in ids

        _cleanup_event(ev["id"])
        _cleanup_user(user["id"])


class TestListEventsCategorySort:
    """sort=category requires a narrowing filter to keep memory bounded."""

    def test_sort_category_without_narrowing_filter_rejected(self):
        resp = client.get("/events?sort=category")
        assert resp.status_code == 422
        assert "narrowing filter" in resp.json()["detail"].lower()

    def test_sort_category_accepted_with_search(self):
        user = _create_test_user("catsearch")
        cat_ids = _get_category_ids(1)
        ev = _create_published_event(user["id"], cat_ids, title="UniqueCatSortTitle", days_from_now=2)

        resp = client.get("/events?sort=category&search=UniqueCatSortTitle")
        assert resp.status_code == 200, resp.text
        ids = [i["id"] for i in resp.json()["items"]]
        assert ev["id"] in ids

        _cleanup_event(ev["id"])
        _cleanup_user(user["id"])

    def test_sort_category_accepted_with_quick_filter(self):
        resp = client.get("/events?sort=category&quick_filter=upcoming")
        assert resp.status_code == 200, resp.text

    def test_sort_category_accepted_with_category_id(self):
        cat_ids = _get_category_ids(1)
        resp = client.get(f"/events?sort=category&category_id={cat_ids[0]}")
        assert resp.status_code == 200, resp.text

    def test_sort_category_accepted_with_location(self):
        resp = client.get("/events?sort=category&near_lat=41.0&near_lng=29.0")
        assert resp.status_code == 200, resp.text

    def test_sort_category_accepted_with_accessibility(self):
        resp = client.get("/events?sort=category&wheelchair=true")
        assert resp.status_code == 200, resp.text

    def test_sort_category_orders_alphabetically(self):
        user = _create_test_user("catorder")
        cat_ids = _get_category_ids(1)
        # Same category bucket → tiebreaker on start_datetime
        ev_first = _create_published_event(user["id"], cat_ids, title="ZZZcatA", days_from_now=2)
        ev_second = _create_published_event(user["id"], cat_ids, title="ZZZcatB", days_from_now=3)

        # Use search to satisfy the narrowing-filter requirement.
        resp = client.get("/events?sort=category&search=ZZZcat")
        assert resp.status_code == 200, resp.text
        ids = [i["id"] for i in resp.json()["items"]]
        if ev_first["id"] in ids and ev_second["id"] in ids:
            # Same category → start_datetime tiebreaker → ev_first earlier
            assert ids.index(ev_first["id"]) < ids.index(ev_second["id"])

        _cleanup_event(ev_first["id"])
        _cleanup_event(ev_second["id"])
        _cleanup_user(user["id"])
