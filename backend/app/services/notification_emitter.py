"""Notification emitter — creates notifications for affected users on event changes."""

from supabase import Client

from app.repositories import notification as notification_repo


def _get_affected_user_ids(db: Client, event_id: str) -> set[str]:
    """Get unique user IDs who bookmarked or are attending (going/interested) the event."""
    user_ids: set[str] = set()

    # Attendees (going or interested)
    attendees = (
        db.table("attendances")
        .select("user_id")
        .eq("event_id", event_id)
        .in_("status", ["going", "interested"])
        .execute()
    )
    for row in (attendees.data or []):
        user_ids.add(row["user_id"])

    # Bookmarkers
    bookmarks = (
        db.table("bookmarks")
        .select("user_id")
        .eq("event_id", event_id)
        .execute()
    )
    for row in (bookmarks.data or []):
        user_ids.add(row["user_id"])

    return user_ids


def emit_event_notification(
    db: Client,
    event_id: str,
    host_id: str,
    notification_type: str,
    message: str,
) -> int:
    """Create notifications for all affected users (excluding host).

    Returns the number of notifications created.
    """
    user_ids = _get_affected_user_ids(db, event_id)
    user_ids.discard(host_id)  # Host doesn't get notified for own action

    if not user_ids:
        return 0

    notifications = [
        {
            "user_id": uid,
            "event_id": event_id,
            "type": notification_type,
            "message": message,
            "is_read": False,
        }
        for uid in user_ids
    ]

    notification_repo.insert_notifications_bulk(db, notifications)
    return len(notifications)
