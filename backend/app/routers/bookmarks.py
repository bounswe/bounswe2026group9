"""Bookmark endpoints — HTTP layer only."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.database import get_supabase
from app.middleware.auth import get_current_user_id
from app.models.bookmark import BookmarkResponse
from app.models.errors import AUTH_RESPONSES, CONFLICT_RESPONSE, NOT_FOUND_RESPONSE
from app.models.user import MessageResponse
from app.services.bookmark import create_bookmark, remove_bookmark

router = APIRouter(prefix="/events/{event_id}/bookmark", tags=["bookmarks"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=BookmarkResponse,
    summary="Bookmark an event",
    responses={**AUTH_RESPONSES, **NOT_FOUND_RESPONSE, **CONFLICT_RESPONSE},
)
def create_bookmark_endpoint(
    event_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return create_bookmark(db, str(event_id), user_id)


@router.delete(
    "",
    response_model=MessageResponse,
    summary="Remove an event bookmark",
    responses={**AUTH_RESPONSES, **NOT_FOUND_RESPONSE},
)
def remove_bookmark_endpoint(
    event_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    remove_bookmark(db, str(event_id), user_id)
    return MessageResponse(message="Bookmark removed successfully")
