from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.base import AppBaseModel


class CommentCreateRequest(AppBaseModel):
    text: str = Field(min_length=1)
    parent_id: UUID | None = None


class CommentAuthor(AppBaseModel):
    id: UUID
    username: str


class CommentResponse(AppBaseModel):
    id: UUID
    event_id: UUID
    user: CommentAuthor
    text: str
    created_at: datetime
    parent_id: UUID | None = None
    replies: list["CommentResponse"] = []


class CommentListResponse(AppBaseModel):
    items: list[CommentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
