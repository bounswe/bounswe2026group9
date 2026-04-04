"""Notification service — business logic for notifications."""

from fastapi import HTTPException, status
from supabase import Client

from app.models.notification import (
    NotificationListResponse,
    NotificationReadAllResponse,
    NotificationReadResponse,
    NotificationResponse,
    NotificationUnreadCountResponse,
)
from app.repositories import notification as notification_repo


def list_notifications(
    db: Client, user_id: str, *, page: int = 1, page_size: int = 20
) -> NotificationListResponse:
    items, total = notification_repo.get_notifications_by_user(
        db, user_id, page=page, page_size=page_size
    )
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return NotificationListResponse(
        items=[NotificationResponse(**n) for n in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def mark_as_read(db: Client, notification_id: str, user_id: str) -> NotificationReadResponse:
    notification = notification_repo.get_notification_by_id(db, notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )
    if notification["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another user's notification",
        )

    updated = notification_repo.mark_notification_as_read(db, notification_id)
    return NotificationReadResponse(id=updated["id"], is_read=updated["is_read"])


def mark_all_as_read(db: Client, user_id: str) -> NotificationReadAllResponse:
    count = notification_repo.mark_all_notifications_as_read(db, user_id)
    return NotificationReadAllResponse(updated_count=count)


def get_unread_count(db: Client, user_id: str) -> NotificationUnreadCountResponse:
    count = notification_repo.get_unread_count(db, user_id)
    return NotificationUnreadCountResponse(unread_count=count)
