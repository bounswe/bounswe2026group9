"""Bookmark Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.event import CategoryResponse, LocationResponse


class BookmarkResponse(BaseModel):
    id: UUID
    event_id: UUID
    created_at: datetime


class BookmarkedEventResponse(BaseModel):
    """Event summary shown in user's bookmark list."""
    id: UUID
    title: str
    start_datetime: datetime
    end_datetime: datetime
    visibility: str
    is_age_restricted: bool
    status: str
    categories: list[CategoryResponse] = []
    primary_location: LocationResponse | None = None
    primary_image_url: str | None = None
    bookmarked_at: datetime


class BookmarkListResponse(BaseModel):
    items: list[BookmarkedEventResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
