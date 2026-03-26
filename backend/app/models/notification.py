from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


# --- Response Schemas ---


class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    event_id: UUID | None
    type: str
    message: str
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Paginated notification list."""
    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class NotificationReadResponse(BaseModel):
    """Single notification mark-as-read response."""
    id: UUID
    is_read: bool


class NotificationReadAllResponse(BaseModel):
    """Bulk mark-as-read response."""
    updated_count: int
