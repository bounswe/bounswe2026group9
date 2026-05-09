"""Unit tests for `services.bookmark` — exercises the new keyword-DI seam.

These tests never touch a real database. They pass `MagicMock` repositories
through the `bookmarks=` and `events=` kwargs introduced in Phase 1 of the
testing roadmap. As more services are converted in subsequent commits a
matching `test_<service>_unit.py` will land alongside.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services import bookmark as bookmark_service

EVENT_ID = "00000000-0000-0000-0000-000000000001"
USER_ID = "00000000-0000-0000-0000-000000000002"
BOOKMARK_ID = "00000000-0000-0000-0000-000000000003"


@pytest.fixture
def fake_event() -> dict:
    return {
        "id": EVENT_ID,
        "title": "Test Event",
        "status": "published",
        "visibility": "public",
        "is_age_restricted": False,
        "start_datetime": "2026-06-01T10:00:00+00:00",
        "end_datetime": "2026-06-01T12:00:00+00:00",
    }


@pytest.fixture
def db():
    """Sentinel; the unit tests never use the client, only forward it."""
    return MagicMock(name="supabase_client")


# ── create_bookmark ──────────────────────────────────────────────────────────


class TestCreateBookmark:
    def test_inserts_bookmark_when_event_is_published(self, db, fake_event):
        events = MagicMock()
        events.get_event_by_id.return_value = fake_event
        bookmarks = MagicMock()
        bookmarks.get_bookmark.return_value = None
        bookmarks.insert_bookmark.return_value = {
            "id": BOOKMARK_ID,
            "event_id": fake_event["id"],
            "created_at": "2026-01-01T00:00:00Z",
        }

        result = bookmark_service.create_bookmark(
            db, fake_event["id"], USER_ID, bookmarks=bookmarks, events=events
        )

        assert str(result.id) == BOOKMARK_ID
        assert str(result.event_id) == fake_event["id"]
        bookmarks.insert_bookmark.assert_called_once_with(
            db, {"user_id": USER_ID, "event_id": fake_event["id"]}
        )

    def test_404_when_event_missing(self, db):
        events = MagicMock()
        events.get_event_by_id.return_value = None
        bookmarks = MagicMock()

        with pytest.raises(HTTPException) as exc:
            bookmark_service.create_bookmark(
                db, EVENT_ID, USER_ID, bookmarks=bookmarks, events=events
            )

        assert exc.value.status_code == 404
        bookmarks.insert_bookmark.assert_not_called()

    def test_400_for_draft_event(self, db, fake_event):
        fake_event["status"] = "draft"
        events = MagicMock()
        events.get_event_by_id.return_value = fake_event
        bookmarks = MagicMock()

        with pytest.raises(HTTPException) as exc:
            bookmark_service.create_bookmark(
                db, fake_event["id"], USER_ID, bookmarks=bookmarks, events=events
            )

        assert exc.value.status_code == 400
        bookmarks.insert_bookmark.assert_not_called()

    def test_409_when_already_bookmarked(self, db, fake_event):
        events = MagicMock()
        events.get_event_by_id.return_value = fake_event
        bookmarks = MagicMock()
        bookmarks.get_bookmark.return_value = {"id": BOOKMARK_ID}

        with pytest.raises(HTTPException) as exc:
            bookmark_service.create_bookmark(
                db, fake_event["id"], USER_ID, bookmarks=bookmarks, events=events
            )

        assert exc.value.status_code == 409
        bookmarks.insert_bookmark.assert_not_called()


# ── remove_bookmark ──────────────────────────────────────────────────────────


class TestRemoveBookmark:
    def test_deletes_when_present(self, db):
        bookmarks = MagicMock()
        bookmarks.get_bookmark.return_value = {"id": BOOKMARK_ID}

        bookmark_service.remove_bookmark(db, EVENT_ID, USER_ID, bookmarks=bookmarks)

        bookmarks.delete_bookmark.assert_called_once_with(db, USER_ID, EVENT_ID)

    def test_404_when_missing(self, db):
        bookmarks = MagicMock()
        bookmarks.get_bookmark.return_value = None

        with pytest.raises(HTTPException) as exc:
            bookmark_service.remove_bookmark(db, EVENT_ID, USER_ID, bookmarks=bookmarks)

        assert exc.value.status_code == 404
        bookmarks.delete_bookmark.assert_not_called()


# ── list_user_bookmarks ──────────────────────────────────────────────────────


class TestListUserBookmarks:
    def test_empty_response_when_user_has_none(self, db):
        bookmarks = MagicMock()
        bookmarks.get_bookmarks_by_user.return_value = ([], 0)
        events = MagicMock()

        result = bookmark_service.list_user_bookmarks(
            db, USER_ID, bookmarks=bookmarks, events=events
        )

        assert result.items == []
        assert result.total == 0
        # Event lookup is skipped when there are no bookmarks
        events.get_event_by_id.assert_not_called()

    def test_redacts_location_and_image_for_private_events(self, db, fake_event):
        fake_event["visibility"] = "private"
        bookmark_row = {
            "event_id": fake_event["id"],
            "created_at": "2026-01-01T00:00:00Z",
        }
        bookmarks = MagicMock()
        bookmarks.get_bookmarks_by_user.return_value = ([bookmark_row], 1)
        events = MagicMock()
        events.get_event_by_id.return_value = fake_event
        events.get_primary_locations_for_events.return_value = {
            fake_event["id"]: {"name": "secret venue"}
        }
        events.get_categories_for_events.return_value = {fake_event["id"]: []}
        events.get_primary_images_for_events.return_value = {
            fake_event["id"]: "https://example.com/img.jpg"
        }

        result = bookmark_service.list_user_bookmarks(
            db, USER_ID, bookmarks=bookmarks, events=events
        )

        assert len(result.items) == 1
        item = result.items[0]
        assert item.primary_location is None
        assert item.primary_image_url is None
