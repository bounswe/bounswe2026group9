"""Event endpoints — HTTP layer only."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, UploadFile, status

from app.database import get_supabase
from app.middleware.auth import get_current_user_id
from app.models.errors import (
    AUTH_RESPONSES,
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
)
from app.models.event import (
    EventCreateRequest,
    EventDetailResponse,
    EventImageResponse,
    EventLimitedResponse,
    EventListResponse,
    EventUpdateRequest,
    StatusChangeRequest,
)
from app.models.geojson import GeoJSONFeatureCollection
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
from app.services.event import (
    list_events_geojson as list_events_geojson_svc,
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


@router.get(
    "",
    response_model=EventListResponse,
    summary="Discover events",
    description=(
        "Paginated event discovery with quick filters, custom time window, accessibility "
        "filters, distance bounding box, and ranking by start time / distance / category. "
        "When the client opts in via use_default_area, the authenticated user's stored "
        "default location is used in place of explicit near_lat/near_lng."
    ),
)
def list_events_endpoint(
    search: str | None = Query(default=None, max_length=200),
    category_id: UUID | None = Query(default=None),
    quick_filter: str | None = Query(
        default=None,
        pattern="^(now|today|weekend|upcoming|this_week|past)$",
        description="Time-window quick filter. Mutually exclusive with start_after/end_before.",
    ),
    start_after: datetime | None = Query(
        default=None,
        description="Custom window: only events starting at or after this time.",
    ),
    end_before: datetime | None = Query(
        default=None,
        description="Custom window: only events ending at or before this time.",
    ),
    near_lat: float | None = Query(default=None, ge=-90, le=90),
    near_lng: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float | None = Query(default=None, gt=0, le=500),
    use_default_area: bool = Query(
        default=False,
        description="If true, use the authenticated user's stored default area. Ignored when near_lat/near_lng are provided.",
    ),
    wheelchair: bool | None = Query(default=None),
    accessible_restroom: bool | None = Query(default=None),
    elevator: bool | None = Query(default=None),
    seating: bool | None = Query(default=None),
    captions: bool | None = Query(
        default=None,
        description=(
            "Filter events whose venue offers captions support. "
            "Note: this maps to the existing `captions_support` venue column; a "
            "dedicated sign-language interpretation column is not modelled yet."
        ),
    ),
    quiet_friendly: bool | None = Query(default=None),
    sort: str | None = Query(
        default=None,
        pattern="^(start_time|distance|category)$",
        description=(
            "Sort order. Defaults to distance when location is provided, otherwise start_time. "
            "sort=distance requires a location (near_lat/near_lng or use_default_area). "
            "sort=category requires a narrowing filter — search, category_id, quick_filter, "
            "custom window, accessibility, or location — to keep the in-memory candidate set bounded."
        ),
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: str | None = Depends(_optional_user_id),
):
    if quick_filter is not None and (start_after is not None or end_before is not None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="quick_filter cannot be combined with start_after/end_before",
        )
    if start_after is not None and end_before is not None and start_after >= end_before:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_after must be earlier than end_before",
        )
    if (near_lat is None) != (near_lng is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="near_lat and near_lng must be provided together",
        )
    if radius_km is not None and near_lat is None and not use_default_area:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="radius_km requires near_lat/near_lng or use_default_area",
        )
    if use_default_area and user_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="use_default_area requires authentication",
        )

    db = get_supabase()
    return list_events_svc(
        db,
        user_id=user_id,
        search=search,
        category_id=str(category_id) if category_id else None,
        quick_filter=quick_filter,
        start_after=start_after,
        end_before=end_before,
        near_lat=near_lat,
        near_lng=near_lng,
        radius_km=radius_km,
        use_default_area=use_default_area,
        accessibility={
            "wheelchair_access": wheelchair,
            "accessible_restroom": accessible_restroom,
            "elevator": elevator,
            "seating": seating,
            "captions": captions,
            "quiet_friendly": quiet_friendly,
        },
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/geojson",
    response_model=GeoJSONFeatureCollection,
    summary="Discover events as GeoJSON",
    description=(
        "Returns event discovery data as an RFC 7946 GeoJSON FeatureCollection. "
        "Supports the exact same spatial and temporal filters as /events, but "
        "forces a large page size internally to return a comprehensive map layer."
    ),
)
def list_events_geojson_endpoint(
    search: str | None = Query(default=None, max_length=200),
    category_id: UUID | None = Query(default=None),
    quick_filter: str | None = Query(
        default=None,
        pattern="^(now|today|weekend|upcoming|this_week|past)$",
        description="Time-window quick filter. Mutually exclusive with start_after/end_before.",
    ),
    start_after: datetime | None = Query(
        default=None,
        description="Custom window: only events starting at or after this time.",
    ),
    end_before: datetime | None = Query(
        default=None,
        description="Custom window: only events ending at or before this time.",
    ),
    near_lat: float | None = Query(default=None, ge=-90, le=90),
    near_lng: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float | None = Query(default=None, gt=0, le=500),
    use_default_area: bool = Query(
        default=False,
        description="If true, use the authenticated user's stored default area. Ignored when near_lat/near_lng are provided.",
    ),
    wheelchair: bool | None = Query(default=None),
    accessible_restroom: bool | None = Query(default=None),
    elevator: bool | None = Query(default=None),
    seating: bool | None = Query(default=None),
    captions: bool | None = Query(default=None),
    quiet_friendly: bool | None = Query(default=None),
    sort: str | None = Query(
        default=None,
        pattern="^(start_time|distance|category)$",
    ),
    user_id: str | None = Depends(_optional_user_id),
):
    if quick_filter is not None and (start_after is not None or end_before is not None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="quick_filter cannot be combined with start_after/end_before",
        )
    if start_after is not None and end_before is not None and start_after >= end_before:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_after must be earlier than end_before",
        )
    if (near_lat is None) != (near_lng is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="near_lat and near_lng must be provided together",
        )

    return list_events_geojson_svc(
        get_supabase(),
        user_id=user_id,
        search=search,
        category_id=str(category_id) if category_id else None,
        quick_filter=quick_filter,
        start_after=start_after,
        end_before=end_before,
        near_lat=near_lat,
        near_lng=near_lng,
        radius_km=radius_km,
        use_default_area=use_default_area,
        accessibility={
            # Canonical key is "wheelchair_access" — must match the
            # _ACCESSIBILITY_DB_MAP keys used by repositories/event.py and
            # the main /events endpoint, otherwise the filter is silently
            # ignored.
            "wheelchair_access": wheelchair,
            "accessible_restroom": accessible_restroom,
            "elevator": elevator,
            "seating": seating,
            "captions": captions,
            "quiet_friendly": quiet_friendly,
        },
        sort=sort,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=EventDetailResponse,
    summary="Create an event",
    description=(
        "Create a new event with locations, categories, optional venue "
        "metadata, equipment list, and itinerary segments — all in one "
        "atomic transaction."
    ),
    responses={**AUTH_RESPONSES, **CONFLICT_RESPONSE},
)
def create_event_endpoint(
    body: EventCreateRequest,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return create_event(db, user_id, body)


@router.get(
    "/{event_id}",
    response_model=EventDetailResponse | EventLimitedResponse,
    summary="Get event detail",
    description=(
        "Returns the full event payload for callers with access. "
        "For private events the caller does not have access to, returns a "
        "limited subset (`EventLimitedResponse`) — title, host, status, "
        "and the public preview fields only."
    ),
    responses={**NOT_FOUND_RESPONSE},
)
def get_event_endpoint(
    event_id: UUID,
    user_id: str | None = Depends(_optional_user_id),
):
    db = get_supabase()
    return get_event_detail(db, str(event_id), user_id)


@router.put(
    "/{event_id}",
    response_model=EventDetailResponse,
    summary="Update an event",
    description="Host-only. Replaces event fields and any nested collections "
                "supplied in the body atomically.",
    responses={**AUTH_RESPONSES, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
def update_event_endpoint(
    event_id: UUID,
    body: EventUpdateRequest,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return update_event(db, str(event_id), user_id, body)


@router.patch(
    "/{event_id}/status",
    response_model=EventDetailResponse,
    summary="Change event status",
    description=(
        "Host-only. Transition the event between `draft`, `published`, "
        "`updated`, and `cancelled` per the lifecycle rules."
    ),
    responses={**AUTH_RESPONSES, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
def change_event_status_endpoint(
    event_id: UUID,
    body: StatusChangeRequest,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return change_event_status(db, str(event_id), user_id, body.status)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponse,
    summary="Delete an event",
    description="Host-only.",
    responses={**AUTH_RESPONSES, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
def delete_event_endpoint(
    event_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    delete_event(db, str(event_id), user_id)
    return MessageResponse(message="Event deleted successfully")


@router.post(
    "/{event_id}/images",
    status_code=status.HTTP_201_CREATED,
    response_model=EventImageResponse,
    summary="Upload an event image",
    description="Host-only. `multipart/form-data` upload; max size and "
                "MIME-type rules are enforced server-side.",
    responses={**AUTH_RESPONSES, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
def upload_image_endpoint(
    event_id: UUID,
    file: UploadFile,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return upload_event_image(db, str(event_id), user_id, file)


@router.delete(
    "/{event_id}/images/{image_id}",
    response_model=MessageResponse,
    summary="Delete an event image",
    description="Host-only.",
    responses={**AUTH_RESPONSES, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
def delete_image_endpoint(
    event_id: UUID,
    image_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    delete_image_svc(db, str(event_id), str(image_id), user_id)
    return MessageResponse(message="Image deleted successfully")
