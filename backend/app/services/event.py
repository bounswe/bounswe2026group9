"""Event service — business logic, validation, orchestration."""

import math
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
    SegmentRequest,
    SegmentResponse,
)
from app.models.geojson import (
    EventGeoJSONProperties,
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    GeoJSONPoint,
)
from app.repositories import attendance as _attendance_repo
from app.repositories import bookmark as _bookmark_repo
from app.repositories import event as _event_repo
from app.repositories import image as _image_repo
from app.repositories import invite as _invite_repo
from app.repositories import user as _user_repo
from app.repositories.protocols import (
    AttendanceRepoProtocol,
    BookmarkRepoProtocol,
    EventRepoProtocol,
    ImageRepoProtocol,
    InviteRepoProtocol,
    UserRepoProtocol,
)
from app.services.rate_limit import is_rate_limit_exempt_email

# Aliases kept for the (still-large) parts of this module that haven't been
# DI-converted yet. Phase 1 slice A converts the validators + helpers; the
# CRUD and read-side functions get their own slices and switch to kwargs.
attendance_repo = _attendance_repo
bookmark_repo = _bookmark_repo
event_repo = _event_repo
image_repo = _image_repo
invite_repo = _invite_repo
user_repo = _user_repo


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometres between two (lat, lng) points."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


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


def validate_categories_exist(
    db: Client,
    category_ids: list[str],
    *,
    events: EventRepoProtocol = _event_repo,
) -> None:
    found_ids = events.get_valid_category_ids(db, category_ids)
    missing = set(category_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or unapproved category IDs: {list(missing)}",
        )


def validate_segments(
    segments: list[SegmentRequest] | None,
    location_count: int,
    event_start: datetime,
    event_end: datetime,
) -> None:
    """Validate itinerary segments against the issue's rules.

    Rules (issue #149):
      1. Each segment.location_index references a real position
         (0 <= location_index < location_count).
      2. Each segment is timezone-aware and end > start.
      3. Each segment lies within [event_start, event_end].
      4. order_index values are contiguous from 0 with no duplicates.
      5. Sorted by order_index, segments do not overlap in time
         (current.start >= previous.end).
    """
    if not segments:
        return

    # 1. location_index in range
    for seg in segments:
        if seg.location_index >= location_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"segment.location_index {seg.location_index} out of range "
                       f"(locations has {location_count} entries)",
            )

    # 2. timezone + inverted time
    for seg in segments:
        _ensure_timezone_aware(seg.start_datetime, "segment.start_datetime")
        _ensure_timezone_aware(seg.end_datetime, "segment.end_datetime")
        if seg.end_datetime <= seg.start_datetime:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="segment end_datetime must be after start_datetime",
            )

    # 3. each segment within event window
    for seg in segments:
        if seg.start_datetime < event_start or seg.end_datetime > event_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="segment must lie within event start_datetime and end_datetime",
            )

    # 4. order_index contiguous from 0
    order_values = sorted(seg.order_index for seg in segments)
    for expected, actual in enumerate(order_values):
        if actual != expected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="segments must have contiguous order_index starting at 0",
            )

    # 5. no time overlaps when sorted by order
    sorted_by_order = sorted(segments, key=lambda s: s.order_index)
    for prev, curr in zip(sorted_by_order, sorted_by_order[1:], strict=False):
        if curr.start_datetime < prev.end_datetime:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="segments must not overlap in time when sorted by order_index",
            )


def _build_segment_rows(segments: list[SegmentRequest] | None) -> list[dict] | None:
    if segments is None:
        return None
    return [
        {
            "location_index": seg.location_index,
            "order_index": seg.order_index,
            "start_datetime": seg.start_datetime.isoformat(),
            "end_datetime": seg.end_datetime.isoformat(),
            "description": seg.description,
        }
        for seg in segments
    ]


def check_duplicate_event(
    db: Client,
    host_id: str,
    title: str,
    start_datetime: str,
    location_name: str,
    *,
    events: EventRepoProtocol = _event_repo,
) -> None:
    """Reject creation when title + start_datetime + *primary* location collide for the same host.

    Issue #149 FRS-2 explicitly scopes this to the primary location. A separate
    event whose primary differs but happens to include `location_name` as a
    non-primary stop is allowed.
    """
    duplicates = events.find_duplicate_events(db, host_id, title, start_datetime)
    for event in duplicates:
        locations = events.find_location_by_event_and_name(db, event["id"], location_name)
        if locations:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A similar event already exists with the same title, time, and primary location",
            )


def check_rate_limit(
    db: Client,
    host_id: str,
    *,
    events: EventRepoProtocol = _event_repo,
    users: UserRepoProtocol = _user_repo,
) -> None:
    host_email = users.get_user_email_by_id(db, host_id)
    if is_rate_limit_exempt_email(host_email):
        return

    config = events.get_rate_limit_config(db)
    if not config:
        return

    max_events = config["max_events_per_user"]
    window_hours = config["time_window_hours"]
    cutoff = (datetime.now(UTC) - timedelta(hours=window_hours)).isoformat()

    count = events.count_events_by_host_since(db, host_id, cutoff)
    if count >= max_events:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: max {max_events} events per {window_hours} hours",
        )


def auto_end_event_if_past(
    db: Client,
    event: dict,
    *,
    events: EventRepoProtocol = _event_repo,
) -> dict:
    if event["status"] in ("published", "updated"):
        end_dt = _parse_stored_datetime(event["end_datetime"])
        if end_dt < datetime.now(UTC):
            events.update_event_status(db, event["id"], "ended")
            event["status"] = "ended"
    return event


# --- Main operations ---

def create_event(
    db: Client,
    user_id: str,
    body: EventCreateRequest,
    *,
    events: EventRepoProtocol = _event_repo,
    users: UserRepoProtocol = _user_repo,
) -> EventDetailResponse:
    # Validations
    validate_event_datetime(body.start_datetime, body.end_datetime)

    category_id_strs = [str(cid) for cid in body.category_ids]
    validate_categories_exist(db, category_id_strs, events=events)

    primary_location = next((loc for loc in body.locations if loc.is_primary), body.locations[0])
    check_duplicate_event(
        db, user_id, body.title, body.start_datetime.isoformat(), primary_location.name,
        events=events,
    )
    check_rate_limit(db, user_id, events=events, users=users)

    # Cannot publish directly on create — images must be uploaded first
    if body.status == "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot publish directly on create. Create as draft, upload images, then publish via PATCH status.",
        )

    has_primary = any(loc.is_primary for loc in body.locations)
    if not has_primary:
        body.locations[0].is_primary = True

    # Itinerary segments (optional)
    validate_segments(
        body.segments, len(body.locations), body.start_datetime, body.end_datetime,
    )
    segment_rows = _build_segment_rows(body.segments)

    # Build atomic insert params
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

    location_rows = [
        {
            "name": loc.name,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "is_primary": loc.is_primary,
            "order_index": loc.order_index,
            "location_address": loc.location_address,
        }
        for loc in body.locations
    ]

    venue_data = None
    if body.venue_metadata:
        venue_data = body.venue_metadata.model_dump()

    equip_data = None
    if body.equipment_requirements:
        equip_data = [eq.model_dump() for eq in body.equipment_requirements]

    # Single-transaction insert via RPC
    event = events.create_event_atomic(
        db,
        event_data=event_data,
        locations=location_rows,
        category_ids=category_id_strs,
        venue_metadata=venue_data,
        equipment=equip_data,
        segments=segment_rows,
    )
    if not event:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create event")

    event_id = event["id"]

    # Fetch related data for response
    locations = events.get_event_locations(db, event_id)
    categories = events.get_event_categories(db, event_id)
    venue_meta = events.get_venue_metadata(db, event_id)
    equipment = events.get_equipment(db, event_id)
    segments = events.get_event_segments(db, event_id)

    return _build_detail_response(
        event, locations, categories, [], venue_meta, equipment, segments=segments,
    )


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
    bookmark_count: int = 0,
    access_request_status: str | None = None,
    attendees: list[dict] | None = None,
    host_username: str = "",
    segments: list[dict] | None = None,
) -> EventDetailResponse:
    actual_going = going_count if going_count is not None else event["attendee_count"]
    is_full = None
    if event["attendee_limit"] is not None:
        is_full = actual_going >= event["attendee_limit"]

    segment_rows = segments or []
    segment_responses = [
        SegmentResponse(
            id=row["id"],
            location_id=row["location_id"],
            order_index=row["order_index"],
            start_datetime=row["start_datetime"],
            end_datetime=row["end_datetime"],
            description=row.get("description"),
        )
        for row in segment_rows
    ]

    return EventDetailResponse(
        id=event["id"],
        host_id=event["host_id"],
        host_username=host_username,
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
        bookmark_count=bookmark_count,
        is_full=is_full,
        access_request_status=access_request_status,
        locations=locations,
        categories=categories,
        images=images,
        venue_metadata=venue_metadata,
        equipment_requirements=equipment,
        attendees=attendees or [],
        segments=segment_responses,
    )


def _build_limited_response(
    event: dict,
    categories: list[dict],
    is_bookmarked: bool | None = None,
    access_request_status: str | None = None,
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
        access_request_status=access_request_status,
        categories=categories,
    )


# --- Read ---

def get_event_detail(
    db: Client,
    event_id: str,
    user_id: str | None = None,
    *,
    events: EventRepoProtocol = _event_repo,
    users: UserRepoProtocol = _user_repo,
    bookmarks: BookmarkRepoProtocol = _bookmark_repo,
    attendances: AttendanceRepoProtocol = _attendance_repo,
    invites: InviteRepoProtocol = _invite_repo,
) -> EventDetailResponse | EventLimitedResponse:
    event = events.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    # Lazy auto-end
    event = auto_end_event_if_past(db, event, events=events)

    # Draft events are only visible to the host
    if event["status"] == "draft" and (not user_id or event["host_id"] != user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    is_bookmarked = None
    attendance_status = None
    access_request_status = None
    has_access_grant = False
    if user_id:
        bookmark = bookmarks.get_bookmark(db, user_id, event_id)
        if bookmark:
            is_bookmarked = True
        else:
            is_bookmarked = False

        attendance = attendances.get_attendance(db, user_id, event_id)
        if attendance:
            attendance_status = attendance["status"]

        access_request = invites.get_access_request(db, event_id, user_id)
        if access_request:
            access_request_status = access_request["status"]
        if event["visibility"] == "private" and event["host_id"] != user_id:
            has_access_grant = invites.get_access_grant(db, event_id, user_id) is not None

    bookmark_count = bookmarks.get_bookmark_count_for_event(db, event_id)

    # Cancelled events show limited info with cancellation label
    if event["status"] == "cancelled" and (not user_id or event["host_id"] != user_id):
        categories = events.get_event_categories(db, event_id)
        return _build_limited_response(
            event,
            categories,
            is_bookmarked,
            access_request_status=access_request_status,
        )

    categories = events.get_event_categories(db, event_id)

    # Guest (no user_id) → limited preview
    if not user_id:
        return _build_limited_response(event, categories, is_bookmarked)

    # Private event → host and granted users see full detail
    if event["visibility"] == "private" and event["host_id"] != user_id:
        if not has_access_grant:
            return _build_limited_response(
                event,
                categories,
                is_bookmarked,
                access_request_status=access_request_status,
            )

    # Age restriction check (host is always exempt)
    if event["is_age_restricted"] and user_id and event["host_id"] != user_id:
        dob_str = users.get_user_date_of_birth(db, user_id)
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
    locations = events.get_event_locations(db, event_id)
    images = events.get_event_images(db, event_id)
    venue_metadata = events.get_venue_metadata(db, event_id)
    equipment = events.get_equipment(db, event_id)
    segments = events.get_event_segments(db, event_id)
    attendee_ids = attendances.get_going_user_ids_for_event(db, event_id)
    attendee_users = users.get_users_by_ids(db, attendee_ids)
    attendee_usernames = {
        attendee["id"]: attendee.get("username", "unknown")
        for attendee in attendee_users
    }
    attendees = [
        {"id": attendee_id, "username": attendee_usernames.get(attendee_id, "unknown")}
        for attendee_id in attendee_ids
    ]

    host = users.get_user_by_id(db, str(event["host_id"]))
    host_username = host["username"] if host else ""

    return _build_detail_response(
        event, locations, categories, images, venue_metadata, equipment,
        is_bookmarked=is_bookmarked,
        attendance_status=attendance_status,
        going_count=event["attendee_count"],
        bookmark_count=bookmark_count,
        access_request_status=access_request_status,
        attendees=attendees,
        host_username=host_username,
        segments=segments,
    )


# --- Update ---

def update_event(
    db: Client,
    event_id: str,
    user_id: str,
    body: EventUpdateRequest,
    *,
    events: EventRepoProtocol = _event_repo,
) -> EventDetailResponse:
    event = events.get_event_by_id(db, event_id)
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

    # Itinerary segments — same lifecycle constraint as time/locations (FRS-2)
    if body.segments is not None and event_started:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify segments after event has started",
        )

    if body.segments is not None:
        # Validate against the *effective* locations and event window.
        # body fields shadow stored values when provided; otherwise fall back to DB.
        if body.locations is not None:
            effective_location_count = len(body.locations)
        else:
            effective_location_count = len(events.get_event_locations(db, event_id))

        effective_start = body.start_datetime or _parse_stored_datetime(event["start_datetime"])
        effective_end = body.end_datetime or _parse_stored_datetime(event["end_datetime"])
        validate_segments(
            body.segments, effective_location_count, effective_start, effective_end,
        )

    if body.category_ids is not None:
        category_id_strs = [str(cid) for cid in body.category_ids]
        validate_categories_exist(db, category_id_strs, events=events)

    # Set status to "updated" if currently published
    has_real_changes = (
        bool(update_data)
        or body.locations is not None
        or body.category_ids is not None
        or body.venue_metadata is not None
        or body.equipment_requirements is not None
        or body.segments is not None
    )
    if event["status"] == "published" and has_real_changes:
        update_data["status"] = "updated"

    # Build atomic update params
    location_rows = None
    if body.locations is not None:
        location_rows = [
            {
                "name": loc.name,
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "is_primary": loc.is_primary,
                "order_index": loc.order_index,
                "location_address": loc.location_address,
            }
            for loc in body.locations
        ]

    cat_id_strs = None
    if body.category_ids is not None:
        cat_id_strs = [str(cid) for cid in body.category_ids]

    venue_data = None
    if body.venue_metadata is not None:
        venue_data = body.venue_metadata.model_dump()

    equip_data = None
    if body.equipment_requirements is not None:
        equip_data = [eq.model_dump() for eq in body.equipment_requirements]

    segment_rows = _build_segment_rows(body.segments)

    # Replacing locations CASCADEs through event_segments.location_id, so
    # require the caller to re-send segments alongside locations (or send []
    # to explicitly clear them) — silent loss is worse than a clear error.
    if body.locations is not None and body.segments is None:
        existing_segments = events.get_event_segments(db, event_id)
        if existing_segments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Updating locations clears existing segments. "
                       "Re-send `segments` (or [] to clear) along with `locations`.",
            )

    # Single-transaction update via RPC
    if has_real_changes or update_data:
        events.update_event_atomic(
            db,
            event_id=event_id,
            event_data=update_data if update_data else None,
            locations=location_rows,
            category_ids=cat_id_strs,
            venue_metadata=venue_data,
            equipment=equip_data,
            segments=segment_rows,
        )

    # Emit notification only if there were real changes
    if has_real_changes and event["status"] in ("published", "updated"):
        from app.services.notification_emitter import emit_event_notification
        updated_event = events.get_event_by_id(db, event_id)
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
    db: Client,
    event_id: str,
    user_id: str,
    new_status: str,
    *,
    events: EventRepoProtocol = _event_repo,
) -> EventDetailResponse:
    event = events.get_event_by_id(db, event_id)
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
        locations = events.get_event_locations(db, event_id)
        if not locations:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event must have at least one location to publish")
        categories = events.get_event_categories(db, event_id)
        if not categories:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event must have at least one category to publish")
        images = events.get_event_images(db, event_id)
        if not images:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event must have at least one image to publish")

    events.update_event_status(db, event_id, new_status)

    # Emit recommendation notifications when an event becomes published
    if current == "draft" and new_status == "published":
        try:
            from app.services.recommendation_emitter import emit_event_recommendations
            emit_event_recommendations(db, event_id, user_id)
        except Exception:
            # Recommendations are best-effort: never fail the publish on emitter error
            import logging
            logging.getLogger(__name__).exception("emit_event_recommendations failed")

    # Emit notification on cancellation
    if new_status == "cancelled":
        from app.services.notification_emitter import emit_event_notification
        emit_event_notification(
            db, event_id, user_id, "event_cancelled",
            f"Event '{event['title']}' has been cancelled",
        )

    return get_event_detail(db, event_id, user_id)


# --- Delete ---

def delete_event(
    db: Client,
    event_id: str,
    user_id: str,
    *,
    events: EventRepoProtocol = _event_repo,
    images: ImageRepoProtocol = _image_repo,
) -> None:
    event = events.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event["host_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can delete this event")

    if event["status"] not in ("cancelled", "ended"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only cancelled or ended events can be deleted",
        )

    # Emit event_deleted notification *before* the row is removed.
    # _get_affected_user_ids reads bookmarks + 'going' attendances, both of
    # which CASCADE on event delete — so this must run first. The
    # notifications.event_id FK is ON DELETE SET NULL, so the rows survive
    # the subsequent delete with event_id cleared.
    from app.services.notification_emitter import emit_event_notification
    emit_event_notification(
        db, event_id, user_id, "event_deleted",
        f"Event '{event['title']}' has been deleted by the host",
    )

    # Clean up storage images before DB delete (CASCADE will remove DB records)
    event_images = images.get_all_event_images(db, event_id)
    for img in event_images:
        try:
            path = img["image_url"].split(f"/{images.BUCKET_NAME}/")[-1]
            images.delete_from_storage(db, path)
        except Exception:
            pass  # Best-effort storage cleanup

    events.delete_event(db, event_id)


# --- Discovery ---

def list_events(
    db: Client,
    *,
    user_id: str | None = None,
    search: str | None = None,
    category_id: str | None = None,
    quick_filter: str | None = None,
    start_after: datetime | None = None,
    end_before: datetime | None = None,
    near_lat: float | None = None,
    near_lng: float | None = None,
    radius_km: float | None = None,
    use_default_area: bool = False,
    accessibility: dict[str, bool | None] | None = None,
    sort: str | None = None,
    suggested: bool = False,
    page: int = 1,
    page_size: int = 20,
    events: EventRepoProtocol = _event_repo,
    users: UserRepoProtocol = _user_repo,
    bookmarks: BookmarkRepoProtocol = _bookmark_repo,
    attendances: AttendanceRepoProtocol = _attendance_repo,
    invites: InviteRepoProtocol = _invite_repo,
) -> EventListResponse:
    # Resolve default-area fallback when client opts in and didn't pass coords.
    if use_default_area and near_lat is None and near_lng is None and user_id:
        default_lat, default_lng = users.get_user_default_area(db, user_id)
        if default_lat is None or default_lng is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No default area set on profile",
            )
        near_lat = default_lat
        near_lng = default_lng

    has_location = near_lat is not None and near_lng is not None
    if sort == "distance" and not has_location:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sort=distance requires near_lat/near_lng or use_default_area",
        )
    # sort=category fetches the full filtered candidate set into memory and
    # ranks in Python (PostgREST cannot order by an aggregated joined column
    # in a single round-trip). To keep memory bounded on large datasets, we
    # require the request to narrow the candidate set first — same shape of
    # constraint as sort=distance requiring a location.
    if sort == "category":
        accessibility_active = any(
            v is True for v in (accessibility or {}).values()
        )
        has_search = bool(search and search.strip())
        has_window = (
            quick_filter is not None
            or start_after is not None
            or end_before is not None
        )
        if not (
            has_search
            or category_id is not None
            or has_window
            or accessibility_active
            or has_location
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "sort=category requires a narrowing filter: search, "
                    "category_id, quick_filter, custom window, accessibility, "
                    "or a location."
                ),
            )
    if sort is None:
        sort = "distance" if has_location else "start_time"

    effective_radius_km = radius_km if radius_km is not None else (50.0 if has_location else None)

    # Resolve "Suggested for you" — only meaningful for authenticated users.
    suggested_category_ids: set[str] | None = None
    suggested_fallback = False
    if suggested and user_id:
        suggested_category_ids = attendances.get_attended_ended_event_categories(
            db, user_id,
        )
        if not suggested_category_ids:
            # User has no attendance history yet — fall back to default listing
            # but signal the empty-history hint to the UI.
            suggested_category_ids = None
            suggested_fallback = True

    event_rows, total = events.list_events(
        db,
        search=search,
        category_id=category_id,
        quick_filter=quick_filter,
        start_after=start_after,
        end_before=end_before,
        near_lat=near_lat,
        near_lng=near_lng,
        radius_km=effective_radius_km,
        accessibility=accessibility or {},
        sort=sort,
        suggested_category_ids=suggested_category_ids,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    if not event_rows:
        return EventListResponse(
            items=[], total=total, page=page, page_size=page_size,
            total_pages=total_pages, suggested_fallback=suggested_fallback,
        )

    # For sort in {distance, category} the repo returned the full filtered set;
    # rank in Python and slice to the requested page.
    if sort in ("distance", "category"):
        if sort == "distance":
            full_event_ids = [e["id"] for e in event_rows]
            locations_by_event = events.get_primary_locations_for_events(db, full_event_ids)

            def _distance_key(ev: dict) -> tuple[float, str]:
                loc = locations_by_event.get(ev["id"])
                if not loc or loc.get("latitude") is None or loc.get("longitude") is None:
                    return (float("inf"), ev["id"])
                return (_haversine_km(near_lat, near_lng, loc["latitude"], loc["longitude"]), ev["id"])

            event_rows.sort(key=_distance_key)
        else:  # category
            full_event_ids = [e["id"] for e in event_rows]
            categories_by_event_full = events.get_categories_for_events(db, full_event_ids)

            def _category_key(ev: dict) -> tuple[str, str, str]:
                cats = categories_by_event_full.get(ev["id"]) or []
                primary = min((c.get("name", "") for c in cats), default="￿")
                return (primary, ev["start_datetime"], ev["id"])

            event_rows.sort(key=_category_key)

        offset = (page - 1) * page_size
        event_rows = event_rows[offset:offset + page_size]
        if not event_rows:
            return EventListResponse(
                items=[], total=total, page=page, page_size=page_size,
                total_pages=total_pages, suggested_fallback=suggested_fallback,
            )

    event_ids = [e["id"] for e in event_rows]
    locations_by_event = events.get_primary_locations_for_events(db, event_ids)
    categories_by_event = events.get_categories_for_events(db, event_ids)
    images_by_event = events.get_primary_images_for_events(db, event_ids)

    is_bookmarked_map: set[str] = set()
    attendance_status_map: dict[str, str] = {}
    access_request_status_map: dict[str, str] = {}
    access_granted_event_ids: set[str] = set()
    if user_id:
        is_bookmarked_map = bookmarks.get_bookmark_status_for_events(db, user_id, event_ids)
        attendance_status_map = attendances.get_attendance_status_for_events(db, user_id, event_ids)
        access_request_status_map = invites.get_access_request_status_for_events(
            db,
            user_id,
            event_ids,
        )
        access_granted_event_ids = invites.get_access_granted_event_ids(
            db,
            user_id,
            event_ids,
        )

    bookmark_counts = bookmarks.get_bookmark_counts_for_events(db, event_ids)

    items = []
    for event in event_rows:
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
            attendance_status=attendance_status_map.get(event["id"]) if user_id else None,
            access_request_status=access_request_status_map.get(event["id"]) if user_id else None,
            has_access=(
                True
                if user_id and event["host_id"] == user_id
                else event["id"] in access_granted_event_ids
            ) if user_id else None,
            going_count=event["attendee_count"],
            bookmark_count=bookmark_counts.get(event["id"], 0),
            is_full=(event["attendee_count"] >= event["attendee_limit"]) if event["attendee_limit"] is not None else None,
            categories=categories_by_event.get(event["id"], []),
            # Location visible to all (needed for map view, even for private events)
            primary_location=locations_by_event.get(event["id"]),
            primary_image_url=images_by_event.get(event["id"]),
        ))

    return EventListResponse(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=total_pages, suggested_fallback=suggested_fallback,
    )


def list_events_geojson(
    db: Client,
    **kwargs,
) -> GeoJSONFeatureCollection:
    """Fetch events using the same filters as list_events and format as GeoJSON.

    This forces page=1 and page_size=2000 to return a comprehensive set of points
    for the map view without requiring the client to iterate pages.
    """
    kwargs["page"] = 1
    kwargs["page_size"] = 2000

    list_response = list_events(db, **kwargs)

    features: list[GeoJSONFeature] = []
    for item in list_response.items:
        # GeoJSON only maps events that have a location
        if not item.primary_location:
            continue

        point = GeoJSONPoint(
            coordinates=[item.primary_location.longitude, item.primary_location.latitude]
        )

        primary_category = item.categories[0].name if item.categories else None

        properties = EventGeoJSONProperties(
            id=item.id,
            host_id=item.host_id,
            title=item.title,
            start_datetime=item.start_datetime.isoformat() if isinstance(item.start_datetime, datetime) else str(item.start_datetime),
            status=item.status,
            visibility=item.visibility,
            primary_category=primary_category,
            attendee_count=item.attendee_count,
            attendee_limit=item.attendee_limit,
            is_bookmarked=item.is_bookmarked,
            attendance_status=item.attendance_status,
            going_count=item.going_count,
            bookmark_count=item.bookmark_count,
            primary_image_url=item.primary_image_url,
        )

        features.append(GeoJSONFeature(geometry=point, properties=properties))

    return GeoJSONFeatureCollection(features=features)


def get_similar_events(
    db: Client,
    event_id: str,
    user_id: str | None = None,
    limit: int = 5,
    *,
    events: EventRepoProtocol = _event_repo,
    bookmarks: BookmarkRepoProtocol = _bookmark_repo,
    invites: InviteRepoProtocol = _invite_repo,
) -> list[EventListItemResponse]:
    """Return up to `limit` scored similar public published/updated future events."""
    source = events.get_event_by_id(db, event_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    source_categories = events.get_event_categories(db, event_id)
    source_cat_ids = {c["id"] for c in source_categories}

    # Source primary location — reuse the batch lookup so we go through the
    # repo seam instead of poking db.table directly.
    source_locs = events.get_primary_locations_for_events(db, [event_id])
    source_loc = source_locs.get(event_id) or {}
    source_lat = source_loc.get("latitude")
    source_lng = source_loc.get("longitude")

    candidates = events.get_similar_candidates(db, event_id, limit=30)
    if not candidates:
        return []

    candidate_ids = [c["id"] for c in candidates]
    cats_by_event = events.get_categories_for_events(db, candidate_ids)
    locs_by_event = events.get_primary_locations_for_events(db, candidate_ids)

    scored = []
    for cand in candidates:
        cid = cand["id"]
        cand_cat_ids = {c["id"] for c in cats_by_event.get(cid, [])}
        overlap = len(source_cat_ids & cand_cat_ids)
        host_match = 1 if cand["host_id"] == source["host_id"] else 0

        proximity_bonus = 0
        if source_lat is not None and source_lng is not None:
            loc = locs_by_event.get(cid)
            if loc and loc.get("latitude") is not None and loc.get("longitude") is not None:
                dist = _haversine_km(source_lat, source_lng, loc["latitude"], loc["longitude"])
                if dist <= 50:
                    proximity_bonus = 1

        score = overlap * 3 + host_match * 2 + proximity_bonus
        scored.append((score, cand))

    scored.sort(key=lambda x: (-x[0], x[1]["start_datetime"], x[1]["id"]))
    top = [c for _, c in scored[:limit]]
    top_ids = [c["id"] for c in top]

    locations_by_event = events.get_primary_locations_for_events(db, top_ids)
    images_by_event = events.get_primary_images_for_events(db, top_ids)
    bookmark_counts = bookmarks.get_bookmark_counts_for_events(db, top_ids)

    # Mirror list_events: private-aware redaction + access state batch lookups.
    is_bookmarked_map: set[str] = set()
    access_request_status_map: dict[str, str] = {}
    access_granted_event_ids: set[str] = set()
    if user_id:
        is_bookmarked_map = bookmarks.get_bookmark_status_for_events(db, user_id, top_ids)
        access_request_status_map = invites.get_access_request_status_for_events(
            db, user_id, top_ids,
        )
        access_granted_event_ids = invites.get_access_granted_event_ids(
            db, user_id, top_ids,
        )

    items = []
    for event in top:
        eid = event["id"]
        is_private = event["visibility"] == "private"
        # Hide description for private events and for guests viewing public
        # events — same teaser rule Discovery uses (`list_events`).
        show_preview_details = user_id is not None and not is_private
        items.append(EventListItemResponse(
            id=eid,
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
            is_bookmarked=(eid in is_bookmarked_map) if user_id else None,
            access_request_status=access_request_status_map.get(eid) if user_id else None,
            has_access=(
                True
                if user_id and event["host_id"] == user_id
                else eid in access_granted_event_ids
            ) if user_id else None,
            going_count=event["attendee_count"],
            bookmark_count=bookmark_counts.get(eid, 0),
            is_full=(event["attendee_count"] >= event["attendee_limit"]) if event["attendee_limit"] is not None else None,
            categories=cats_by_event.get(eid, []),
            # Location visible to all (needed for map view, even private events) — Discovery parity.
            primary_location=locations_by_event.get(eid),
            primary_image_url=images_by_event.get(eid),
        ))

    return items
