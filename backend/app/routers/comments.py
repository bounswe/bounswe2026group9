"""Comment endpoints — HTTP layer only."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.database import get_supabase
from app.middleware.auth import get_current_user_id
from app.models.comment import CommentCreateRequest, CommentListResponse, CommentResponse
from app.models.errors import AUTH_RESPONSES, FORBIDDEN_RESPONSE, NOT_FOUND_RESPONSE
from app.models.user import MessageResponse
from app.services.comment import (
    create_comment,
    delete_comment,
    list_comments,
)

router = APIRouter(prefix="/events/{event_id}/comments", tags=["comments"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CommentResponse,
    summary="Post a comment on an event",
    responses={**AUTH_RESPONSES, **NOT_FOUND_RESPONSE},
)
def create_comment_endpoint(
    event_id: UUID,
    body: CommentCreateRequest,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return create_comment(db, str(event_id), user_id, body)


@router.get(
    "",
    response_model=CommentListResponse,
    summary="List comments for an event",
    responses={**NOT_FOUND_RESPONSE},
)
def list_comments_endpoint(
    event_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    db = get_supabase()
    return list_comments(db, str(event_id), page=page, page_size=page_size)


@router.delete(
    "/{comment_id}",
    response_model=MessageResponse,
    summary="Delete a comment",
    description="Author or event host only.",
    responses={**AUTH_RESPONSES, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
def delete_comment_endpoint(
    event_id: UUID,
    comment_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    delete_comment(db, str(event_id), str(comment_id), user_id)
    return MessageResponse(message="Comment deleted successfully")
