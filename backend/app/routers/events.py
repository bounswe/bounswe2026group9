"""Event endpoints — HTTP layer only."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile, status

from app.database import get_supabase
from app.middleware.auth import get_current_user_id
from app.models.event import (
    EventCreateRequest,
    EventDetailResponse,
    EventImageResponse,
    EventLimitedResponse,
    EventListResponse,
    EventUpdateRequest,
    StatusChangeRequest,
)
from app.models.user import MessageResponse
from app.services.auth import decode_access_token
from app.services.event import (
    change_event_status,
    create_event,
    delete_event,
    get_event_detail,
    update_event,
)
from app.services.event import (
    list_events as list_events_svc,
)
from app.services.image import delete_event_image as delete_image_svc
from app.services.image import upload_event_image

router = APIRouter(prefix="/events", tags=["events"])


def _optional_user_id(authorization: str | None = Header(default=None)) -> str | None:
    """Extract user_id from Bearer token if present, otherwise return None (guest).

    No token = guest (returns None). Invalid/expired token = 401 error.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        # Check if user is still active
        if user_id:
            from app.repositories import user as user_repo
            db = get_supabase()
            user = user_repo.get_user_by_id(db, user_id)
            if not user or not user.get("is_active", True):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Account is deactivated",
                )
        return user_id
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from e


@router.get("", response_model=EventListResponse)
def list_events_endpoint(
    search: str | None = Query(default=None, max_length=200),
    category_id: UUID | None = Query(default=None),
    temporal_filter: str | None = Query(default=None, pattern="^(upcoming|today|this_week)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: str | None = Depends(_optional_user_id),  # noqa: ARG001 — reserved for future auth-only filters
):
    db = get_supabase()
    return list_events_svc(
        db,
        search=search,
        category_id=str(category_id) if category_id else None,
        temporal_filter=temporal_filter,
        page=page,
        page_size=page_size,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=EventDetailResponse)
def create_event_endpoint(
    body: EventCreateRequest,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return create_event(db, user_id, body)


@router.get("/{event_id}", response_model=EventDetailResponse | EventLimitedResponse)
def get_event_endpoint(
    event_id: UUID,
    user_id: str | None = Depends(_optional_user_id),
):
    db = get_supabase()
    return get_event_detail(db, str(event_id), user_id)


@router.put("/{event_id}", response_model=EventDetailResponse)
def update_event_endpoint(
    event_id: UUID,
    body: EventUpdateRequest,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return update_event(db, str(event_id), user_id, body)


@router.patch("/{event_id}/status", response_model=EventDetailResponse)
def change_event_status_endpoint(
    event_id: UUID,
    body: StatusChangeRequest,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return change_event_status(db, str(event_id), user_id, body.status)


@router.delete("/{event_id}", status_code=status.HTTP_200_OK, response_model=MessageResponse)
def delete_event_endpoint(
    event_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    delete_event(db, str(event_id), user_id)
    return MessageResponse(message="Event deleted successfully")


@router.post("/{event_id}/images", status_code=status.HTTP_201_CREATED, response_model=EventImageResponse)
def upload_image_endpoint(
    event_id: UUID,
    file: UploadFile,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return upload_event_image(db, str(event_id), user_id, file)


@router.delete("/{event_id}/images/{image_id}", response_model=MessageResponse)
def delete_image_endpoint(
    event_id: UUID,
    image_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    delete_image_svc(db, str(event_id), str(image_id), user_id)
    return MessageResponse(message="Image deleted successfully")
