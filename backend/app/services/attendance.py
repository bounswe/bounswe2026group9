"""Attendance service — business logic for event attendance."""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from supabase import Client

from app.models.attendance import AttendanceResponse
from app.repositories import attendance as attendance_repo
from app.repositories import event as event_repo
from app.repositories import user as user_repo


def set_attendance(db: Client, event_id: str, user_id: str, target_status: str) -> AttendanceResponse:
    if target_status not in ("going", "interested"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be 'going' or 'interested'",
        )

    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event["status"] not in ("published", "updated"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot attend an event that is draft, cancelled, or ended",
        )

    if event["host_id"] == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Host cannot explicitly set attendance on their own event",
        )

    if event["is_age_restricted"]:
        dob_str = user_repo.get_user_date_of_birth(db, user_id)
        if not dob_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Date of birth is required to attend age-restricted events",
            )
        dob = datetime.fromisoformat(dob_str).date()
        today = datetime.now(UTC).date()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 18:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be at least 18 years old to attend this event",
            )

    existing = attendance_repo.get_attendance(db, user_id, event_id)

    # Capacity check only relevant when switching to 'going'
    if target_status == "going":
        # we check if existing is not going to avoid rejecting someone already going
        is_already_going = existing and existing["status"] == "going"
        if not is_already_going and event["attendee_limit"] is not None:
            if event["attendee_count"] >= event["attendee_limit"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Event attendee limit reached",
                )

    if not existing:
        att = attendance_repo.insert_attendance(db, {
            "user_id": user_id,
            "event_id": event_id,
            "status": target_status,
        })
    elif existing["status"] != target_status:
        att = attendance_repo.update_attendance(db, user_id, event_id, target_status)
    else:
        # no change needed
        att = existing

    return AttendanceResponse(
        id=att["id"],
        event_id=att["event_id"],
        user_id=att["user_id"],
        status=att["status"],
        marked_at=att["marked_at"]
    )


def remove_attendance(db: Client, event_id: str, user_id: str) -> None:
    existing = attendance_repo.get_attendance(db, user_id, event_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance not found")

    attendance_repo.delete_attendance(db, user_id, event_id)
