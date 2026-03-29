"""Notification endpoints — HTTP layer only."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.database import get_supabase
from app.middleware.auth import get_current_user_id
from app.models.notification import (
    NotificationListResponse,
    NotificationReadAllResponse,
    NotificationReadResponse,
)
from app.services.notification import (
    list_notifications,
    mark_all_as_read,
    mark_as_read,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.patch("/read-all", response_model=NotificationReadAllResponse)
def read_all_notifications(
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return mark_all_as_read(db, user_id)


@router.get("", response_model=NotificationListResponse)
def list_notifications_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return list_notifications(db, user_id, page=page, page_size=page_size)


@router.patch("/{notification_id}/read", response_model=NotificationReadResponse)
def read_notification(
    notification_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return mark_as_read(db, str(notification_id), user_id)
