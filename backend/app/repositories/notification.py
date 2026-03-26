"""Notification repository — all database operations for notifications."""

from supabase import Client


def get_notifications_by_user(
    db: Client,
    user_id: str,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict], int]:
    """Return (notifications, total_count) for a user, newest first."""
    count_result = (
        db.table("notifications")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    total = count_result.count or 0

    offset = (page - 1) * page_size
    if offset >= total and total > 0:
        return [], total

    result = (
        db.table("notifications")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .order("id", desc=True)
        .range(offset, offset + page_size - 1)
        .execute()
    )
    return result.data or [], total


def get_notification_by_id(db: Client, notification_id: str) -> dict | None:
    """Fetch a single notification by ID."""
    result = (
        db.table("notifications")
        .select("*")
        .eq("id", notification_id)
        .execute()
    )
    return result.data[0] if result.data else None


def mark_notification_as_read(db: Client, notification_id: str) -> dict | None:
    """Mark a single notification as read."""
    (
        db.table("notifications")
        .update({"is_read": True})
        .eq("id", notification_id)
        .execute()
    )
    return get_notification_by_id(db, notification_id)


def mark_all_notifications_as_read(db: Client, user_id: str) -> int:
    """Mark all unread notifications as read for a user. Returns updated count."""
    count_result = (
        db.table("notifications")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .eq("is_read", False)
        .execute()
    )
    updated_count = count_result.count or 0
    if updated_count == 0:
        return 0

    (
        db.table("notifications")
        .update({"is_read": True})
        .eq("user_id", user_id)
        .eq("is_read", False)
        .execute()
    )
    return updated_count


def insert_notification(db: Client, data: dict) -> dict | None:
    """Insert a new notification."""
    result = db.table("notifications").insert(data).execute()
    return result.data[0] if result.data else None


def insert_notifications_bulk(db: Client, notifications: list[dict]) -> list[dict]:
    """Insert multiple notifications at once."""
    if not notifications:
        return []
    result = db.table("notifications").insert(notifications).execute()
    return result.data or []
