"""Unit tests for the suggested_fallback / suggested_fallback_reason logic
in services.event.list_events.

Verifies the three cases:
  - no_history : user has never attended any ended event
  - no_match   : user has history but no current events match their categories
  - active     : suggestions are non-empty (reason is None)
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.services import event as event_service

USER_ID = str(uuid4())
EVENT_ID = str(uuid4())
CAT_ID = str(uuid4())


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


def _stub_event() -> dict:
    now = datetime.now(UTC)
    return {
        "id": EVENT_ID,
        "host_id": str(uuid4()),
        "title": "Test Event",
        "description": "desc",
        "start_datetime": (now + timedelta(hours=24)).isoformat(),
        "end_datetime": (now + timedelta(hours=26)).isoformat(),
        "visibility": "public",
        "is_age_restricted": False,
        "attendee_limit": None,
        "attendee_count": 0,
        "status": "published",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }


@pytest.fixture
def base_repos():
    events = MagicMock(name="event_repo")
    events.get_primary_locations_for_events.return_value = {}
    events.get_categories_for_events.return_value = {}
    events.get_primary_images_for_events.return_value = {}
    events.get_valid_category_ids.return_value = set()
    events.get_rate_limit_config.return_value = None
    events.count_events_by_host_since.return_value = 0

    bookmarks = MagicMock(name="bookmark_repo")
    bookmarks.get_bookmark_counts_for_events.return_value = {}
    bookmarks.get_bookmark_status_for_events.return_value = set()

    attendances = MagicMock(name="attendance_repo")
    attendances.get_attendance_status_for_events.return_value = {}
    attendances.get_attended_ended_event_categories.return_value = set()

    invites = MagicMock(name="invite_repo")
    invites.get_access_request_status_for_events.return_value = {}
    invites.get_access_granted_event_ids.return_value = set()

    users = MagicMock(name="user_repo")
    users.get_user_default_area.return_value = (None, None)

    return {
        "events": events,
        "bookmarks": bookmarks,
        "attendances": attendances,
        "invites": invites,
        "users": users,
    }


class TestSuggestedFallbackReason:
    def test_no_history_when_user_has_no_attended_categories(self, db, base_repos):
        """User never attended any ended event → fallback=True, reason='no_history'."""
        base_repos["attendances"].get_attended_ended_event_categories.return_value = set()
        base_repos["events"].list_events.return_value = ([], 0)

        result = event_service.list_events(
            db,
            suggested=True,
            user_id=USER_ID,
            **base_repos,
        )

        assert result.suggested_fallback is True
        assert result.suggested_fallback_reason == "no_history"

    def test_no_match_when_history_exists_but_no_events_returned(self, db, base_repos):
        """User attended events, cluster expansion ran, but zero events matched."""
        base_repos["attendances"].get_attended_ended_event_categories.return_value = {CAT_ID}
        base_repos["events"].list_events.return_value = ([], 0)

        with patch(
            "app.services.event._expand_suggested_category_ids",
            return_value={CAT_ID, str(uuid4())},
        ):
            result = event_service.list_events(
                db,
                suggested=True,
                user_id=USER_ID,
                **base_repos,
            )

        assert result.suggested_fallback is True
        assert result.suggested_fallback_reason == "no_match"

    def test_null_reason_when_suggestions_active(self, db, base_repos):
        """Normal suggestion flow — events returned, reason is None."""
        ev = _stub_event()
        base_repos["attendances"].get_attended_ended_event_categories.return_value = {CAT_ID}
        base_repos["events"].list_events.return_value = ([ev], 1)

        with patch(
            "app.services.event._expand_suggested_category_ids",
            return_value={CAT_ID},
        ):
            result = event_service.list_events(
                db,
                suggested=True,
                user_id=USER_ID,
                **base_repos,
            )

        assert result.suggested_fallback is False
        assert result.suggested_fallback_reason is None

    def test_fallback_not_set_when_suggested_is_false(self, db, base_repos):
        """When suggested=False, fallback fields are always False/None regardless
        of the user's attendance history."""
        ev = _stub_event()
        base_repos["events"].list_events.return_value = ([ev], 1)

        result = event_service.list_events(
            db,
            suggested=False,
            user_id=USER_ID,
            **base_repos,
        )

        assert result.suggested_fallback is False
        assert result.suggested_fallback_reason is None
        # Attendance history must NOT be queried when suggested=False
        base_repos["attendances"].get_attended_ended_event_categories.assert_not_called()

    def test_fallback_not_set_for_guest_user(self, db, base_repos):
        """Unauthenticated requests (user_id=None) never trigger suggested logic."""
        ev = _stub_event()
        base_repos["events"].list_events.return_value = ([ev], 1)

        result = event_service.list_events(
            db,
            suggested=True,
            user_id=None,
            **base_repos,
        )

        assert result.suggested_fallback is False
        assert result.suggested_fallback_reason is None
        base_repos["attendances"].get_attended_ended_event_categories.assert_not_called()
