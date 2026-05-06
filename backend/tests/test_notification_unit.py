"""Unit tests for `services.notification` — exercises the keyword-DI seam."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services import notification as notification_service

USER_ID = "00000000-0000-0000-0000-000000000020"
OTHER_USER_ID = "00000000-0000-0000-0000-000000000021"
NOTIFICATION_ID = "00000000-0000-0000-0000-000000000022"


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


def _row(read: bool = False, user_id: str = USER_ID, type_: str = "event_updated") -> dict:
    return {
        "id": NOTIFICATION_ID,
        "user_id": user_id,
        "event_id": "00000000-0000-0000-0000-000000000023",
        "type": type_,
        "message": "msg",
        "is_read": read,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


# ── list_notifications ──────────────────────────────────────────────────────


class TestListNotifications:
    def test_combines_paged_rows_with_unread_count(self, db):
        notifications = MagicMock()
        notifications.get_notifications_by_user.return_value = ([_row(read=False)], 1)
        notifications.get_unread_count.return_value = 1

        result = notification_service.list_notifications(
            db, USER_ID, notifications=notifications
        )

        assert result.total == 1
        assert result.unread_count == 1
        assert result.total_pages == 1
        assert len(result.items) == 1

    def test_zero_total_yields_zero_pages(self, db):
        notifications = MagicMock()
        notifications.get_notifications_by_user.return_value = ([], 0)
        notifications.get_unread_count.return_value = 0

        result = notification_service.list_notifications(
            db, USER_ID, notifications=notifications
        )

        assert result.total == 0
        assert result.total_pages == 0
        assert result.items == []


# ── mark_as_read ────────────────────────────────────────────────────────────


class TestMarkAsRead:
    def test_marks_when_owner(self, db):
        notifications = MagicMock()
        notifications.get_notification_by_id.return_value = _row(read=False)
        notifications.mark_notification_as_read.return_value = _row(read=True)

        result = notification_service.mark_as_read(
            db, NOTIFICATION_ID, USER_ID, notifications=notifications
        )

        assert result.is_read is True
        notifications.mark_notification_as_read.assert_called_once_with(db, NOTIFICATION_ID)

    def test_404_when_missing(self, db):
        notifications = MagicMock()
        notifications.get_notification_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            notification_service.mark_as_read(
                db, NOTIFICATION_ID, USER_ID, notifications=notifications
            )

        assert exc.value.status_code == 404
        notifications.mark_notification_as_read.assert_not_called()

    def test_403_when_not_owner(self, db):
        notifications = MagicMock()
        notifications.get_notification_by_id.return_value = _row(user_id=OTHER_USER_ID)

        with pytest.raises(HTTPException) as exc:
            notification_service.mark_as_read(
                db, NOTIFICATION_ID, USER_ID, notifications=notifications
            )

        assert exc.value.status_code == 403
        notifications.mark_notification_as_read.assert_not_called()


# ── mark_all_as_read / get_unread_count ─────────────────────────────────────


class TestBulkOperations:
    def test_mark_all_returns_count_from_repo(self, db):
        notifications = MagicMock()
        notifications.mark_all_notifications_as_read.return_value = 7

        result = notification_service.mark_all_as_read(
            db, USER_ID, notifications=notifications
        )

        assert result.updated_count == 7
        notifications.mark_all_notifications_as_read.assert_called_once_with(db, USER_ID)

    def test_get_unread_count_returns_count_from_repo(self, db):
        notifications = MagicMock()
        notifications.get_unread_count.return_value = 3

        result = notification_service.get_unread_count(
            db, USER_ID, notifications=notifications
        )

        assert result.unread_count == 3
