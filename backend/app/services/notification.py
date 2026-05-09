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
from app.repositories import notification as _notification_repo
from app.repositories.protocols import NotificationRepoProtocol


def list_notifications(
    db: Client,
    user_id: str,
    *,
    page: int = 1,
    page_size: int = 20,
    notifications: NotificationRepoProtocol = _notification_repo,
) -> NotificationListResponse:
    items, total = notifications.get_notifications_by_user(
        db, user_id, page=page, page_size=page_size
    )
    unread_count = notifications.get_unread_count(db, user_id)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return NotificationListResponse(
        items=[NotificationResponse(**n) for n in items],
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def mark_as_read(
    db: Client,
    notification_id: str,
    user_id: str,
    *,
    notifications: NotificationRepoProtocol = _notification_repo,
) -> NotificationReadResponse:
    notification = notifications.get_notification_by_id(db, notification_id)
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )
    if notification["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access another user's notification",
        )

    updated = notifications.mark_notification_as_read(db, notification_id)
    return NotificationReadResponse(id=updated["id"], is_read=updated["is_read"])


def mark_all_as_read(
    db: Client,
    user_id: str,
    *,
    notifications: NotificationRepoProtocol = _notification_repo,
) -> NotificationReadAllResponse:
    count = notifications.mark_all_notifications_as_read(db, user_id)
    return NotificationReadAllResponse(updated_count=count)


def get_unread_count(
    db: Client,
    user_id: str,
    *,
    notifications: NotificationRepoProtocol = _notification_repo,
) -> NotificationUnreadCountResponse:
    count = notifications.get_unread_count(db, user_id)
    return NotificationUnreadCountResponse(unread_count=count)
