"""Event service — business logic, validation, orchestration."""

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from supabase import Client

from app.models.event import (
    EventCreateRequest,
    EventDetailResponse,
    EventLimitedResponse,
    EventListItemResponse,
    EventListResponse,
    EventUpdateRequest,
)
from app.repositories import attendance as attendance_repo
from app.repositories import bookmark as bookmark_repo
from app.repositories import event as event_repo
from app.repositories import image as image_repo
from app.repositories import user as user_repo
from app.services.rate_limit import is_rate_limit_exempt_email

# --- Validators ---

def _ensure_timezone_aware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must include timezone information",
        )
    return value


def _parse_stored_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return parsed.replace(tzinfo=UTC)
    return parsed

def validate_event_datetime(
    start_datetime: datetime, end_datetime: datetime, *, allow_past: bool = False,
) -> None:
    start_datetime = _ensure_timezone_aware(start_datetime, "start_datetime")
    end_datetime = _ensure_timezone_aware(end_datetime, "end_datetime")
    if not allow_past and start_datetime <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_datetime must be in the future",
        )
    if end_datetime <= start_datetime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_datetime must be after start_datetime",
        )


def validate_categories_exist(db: Client, category_ids: list[str]) -> None:
    found_ids = event_repo.get_valid_category_ids(db, category_ids)
    missing = set(category_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or unapproved category IDs: {list(missing)}",
        )


def check_duplicate_event(
    db: Client, host_id: str, title: str, start_datetime: str, location_name: str
) -> None:
    events = event_repo.find_duplicate_events(db, host_id, title, start_datetime)
    for event in events:
        locations = event_repo.find_location_by_event_and_name(db, event["id"], location_name)
        if locations:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A similar event already exists with the same title, time, and location",
            )


def check_rate_limit(db: Client, host_id: str) -> None:
    host_email = user_repo.get_user_email_by_id(db, host_id)
    if is_rate_limit_exempt_email(host_email):
        return

    config = event_repo.get_rate_limit_config(db)
    if not config:
        return

    max_events = config["max_events_per_user"]
    window_hours = config["time_window_hours"]
    cutoff = (datetime.now(UTC) - timedelta(hours=window_hours)).isoformat()

    count = event_repo.count_events_by_host_since(db, host_id, cutoff)
    if count >= max_events:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: max {max_events} events per {window_hours} hours",
        )


def auto_end_event_if_past(db: Client, event: dict) -> dict:
    if event["status"] in ("published", "updated"):
        end_dt = _parse_stored_datetime(event["end_datetime"])
        if end_dt < datetime.now(UTC):
            event_repo.update_event_status(db, event["id"], "ended")
            event["status"] = "ended"
    return event


# --- Main operations ---

def create_event(db: Client, user_id: str, body: EventCreateRequest) -> EventDetailResponse:
    # Validations
    validate_event_datetime(body.start_datetime, body.end_datetime)

    category_id_strs = [str(cid) for cid in body.category_ids]
    validate_categories_exist(db, category_id_strs)

    primary_location = next((loc for loc in body.locations if loc.is_primary), body.locations[0])
    check_duplicate_event(
        db, user_id, body.title, body.start_datetime.isoformat(), primary_location.name,
    )
    check_rate_limit(db, user_id)

    # Cannot publish directly on create — images must be uploaded first
    if body.status == "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish directly on create. Create as draft, upload images, then publish via PATCH status.",
        )

    has_primary = any(loc.is_primary for loc in body.locations)
    if not has_primary:
        body.locations[0].is_primary = True

    # Insert event
    event_data = {
        "host_id": user_id,
        "title": body.title,
        "description": body.description,
        "start_datetime": body.start_datetime.isoformat(),
        "end_datetime": body.end_datetime.isoformat(),
        "visibility": body.visibility,
        "is_age_restricted": body.is_age_restricted,
        "attendee_limit": body.attendee_limit,
        "status": body.status,
    }
    event = event_repo.insert_event(db, event_data)
    if not event:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create event")

    event_id = event["id"]

    # Insert related data
    location_rows = [
        {
            "event_id": event_id,
            "name": loc.name,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "is_primary": loc.is_primary,
            "order_index": loc.order_index,
        }
        for loc in body.locations
    ]
    locations = event_repo.insert_locations(db, location_rows)

    cat_rows = [{"event_id": event_id, "category_id": str(cid)} for cid in body.category_ids]
    event_repo.insert_event_categories(db, cat_rows)

    venue_meta = None
    if body.venue_metadata:
        venue_data = {"event_id": event_id, **body.venue_metadata.model_dump()}
        venue_meta = event_repo.insert_venue_metadata(db, venue_data)

    equipment = []
    if body.equipment_requirements:
        equip_rows = [{"event_id": event_id, **eq.model_dump()} for eq in body.equipment_requirements]
        equipment = event_repo.insert_equipment(db, equip_rows)

    categories = event_repo.get_event_categories(db, event_id)

    return _build_detail_response(event, locations, categories, [], venue_meta, equipment)


# --- Helpers ---

def _build_detail_response(
    event: dict,
    locations: list[dict],
    categories: list[dict],
    images: list[dict],
    venue_metadata: dict | None,
    equipment: list[dict],
    is_bookmarked: bool | None = None,
    attendance_status: str | None = None,
    going_count: int | None = None,
    interested_count: int = 0,
) -> EventDetailResponse:
    actual_going = going_count if going_count is not None else event["attendee_count"]
    is_full = None
    if event["attendee_limit"] is not None:
        is_full = actual_going >= event["attendee_limit"]

    return EventDetailResponse(
        id=event["id"],
        host_id=event["host_id"],
        title=event["title"],
        description=event["description"],
        start_datetime=event["start_datetime"],
        end_datetime=event["end_datetime"],
        visibility=event["visibility"],
        is_age_restricted=event["is_age_restricted"],
        attendee_limit=event["attendee_limit"],
        attendee_count=event["attendee_count"],
        status=event["status"],
        created_at=event["created_at"],
        updated_at=event["updated_at"],
        is_bookmarked=is_bookmarked,
        attendance_status=attendance_status,
        going_count=actual_going,
        interested_count=interested_count,
        is_full=is_full,
        locations=locations,
        categories=categories,
        images=images,
        venue_metadata=venue_metadata,
        equipment_requirements=equipment,
    )


def _build_limited_response(
    event: dict, categories: list[dict], is_bookmarked: bool | None = None
) -> EventLimitedResponse:
    return EventLimitedResponse(
        id=event["id"],
        title=event["title"],
        start_datetime=event["start_datetime"],
        end_datetime=event["end_datetime"],
        visibility=event["visibility"],
        is_age_restricted=event["is_age_restricted"],
        status=event["status"],
        is_bookmarked=is_bookmarked,
        categories=categories,
    )


# --- Read ---

def get_event_detail(
    db: Client, event_id: str, user_id: str | None = None,
) -> EventDetailResponse | EventLimitedResponse:
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Lazy auto-end
    event = auto_end_event_if_past(db, event)

    # Draft events are only visible to the host
    if event["status"] == "draft" and (not user_id or event["host_id"] != user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    is_bookmarked = None
    attendance_status = None
    if user_id:
        bookmark = bookmark_repo.get_bookmark(db, user_id, event_id)
        if bookmark:
            is_bookmarked = True
        else:
            is_bookmarked = False

        attendance = attendance_repo.get_attendance(db, user_id, event_id)
        if attendance:
            attendance_status = attendance["status"]

    interested_count = attendance_repo.get_interested_count_for_event(db, event_id)

    # Cancelled events show limited info with cancellation label
    if event["status"] == "cancelled" and (not user_id or event["host_id"] != user_id):
        categories = event_repo.get_event_categories(db, event_id)
        return _build_limited_response(event, categories, is_bookmarked)

    categories = event_repo.get_event_categories(db, event_id)

    # Guest (no user_id) → limited preview
    if not user_id:
        return _build_limited_response(event, categories, is_bookmarked)

    # Private event → host and granted users see full detail
    if event["visibility"] == "private" and event["host_id"] != user_id:
        from app.repositories import invite as invite_repo
        grant = invite_repo.get_access_grant(db, event_id, user_id)
        if not grant:
            return _build_limited_response(event, categories, is_bookmarked)

    # Age restriction check (host is always exempt)
    if event["is_age_restricted"] and user_id and event["host_id"] != user_id:
        dob_str = user_repo.get_user_date_of_birth(db, user_id)
        if not dob_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Date of birth is required to view age-restricted events",
            )
        dob = datetime.fromisoformat(dob_str).date()
        today = datetime.now(UTC).date()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be 18 or older to view this event",
            )

    # Full detail
    locations = event_repo.get_event_locations(db, event_id)
    images = event_repo.get_event_images(db, event_id)
    venue_metadata = event_repo.get_venue_metadata(db, event_id)
    equipment = event_repo.get_equipment(db, event_id)

    return _build_detail_response(
        event, locations, categories, images, venue_metadata, equipment,
        is_bookmarked=is_bookmarked,
        attendance_status=attendance_status,
        going_count=event["attendee_count"],
        interested_count=interested_count
    )


# --- Update ---

def update_event(
    db: Client, event_id: str, user_id: str, body: EventUpdateRequest,
) -> EventDetailResponse:
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Only host can update
    if event["host_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can update this event")

    # Cannot update cancelled/ended events
    if event["status"] in ("cancelled", "ended"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot update a {event['status']} event")

    # Build update dict from non-None fields
    update_data = {}
    for field in ("title", "description", "visibility", "is_age_restricted", "attendee_limit"):
        value = getattr(body, field)
        if value is not None:
            update_data[field] = value

    # Handle clearing attendee limit (set to unlimited)
    if body.clear_attendee_limit:
        update_data["attendee_limit"] = None

    # Check if event has started — time/location changes restricted
    event_started = _parse_stored_datetime(event["start_datetime"]) < datetime.now(UTC)

    if body.start_datetime is not None or body.end_datetime is not None:
        if event_started:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify time after event has started",
            )
        new_start = body.start_datetime or _parse_stored_datetime(event["start_datetime"])
        new_end = body.end_datetime or _parse_stored_datetime(event["end_datetime"])
        validate_event_datetime(new_start, new_end)
        if body.start_datetime:
            update_data["start_datetime"] = body.start_datetime.isoformat()
        if body.end_datetime:
            update_data["end_datetime"] = body.end_datetime.isoformat()

    if body.locations is not None:
        if event_started:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify locations after event has started",
            )
        # Replace locations
        event_repo.delete_event_locations(db, event_id)
        location_rows = [
            {
                "event_id": event_id,
                "name": loc.name,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "is_primary": loc.is_primary,
                "order_index": loc.order_index,
            }
            for loc in body.locations
        ]
        event_repo.insert_locations(db, location_rows)

    if body.category_ids is not None:
        category_id_strs = [str(cid) for cid in body.category_ids]
        validate_categories_exist(db, category_id_strs)
        event_repo.delete_event_categories(db, event_id)
        cat_rows = [{"event_id": event_id, "category_id": str(cid)} for cid in body.category_ids]
        event_repo.insert_event_categories(db, cat_rows)

    if body.venue_metadata is not None:
        event_repo.delete_venue_metadata(db, event_id)
        venue_data = {"event_id": event_id, **body.venue_metadata.model_dump()}
        event_repo.insert_venue_metadata(db, venue_data)

    if body.equipment_requirements is not None:
        event_repo.delete_equipment(db, event_id)
        equip_rows = [{"event_id": event_id, **eq.model_dump()} for eq in body.equipment_requirements]
        event_repo.insert_equipment(db, equip_rows)

    # Set status to "updated" if currently published
    has_real_changes = bool(update_data) or body.locations is not None or body.category_ids is not None or body.venue_metadata is not None or body.equipment_requirements is not None
    if event["status"] == "published" and has_real_changes:
        update_data["status"] = "updated"

    if update_data:
        event_repo.update_event(db, event_id, update_data)

    # Emit notification only if there were real changes
    if has_real_changes and event["status"] in ("published", "updated"):
        from app.services.notification_emitter import emit_event_notification
        updated_event = event_repo.get_event_by_id(db, event_id)
        emit_event_notification(
            db, event_id, user_id, "event_updated",
            f"Event '{updated_event['title']}' has been updated",
        )

    # Return fresh detail
    return get_event_detail(db, event_id, user_id)


# --- Status change ---

VALID_STATUS_TRANSITIONS = {
    "draft": ["published"],
    "published": ["cancelled", "ended"],
    "updated": ["cancelled", "ended"],
}


def change_event_status(
    db: Client, event_id: str, user_id: str, new_status: str,
) -> EventDetailResponse:
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event["host_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can change event status")

    current = event["status"]
    allowed = VALID_STATUS_TRANSITIONS.get(current, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from '{current}' to '{new_status}'. Allowed: {allowed}",
        )

    # draft → published: check required fields and validate datetime
    if current == "draft" and new_status == "published":
        start = _parse_stored_datetime(event["start_datetime"])
        if start <= datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot publish an event with a start time in the past",
            )
        locations = event_repo.get_event_locations(db, event_id)
        if not locations:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event must have at least one location to publish")
        categories = event_repo.get_event_categories(db, event_id)
        if not categories:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event must have at least one category to publish")
        images = event_repo.get_event_images(db, event_id)
        if not images:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event must have at least one image to publish")

    event_repo.update_event_status(db, event_id, new_status)

    # Emit notification on cancellation
    if new_status == "cancelled":
        from app.services.notification_emitter import emit_event_notification
        emit_event_notification(
            db, event_id, user_id, "event_cancelled",
            f"Event '{event['title']}' has been cancelled",
        )

    return get_event_detail(db, event_id, user_id)


# --- Delete ---

def delete_event(db: Client, event_id: str, user_id: str) -> None:
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event["host_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can delete this event")

    if event["status"] not in ("cancelled", "ended"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only cancelled or ended events can be deleted",
        )

    # Clean up storage images before DB delete (CASCADE will remove DB records)
    images = image_repo.get_all_event_images(db, event_id)
    for img in images:
        try:
            path = img["image_url"].split(f"/{image_repo.BUCKET_NAME}/")[-1]
            image_repo.delete_from_storage(db, path)
        except Exception:
            pass  # Best-effort storage cleanup

    event_repo.delete_event(db, event_id)


# --- Discovery ---

def list_events(
    db: Client,
    *,
    user_id: str | None = None,
    search: str | None = None,
    category_id: str | None = None,
    temporal_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> EventListResponse:
    events, total = event_repo.list_events(
        db,
        search=search,
        category_id=category_id,
        temporal_filter=temporal_filter,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    if not events:
        return EventListResponse(items=[], total=total, page=page, page_size=page_size, total_pages=total_pages)

    event_ids = [e["id"] for e in events]
    locations_by_event = event_repo.get_primary_locations_for_events(db, event_ids)
    categories_by_event = event_repo.get_categories_for_events(db, event_ids)
    images_by_event = event_repo.get_primary_images_for_events(db, event_ids)

    is_bookmarked_map = set()
    if user_id:
        is_bookmarked_map = bookmark_repo.get_bookmark_status_for_events(db, user_id, event_ids)

    interested_counts = attendance_repo.get_interested_counts_for_events(db, event_ids)

    items = []
    for event in events:
        is_private = event["visibility"] == "private"
        # Discovery previews stay limited for private events and guests.
        show_preview_details = user_id is not None and not is_private
        items.append(EventListItemResponse(
            id=event["id"],
            host_id=event["host_id"],
            title=event["title"],
            description=event["description"] if show_preview_details else None,
            start_datetime=event["start_datetime"],
            end_datetime=event["end_datetime"],
            visibility=event["visibility"],
            is_age_restricted=event["is_age_restricted"],
            attendee_limit=event["attendee_limit"],
            attendee_count=event["attendee_count"],
            status=event["status"],
            is_bookmarked=(event["id"] in is_bookmarked_map) if user_id else None,
            going_count=event["attendee_count"],
            interested_count=interested_counts.get(event["id"], 0),
            is_full=(event["attendee_count"] >= event["attendee_limit"]) if event["attendee_limit"] is not None else None,
            categories=categories_by_event.get(event["id"], []),
            # Private events: no location in list (venue is private)
            # Public events: location visible to all (needed for map view)
            primary_location=locations_by_event.get(event["id"]) if not is_private else None,
            primary_image_url=images_by_event.get(event["id"]),
        ))

    return EventListResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)
