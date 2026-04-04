from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CommentCreateRequest(BaseModel):
    text: str = Field(min_length=1)
    parent_id: UUID | None = None


class CommentAuthor(BaseModel):
    id: UUID
    username: str


class CommentResponse(BaseModel):
    id: UUID
    event_id: UUID
    user: CommentAuthor
    text: str
    created_at: datetime
    parent_id: UUID | None = None
    replies: list["CommentResponse"] = []


class CommentListResponse(BaseModel):
    items: list[CommentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
