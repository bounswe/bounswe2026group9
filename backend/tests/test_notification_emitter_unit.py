"""Unit tests for `services.notification_emitter` — exercises the keyword-DI seam."""

from unittest.mock import MagicMock

import pytest

from app.services import notification_emitter as emitter


EVENT_ID = "00000000-0000-0000-0000-000000000090"
HOST_ID = "00000000-0000-0000-0000-000000000091"
USER_A = "00000000-0000-0000-0000-000000000092"
USER_B = "00000000-0000-0000-0000-000000000093"
USER_C = "00000000-0000-0000-0000-000000000094"


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


@pytest.fixture
def repos():
    attendances = MagicMock()
    bookmarks = MagicMock()
    notifications = MagicMock()
    return attendances, bookmarks, notifications


# ── _get_affected_user_ids ──────────────────────────────────────────────────


class TestGetAffectedUserIds:
    def test_combines_attendees_and_bookmarkers_without_duplicates(self, db, repos):
        attendances, bookmarks, _ = repos
        attendances.get_going_user_ids_for_event.return_value = ["going", "shared"]
        bookmarks.get_bookmarker_user_ids.return_value = {"shared", "bookmark"}

        result = emitter._get_affected_user_ids(db, EVENT_ID, attendances, bookmarks)

        assert result == {"going", "shared", "bookmark"}


# ── emit_event_notification ─────────────────────────────────────────────────


class TestEmitEventNotification:
    def test_returns_zero_when_no_affected_users(self, db, repos):
        attendances, bookmarks, notifications = repos
        attendances.get_going_user_ids_for_event.return_value = []
        bookmarks.get_bookmarker_user_ids.return_value = set()

        count = emitter.emit_event_notification(
            db, EVENT_ID, HOST_ID, "event_updated", "msg",
            attendances=attendances, bookmarks=bookmarks, notifications=notifications,
        )

        assert count == 0
        notifications.insert_notifications_bulk.assert_not_called()

    def test_unions_going_and_bookmarkers(self, db, repos):
        attendances, bookmarks, notifications = repos
        attendances.get_going_user_ids_for_event.return_value = [USER_A, USER_B]
        bookmarks.get_bookmarker_user_ids.return_value = {USER_B, USER_C}  # B overlaps

        count = emitter.emit_event_notification(
            db, EVENT_ID, HOST_ID, "event_updated", "show changed",
            attendances=attendances, bookmarks=bookmarks, notifications=notifications,
        )

        assert count == 3
        sent_user_ids = {
            r["user_id"]
            for r in notifications.insert_notifications_bulk.call_args.args[1]
        }
        assert sent_user_ids == {USER_A, USER_B, USER_C}

    def test_excludes_host_from_recipients(self, db, repos):
        attendances, bookmarks, notifications = repos
        attendances.get_going_user_ids_for_event.return_value = [HOST_ID, USER_A]
        bookmarks.get_bookmarker_user_ids.return_value = {HOST_ID, USER_B}

        count = emitter.emit_event_notification(
            db, EVENT_ID, HOST_ID, "event_cancelled", "show is off",
            attendances=attendances, bookmarks=bookmarks, notifications=notifications,
        )

        assert count == 2
        sent_user_ids = {
            r["user_id"]
            for r in notifications.insert_notifications_bulk.call_args.args[1]
        }
        assert HOST_ID not in sent_user_ids
        assert sent_user_ids == {USER_A, USER_B}

    def test_payload_carries_type_message_and_unread_flag(self, db, repos):
        attendances, bookmarks, notifications = repos
        attendances.get_going_user_ids_for_event.return_value = [USER_A]
        bookmarks.get_bookmarker_user_ids.return_value = set()

        emitter.emit_event_notification(
            db, EVENT_ID, HOST_ID, "event_recommended", "Based on jazz",
            attendances=attendances, bookmarks=bookmarks, notifications=notifications,
        )

        sent = notifications.insert_notifications_bulk.call_args.args[1]
        assert sent[0]["event_id"] == EVENT_ID
        assert sent[0]["type"] == "event_recommended"
        assert sent[0]["message"] == "Based on jazz"
        assert sent[0]["is_read"] is False
