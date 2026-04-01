"""Fast unit tests for notification emitter behavior."""

from types import SimpleNamespace
from unittest.mock import patch

from app.services import notification_emitter


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def in_(self, *_args, **_kwargs):
        return self

    def execute(self):
        return SimpleNamespace(data=self._rows)


class _FakeDB:
    def __init__(self, table_rows):
        self._table_rows = table_rows

    def table(self, name):
        return _FakeQuery(self._table_rows.get(name, []))


class TestGetAffectedUserIds:
    def test_combines_attendees_and_bookmarkers_without_duplicates(self):
        db = _FakeDB({
            "attendances": [
                {"user_id": "user-going"},
                {"user_id": "user-shared"},
            ],
            "bookmarks": [
                {"user_id": "user-shared"},
                {"user_id": "user-bookmark"},
            ],
        })

        user_ids = notification_emitter._get_affected_user_ids(db, "event-1")

        assert user_ids == {"user-going", "user-shared", "user-bookmark"}


class TestEmitEventNotification:
    @patch("app.services.notification_emitter.notification_repo.insert_notifications_bulk")
    @patch("app.services.notification_emitter._get_affected_user_ids")
    def test_excludes_host_and_inserts_expected_payload(
        self, mock_get_affected_user_ids, mock_insert_notifications_bulk
    ):
        db = object()
        mock_get_affected_user_ids.return_value = {
            "host-1",
            "user-1",
            "user-2",
        }

        created_count = notification_emitter.emit_event_notification(
            db=db,
            event_id="event-1",
            host_id="host-1",
            notification_type="event_updated",
            message="Event changed",
        )

        assert created_count == 2
        mock_insert_notifications_bulk.assert_called_once()
        assert mock_insert_notifications_bulk.call_args.args[0] is db
        inserted_rows = mock_insert_notifications_bulk.call_args.args[1]
        assert {row["user_id"] for row in inserted_rows} == {"user-1", "user-2"}
        for row in inserted_rows:
            assert row["event_id"] == "event-1"
            assert row["type"] == "event_updated"
            assert row["message"] == "Event changed"
            assert row["is_read"] is False

    @patch("app.services.notification_emitter.notification_repo.insert_notifications_bulk")
    @patch("app.services.notification_emitter._get_affected_user_ids")
    def test_returns_zero_without_non_host_recipients(
        self, mock_get_affected_user_ids, mock_insert_notifications_bulk
    ):
        db = object()
        mock_get_affected_user_ids.return_value = {"host-1"}

        created_count = notification_emitter.emit_event_notification(
            db=db,
            event_id="event-1",
            host_id="host-1",
            notification_type="event_cancelled",
            message="Event cancelled",
        )

        assert created_count == 0
        mock_insert_notifications_bulk.assert_not_called()
