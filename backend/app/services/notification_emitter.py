"""Notification emitter — creates notifications for affected users on event changes."""

from supabase import Client

from app.repositories import attendance as _attendance_repo
from app.repositories import bookmark as _bookmark_repo
from app.repositories import notification as _notification_repo
from app.repositories.protocols import (
    AttendanceRepoProtocol,
    BookmarkRepoProtocol,
    NotificationRepoProtocol,
)


def _get_affected_user_ids(
    db: Client,
    event_id: str,
    attendances: AttendanceRepoProtocol,
    bookmarks: BookmarkRepoProtocol,
) -> set[str]:
    """Get unique user IDs who bookmarked or are going to the event."""
    going = set(attendances.get_going_user_ids_for_event(db, event_id))
    bookmarkers = bookmarks.get_bookmarker_user_ids(db, event_id)
    return going | bookmarkers


def emit_event_notification(
    db: Client,
    event_id: str,
    host_id: str,
    notification_type: str,
    message: str,
    *,
    attendances: AttendanceRepoProtocol = _attendance_repo,
    bookmarks: BookmarkRepoProtocol = _bookmark_repo,
    notifications: NotificationRepoProtocol = _notification_repo,
) -> int:
    """Create notifications for all affected users (excluding host).

    Returns the number of notifications created.
    """
    user_ids = _get_affected_user_ids(db, event_id, attendances, bookmarks)
    user_ids.discard(host_id)  # Host doesn't get notified for own action

    if not user_ids:
        return 0

    rows = [
        {
            "user_id": uid,
            "event_id": event_id,
            "type": notification_type,
            "message": message,
            "is_read": False,
        }
        for uid in user_ids
    ]

    notifications.insert_notifications_bulk(db, rows)
    return len(rows)
