"""Unit tests for attendance.get_my_going_events service function.

All DB calls are mocked — no network/Supabase required.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.attendance import get_my_going_events

USER_ID = str(uuid4())


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


def _event(event_id: str | None = None, host_id: str | None = None) -> dict:
    now = datetime.now(UTC)
    eid = event_id or str(uuid4())
    return {
        "id": eid,
        "host_id": host_id or str(uuid4()),
        "title": f"Event {eid[:8]}",
        "description": "desc",
        "start_datetime": (now + timedelta(days=1)).isoformat(),
        "end_datetime": (now + timedelta(days=1, hours=2)).isoformat(),
        "visibility": "public",
        "is_age_restricted": False,
        "attendee_limit": None,
        "attendee_count": 3,
        "status": "published",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }


@pytest.fixture
def attendances_repo():
    m = MagicMock(name="attendance_repo")
    m.get_going_event_ids_for_user.return_value = []
    return m


@pytest.fixture
def events_repo():
    m = MagicMock(name="event_repo")
    m.get_events_by_ids.return_value = []
    m.get_categories_for_events.return_value = {}
    m.get_primary_locations_for_events.return_value = {}
    m.get_primary_images_for_events.return_value = {}
    return m


class TestGetMyGoingEvents:
    def test_returns_empty_when_no_going_events(self, db, attendances_repo, events_repo):
        attendances_repo.get_going_event_ids_for_user.return_value = []

        result = get_my_going_events(db, USER_ID, attendances=attendances_repo, events=events_repo)

        assert result == []
        events_repo.get_events_by_ids.assert_not_called()

    def test_returns_event_list_response_items(self, db, attendances_repo, events_repo):
        ev = _event()
        attendances_repo.get_going_event_ids_for_user.return_value = [ev["id"]]
        events_repo.get_events_by_ids.return_value = [ev]

        result = get_my_going_events(db, USER_ID, attendances=attendances_repo, events=events_repo)

        assert len(result) == 1
        assert str(result[0].id) == ev["id"]
        assert result[0].title == ev["title"]

    def test_attendance_status_is_going(self, db, attendances_repo, events_repo):
        ev = _event()
        attendances_repo.get_going_event_ids_for_user.return_value = [ev["id"]]
        events_repo.get_events_by_ids.return_value = [ev]

        result = get_my_going_events(db, USER_ID, attendances=attendances_repo, events=events_repo)

        assert result[0].attendance_status == "going"

    def test_multiple_events_order_preserved(self, db, attendances_repo, events_repo):
        ev1, ev2, ev3 = _event(), _event(), _event()
        ordered_ids = [ev1["id"], ev2["id"], ev3["id"]]
        attendances_repo.get_going_event_ids_for_user.return_value = ordered_ids
        # Repo returns in same order (get_events_by_ids preserves input order)
        events_repo.get_events_by_ids.return_value = [ev1, ev2, ev3]

        result = get_my_going_events(db, USER_ID, attendances=attendances_repo, events=events_repo)

        assert [str(r.id) for r in result] == ordered_ids

    def test_bookmarked_event_reflected(self, db, attendances_repo, events_repo):
        ev = _event()
        attendances_repo.get_going_event_ids_for_user.return_value = [ev["id"]]
        events_repo.get_events_by_ids.return_value = [ev]

        from unittest.mock import patch
        with patch(
            "app.repositories.bookmark.get_bookmark_status_for_events",
            return_value={ev["id"]},
        ):
            result = get_my_going_events(db, USER_ID, attendances=attendances_repo, events=events_repo)

        assert result[0].is_bookmarked is True

    def test_not_bookmarked_event_reflected(self, db, attendances_repo, events_repo):
        ev = _event()
        attendances_repo.get_going_event_ids_for_user.return_value = [ev["id"]]
        events_repo.get_events_by_ids.return_value = [ev]

        from unittest.mock import patch
        with patch(
            "app.repositories.bookmark.get_bookmark_status_for_events",
            return_value={},
        ):
            result = get_my_going_events(db, USER_ID, attendances=attendances_repo, events=events_repo)

        assert result[0].is_bookmarked is False

    def test_primary_location_included_when_available(self, db, attendances_repo, events_repo):
        ev = _event()
        loc = {
            "id": str(uuid4()),
            "name": "Main Stage",
            "latitude": 41.0,
            "longitude": 29.0,
            "is_primary": True,
            "order_index": 0,
            "location_address": None,
        }
        attendances_repo.get_going_event_ids_for_user.return_value = [ev["id"]]
        events_repo.get_events_by_ids.return_value = [ev]
        events_repo.get_primary_locations_for_events.return_value = {ev["id"]: loc}

        result = get_my_going_events(db, USER_ID, attendances=attendances_repo, events=events_repo)

        assert result[0].primary_location is not None
        assert result[0].primary_location.latitude == 41.0

    def test_no_location_gives_none(self, db, attendances_repo, events_repo):
        ev = _event()
        attendances_repo.get_going_event_ids_for_user.return_value = [ev["id"]]
        events_repo.get_events_by_ids.return_value = [ev]
        events_repo.get_primary_locations_for_events.return_value = {}

        result = get_my_going_events(db, USER_ID, attendances=attendances_repo, events=events_repo)

        assert result[0].primary_location is None

    def test_categories_attached_to_event(self, db, attendances_repo, events_repo):
        ev = _event()
        cat_id = str(uuid4())
        attendances_repo.get_going_event_ids_for_user.return_value = [ev["id"]]
        events_repo.get_events_by_ids.return_value = [ev]
        events_repo.get_categories_for_events.return_value = {
            ev["id"]: [{"id": cat_id, "name": "Music", "is_predefined": True, "is_approved": True}]
        }

        result = get_my_going_events(db, USER_ID, attendances=attendances_repo, events=events_repo)

        assert len(result[0].categories) == 1
        assert result[0].categories[0].name == "Music"

    def test_events_not_found_in_db_returns_empty(self, db, attendances_repo, events_repo):
        """get_going_event_ids_for_user returns IDs but get_events_by_ids returns empty
        (e.g. event was deleted). Should return empty list gracefully."""
        attendances_repo.get_going_event_ids_for_user.return_value = [str(uuid4())]
        events_repo.get_events_by_ids.return_value = []

        result = get_my_going_events(db, USER_ID, attendances=attendances_repo, events=events_repo)

        assert result == []
