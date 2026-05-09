"""Unit tests for `services.event` read-side (Phase 1 slice C).

Targets get_event_detail, list_events, list_events_geojson, get_similar_events
with mocked repo modules through the keyword-default DI seam. Focuses on
visibility/age-gate branches for detail, the 422 error branches and
sort-rank delegation for list_events, point-projection for the geojson
adapter, and the scoring logic for similar events.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services import event as event_service

HOST_ID = "00000000-0000-0000-0000-0000000000a0"
OTHER_USER = "00000000-0000-0000-0000-0000000000b0"
EVENT_ID = "00000000-0000-0000-0000-0000000000a1"
EVENT_ID_2 = "00000000-0000-0000-0000-0000000000a2"
CAT_A = "00000000-0000-0000-0000-0000000000a3"
CAT_B = "00000000-0000-0000-0000-0000000000a4"


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


@pytest.fixture
def events_repo():
    m = MagicMock(name="event_repo")
    m.get_event_categories.return_value = []
    m.get_event_locations.return_value = []
    m.get_event_images.return_value = []
    m.get_venue_metadata.return_value = None
    m.get_equipment.return_value = []
    m.get_event_segments.return_value = []
    m.get_primary_locations_for_events.return_value = {}
    m.get_categories_for_events.return_value = {}
    m.get_primary_images_for_events.return_value = {}
    return m


@pytest.fixture
def users_repo():
    m = MagicMock(name="user_repo")
    m.get_user_by_id.return_value = {"id": HOST_ID, "username": "alice"}
    m.get_user_email_by_id.return_value = "alice@example.com"
    m.get_users_by_ids.return_value = []
    m.get_user_default_area.return_value = (None, None)
    return m


@pytest.fixture
def bookmarks_repo():
    m = MagicMock(name="bookmark_repo")
    m.get_bookmark.return_value = None
    m.get_bookmark_count_for_event.return_value = 0
    m.get_bookmark_counts_for_events.return_value = {}
    m.get_bookmark_status_for_events.return_value = set()
    return m


@pytest.fixture
def attendances_repo():
    m = MagicMock(name="attendance_repo")
    m.get_attendance.return_value = None
    m.get_going_user_ids_for_event.return_value = []
    m.get_attendance_status_for_events.return_value = {}
    m.get_attended_ended_event_categories.return_value = set()
    return m


@pytest.fixture
def invites_repo():
    m = MagicMock(name="invite_repo")
    m.get_access_request.return_value = None
    m.get_access_grant.return_value = None
    m.get_access_request_status_for_events.return_value = {}
    m.get_access_granted_event_ids.return_value = set()
    return m


def _stub_event(**overrides) -> dict:
    base = {
        "id": EVENT_ID,
        "host_id": HOST_ID,
        "title": "Festival",
        "description": "fun",
        "start_datetime": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
        "end_datetime": (datetime.now(UTC) + timedelta(hours=26)).isoformat(),
        "visibility": "public",
        "is_age_restricted": False,
        "attendee_limit": None,
        "attendee_count": 0,
        "status": "published",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def _all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
    return {
        "events": events_repo,
        "users": users_repo,
        "bookmarks": bookmarks_repo,
        "attendances": attendances_repo,
        "invites": invites_repo,
    }


# ── get_event_detail ────────────────────────────────────────────────────────


class TestGetEventDetail:
    def test_404_when_missing(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        events_repo.get_event_by_id.return_value = None
        with pytest.raises(HTTPException) as exc:
            event_service.get_event_detail(
                db, EVENT_ID, None,
                **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
            )
        assert exc.value.status_code == 404

    def test_404_for_draft_to_non_host(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        events_repo.get_event_by_id.return_value = _stub_event(status="draft")
        with pytest.raises(HTTPException) as exc:
            event_service.get_event_detail(
                db, EVENT_ID, OTHER_USER,
                **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
            )
        assert exc.value.status_code == 404

    def test_guest_gets_limited_response(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        events_repo.get_event_by_id.return_value = _stub_event()
        events_repo.get_event_categories.return_value = [
            {"id": CAT_A, "name": "music", "is_predefined": True, "is_approved": True},
        ]

        resp = event_service.get_event_detail(
            db, EVENT_ID, None,
            **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
        )

        # Limited responses don't carry locations/images/attendees
        assert not hasattr(resp, "attendees") or resp.__class__.__name__ == "EventLimitedResponse"
        assert resp.__class__.__name__ == "EventLimitedResponse"

    def test_cancelled_returns_limited_for_non_host(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        events_repo.get_event_by_id.return_value = _stub_event(status="cancelled")
        events_repo.get_event_categories.return_value = []

        resp = event_service.get_event_detail(
            db, EVENT_ID, OTHER_USER,
            **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
        )

        assert resp.__class__.__name__ == "EventLimitedResponse"

    def test_private_event_non_host_no_grant_returns_limited(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        events_repo.get_event_by_id.return_value = _stub_event(visibility="private")
        invites_repo.get_access_grant.return_value = None
        events_repo.get_event_categories.return_value = []

        resp = event_service.get_event_detail(
            db, EVENT_ID, OTHER_USER,
            **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
        )

        assert resp.__class__.__name__ == "EventLimitedResponse"

    def test_age_restricted_403_for_underage(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        events_repo.get_event_by_id.return_value = _stub_event(is_age_restricted=True)
        # 17 years 364 days old → strictly under 18
        underage_dob = (datetime.now(UTC).date() - timedelta(days=17 * 365 + 100)).isoformat()
        users_repo.get_user_date_of_birth.return_value = underage_dob

        with pytest.raises(HTTPException) as exc:
            event_service.get_event_detail(
                db, EVENT_ID, OTHER_USER,
                **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
            )
        assert exc.value.status_code == 403

    def test_age_restricted_403_when_dob_missing(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        events_repo.get_event_by_id.return_value = _stub_event(is_age_restricted=True)
        users_repo.get_user_date_of_birth.return_value = None

        with pytest.raises(HTTPException) as exc:
            event_service.get_event_detail(
                db, EVENT_ID, OTHER_USER,
                **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
            )
        assert exc.value.status_code == 403

    def test_host_gets_full_detail(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        events_repo.get_event_by_id.return_value = _stub_event()
        events_repo.get_event_categories.return_value = []

        resp = event_service.get_event_detail(
            db, EVENT_ID, HOST_ID,
            **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
        )

        assert resp.__class__.__name__ == "EventDetailResponse"
        events_repo.get_event_locations.assert_called_once()
        events_repo.get_event_images.assert_called_once()


# ── list_events ─────────────────────────────────────────────────────────────


class TestListEvents:
    def test_422_when_sort_distance_without_location(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        with pytest.raises(HTTPException) as exc:
            event_service.list_events(
                db,
                sort="distance",
                **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
            )
        assert exc.value.status_code == 422

    def test_422_when_use_default_area_without_saved_coords(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        users_repo.get_user_default_area.return_value = (None, None)
        with pytest.raises(HTTPException) as exc:
            event_service.list_events(
                db,
                user_id=HOST_ID,
                use_default_area=True,
                **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
            )
        assert exc.value.status_code == 422

    def test_resolves_default_area_when_saved(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        users_repo.get_user_default_area.return_value = (41.0, 29.0)
        events_repo.list_events.return_value = ([], 0)

        event_service.list_events(
            db,
            user_id=HOST_ID,
            use_default_area=True,
            **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
        )

        sent = events_repo.list_events.call_args.kwargs
        assert sent["near_lat"] == 41.0
        assert sent["near_lng"] == 29.0

    def test_empty_result_returns_empty_response(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        events_repo.list_events.return_value = ([], 0)

        resp = event_service.list_events(
            db,
            **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
        )

        assert resp.items == []
        assert resp.total == 0
        assert resp.total_pages == 0

    def test_suggested_fallback_when_no_attendance_history(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        attendances_repo.get_attended_ended_event_categories.return_value = set()
        events_repo.list_events.return_value = ([], 0)

        resp = event_service.list_events(
            db,
            user_id=HOST_ID,
            suggested=True,
            **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
        )

        assert resp.suggested_fallback is True

    def test_distance_sort_orders_closer_first_in_memory(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        # Closer event must appear before farther one in the response items.
        far = _stub_event(id=EVENT_ID)
        close = _stub_event(id=EVENT_ID_2)
        events_repo.list_events.return_value = ([far, close], 2)
        events_repo.get_primary_locations_for_events.return_value = {
            EVENT_ID: {
                "id": "00000000-0000-0000-0000-0000000000d0",
                "name": "far", "latitude": 41.5, "longitude": 29.5,
                "is_primary": True, "order_index": 0,
            },
            EVENT_ID_2: {
                "id": "00000000-0000-0000-0000-0000000000d1",
                "name": "close", "latitude": 41.0, "longitude": 29.0,
                "is_primary": True, "order_index": 0,
            },
        }

        resp = event_service.list_events(
            db,
            near_lat=41.0,
            near_lng=29.0,
            sort="distance",
            **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
        )

        assert [str(item.id) for item in resp.items] == [EVENT_ID_2, EVENT_ID]

    def test_private_event_description_redacted_in_listing(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        priv = _stub_event(id=EVENT_ID, visibility="private")
        events_repo.list_events.return_value = ([priv], 1)

        resp = event_service.list_events(
            db,
            user_id=HOST_ID,
            **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
        )

        assert resp.items[0].description is None

    def test_host_sees_has_access_true_for_own_event(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        own = _stub_event(id=EVENT_ID, host_id=HOST_ID, visibility="private")
        events_repo.list_events.return_value = ([own], 1)

        resp = event_service.list_events(
            db,
            user_id=HOST_ID,
            **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
        )

        assert resp.items[0].has_access is True


# ── list_events_geojson ─────────────────────────────────────────────────────


class TestListEventsGeoJSON:
    def test_drops_items_without_location(self, db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
        # Two events; only one has a primary location → only one feature.
        events_repo.list_events.return_value = (
            [
                _stub_event(id=EVENT_ID),
                _stub_event(id=EVENT_ID_2),
            ],
            2,
        )
        events_repo.get_primary_locations_for_events.return_value = {
            EVENT_ID: {
                "id": "00000000-0000-0000-0000-0000000000d0",
                "name": "x",
                "latitude": 41.0,
                "longitude": 29.0,
                "is_primary": True,
                "order_index": 0,
            },
        }

        result = event_service.list_events_geojson(
            db,
            **_all(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
        )

        assert len(result.features) == 1
        feature = result.features[0]
        # GeoJSON spec ordering: [lng, lat]
        assert feature.geometry.coordinates == [29.0, 41.0]


# ── get_similar_events ──────────────────────────────────────────────────────


class TestGetSimilarEvents:
    def test_404_when_source_missing(self, db, events_repo, bookmarks_repo, invites_repo):
        events_repo.get_event_by_id.return_value = None
        with pytest.raises(HTTPException) as exc:
            event_service.get_similar_events(
                db, EVENT_ID,
                events=events_repo, bookmarks=bookmarks_repo, invites=invites_repo,
            )
        assert exc.value.status_code == 404

    def test_returns_empty_when_no_candidates(self, db, events_repo, bookmarks_repo, invites_repo):
        events_repo.get_event_by_id.return_value = _stub_event()
        events_repo.get_event_categories.return_value = []
        events_repo.get_similar_candidates.return_value = []

        result = event_service.get_similar_events(
            db, EVENT_ID,
            events=events_repo, bookmarks=bookmarks_repo, invites=invites_repo,
        )

        assert result == []

    def test_scoring_ranks_by_category_overlap(self, db, events_repo, bookmarks_repo, invites_repo):
        source = _stub_event(id=EVENT_ID)
        events_repo.get_event_by_id.return_value = source
        events_repo.get_event_categories.return_value = [
            {"id": CAT_A, "name": "music", "is_predefined": True, "is_approved": True},
            {"id": CAT_B, "name": "art", "is_predefined": True, "is_approved": True},
        ]

        # Candidate 1: 0 overlap; Candidate 2: 2 overlaps. Cand 2 must rank higher.
        cand1 = _stub_event(id=EVENT_ID_2, host_id=OTHER_USER)
        cand2_id = "00000000-0000-0000-0000-0000000000c0"
        cand2 = _stub_event(id=cand2_id, host_id=OTHER_USER)
        events_repo.get_similar_candidates.return_value = [cand1, cand2]
        events_repo.get_categories_for_events.side_effect = [
            # First call: scoring lookup for both candidates
            {EVENT_ID_2: [], cand2_id: [
                {"id": CAT_A, "name": "music", "is_predefined": True, "is_approved": True},
                {"id": CAT_B, "name": "art", "is_predefined": True, "is_approved": True},
            ]},
        ]
        # Source location lookup + later top_ids lookup
        events_repo.get_primary_locations_for_events.return_value = {}
        events_repo.get_primary_images_for_events.return_value = {}

        result = event_service.get_similar_events(
            db, EVENT_ID,
            events=events_repo, bookmarks=bookmarks_repo, invites=invites_repo,
        )

        # Higher-overlap candidate ranks first.
        assert str(result[0].id) == cand2_id
        assert str(result[1].id) == EVENT_ID_2

    def test_limit_caps_results(self, db, events_repo, bookmarks_repo, invites_repo):
        source = _stub_event(id=EVENT_ID)
        events_repo.get_event_by_id.return_value = source
        events_repo.get_event_categories.return_value = []

        candidates = [
            _stub_event(id=f"00000000-0000-0000-0000-{i:012x}", host_id=OTHER_USER)
            for i in range(10)
        ]
        events_repo.get_similar_candidates.return_value = candidates
        events_repo.get_categories_for_events.return_value = {c["id"]: [] for c in candidates}
        events_repo.get_primary_locations_for_events.return_value = {}
        events_repo.get_primary_images_for_events.return_value = {}

        result = event_service.get_similar_events(
            db, EVENT_ID, limit=3,
            events=events_repo, bookmarks=bookmarks_repo, invites=invites_repo,
        )

        assert len(result) == 3
