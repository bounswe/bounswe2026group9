"""Profile service — business logic for user profiles."""

from fastapi import HTTPException, status
from supabase import Client

from app.models.event import EventListItemResponse
from app.models.profile import HostProfileResponse, ProfileUpdateRequest
from app.models.user import UserResponse
from app.repositories import attendance as _attendance_repo
from app.repositories import event as _event_repo
from app.repositories import profile as _profile_repo
from app.repositories import rating as _rating_repo
from app.repositories.protocols import (
    AttendanceRepoProtocol,
    EventRepoProtocol,
    ProfileRepoProtocol,
    RatingRepoProtocol,
)


def get_host_profile(
    db: Client,
    target_user_id: str,
    current_user_id: str | None = None,
    *,
    profiles: ProfileRepoProtocol = _profile_repo,
    ratings: RatingRepoProtocol = _rating_repo,
    events: EventRepoProtocol = _event_repo,
    attendances: AttendanceRepoProtocol = _attendance_repo,
) -> HostProfileResponse:
    user = profiles.get_full_user_profile(db, target_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Get rating stats
    rating_stats = ratings.get_host_rating_stats(db, target_user_id)

    # Only include drafts if the current user is viewing their own profile
    is_owner = current_user_id == target_user_id
    hosted = profiles.get_hosted_events(db, target_user_id, include_drafts=is_owner)

    # Order upcoming events first (asc by start) then past events (most recent ended first).
    upcoming = [e for e in hosted if e.get("status") != "ended"]
    past = [e for e in hosted if e.get("status") == "ended"]
    upcoming.sort(key=lambda e: e["start_datetime"])
    past.sort(key=lambda e: e["start_datetime"], reverse=True)
    ordered = upcoming + past
    event_ids = [e["id"] for e in ordered]

    locations_by_event = events.get_primary_locations_for_events(db, event_ids)
    categories_by_event = events.get_categories_for_events(db, event_ids)
    images_by_event = events.get_primary_images_for_events(db, event_ids)

    items = []
    for event in ordered:
        is_private = event["visibility"] == "private"
        show_description = current_user_id is not None and not is_private

        items.append(EventListItemResponse(
            id=event["id"],
            host_id=event["host_id"],
            title=event["title"],
            description=event["description"] if show_description else None,
            start_datetime=event["start_datetime"],
            end_datetime=event["end_datetime"],
            visibility=event["visibility"],
            is_age_restricted=event["is_age_restricted"],
            attendee_limit=event["attendee_limit"],
            attendee_count=event["attendee_count"],
            status=event["status"],
            categories=categories_by_event.get(event["id"], []),
            primary_location=locations_by_event.get(event["id"]),
            primary_image_url=images_by_event.get(event["id"]),
        ))

    email = None
    if user.get("email_visibility") is True:
        email = user.get("email")

    phone_number = None
    if user.get("phone_visibility") is True:
        phone_number = user.get("phone_number")

    can_rate = (
        current_user_id is not None
        and not is_owner
        and attendances.has_attended_ended_event_by_host(db, current_user_id, target_user_id)
    )

    return HostProfileResponse(
        id=user["id"],
        username=user["username"],
        email=email,
        phone_number=phone_number,
        average_rating=rating_stats["average"],
        hosted_events_count=len(items),
        hosted_events=items,
        can_rate=can_rate,
    )


def update_profile(
    db: Client,
    user_id: str,
    req: ProfileUpdateRequest,
    *,
    profiles: ProfileRepoProtocol = _profile_repo,
) -> UserResponse:
    update_data = {}
    for field in (
        "date_of_birth", "phone_number", "email_visibility", "phone_visibility",
        "default_location_name", "default_location_lat", "default_location_lng",
    ):
        val = getattr(req, field, None)
        if val is not None:
            if field == "date_of_birth":
                update_data[field] = val.isoformat()
            elif field in ("email_visibility", "phone_visibility"):
                update_data[field] = (val == "public")
            else:
                update_data[field] = val

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields provided for update"
        )

    user = profiles.update_user_profile(db, user_id, update_data)
    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        phone_number=user.get("phone_number"),
        date_of_birth=user.get("date_of_birth"),
        email_visibility=user.get("email_visibility", False),
        phone_visibility=user.get("phone_visibility", False),
        role=user.get("role", "registered"),
        auth_provider=user.get("auth_provider", "local"),
        email_verified=user.get("email_verified", False),
        is_active=user["is_active"],
        created_at=user["created_at"],
        updated_at=user["updated_at"],
    )
