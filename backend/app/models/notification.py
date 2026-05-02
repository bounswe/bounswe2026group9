from datetime import datetime
from uuid import UUID

from app.models.base import AppBaseModel

# --- Response Schemas ---

class NotificationResponse(AppBaseModel):
    id: UUID
    user_id: UUID
    event_id: UUID | None
    type: str
    message: str
    is_read: bool
    created_at: datetime


class NotificationListResponse(AppBaseModel):
    """Paginated notification list."""
    items: list[NotificationResponse]
    total: int
    unread_count: int
    page: int
    page_size: int
    total_pages: int


class NotificationReadResponse(AppBaseModel):
    """Single notification mark-as-read response."""
    id: UUID
    is_read: bool


class NotificationReadAllResponse(AppBaseModel):
    """Bulk mark-as-read response."""
    updated_count: int


class NotificationUnreadCountResponse(AppBaseModel):
    """Unread notification count."""
    unread_count: int
