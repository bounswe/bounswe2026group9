"""Attendance service — business logic for event attendance."""

import base64
import hashlib
import hmac as _hmac
import json
import time
from datetime import UTC, datetime

from fastapi import HTTPException, status
from supabase import Client

from app.config import settings
from app.models.attendance import (
    AttendanceResponse,
    AttendeeStatusItem,
    CheckInRequest,
    CheckInResultResponse,
    QrTokenResponse,
)
from app.repositories import attendance as _attendance_repo
from app.repositories import event as _event_repo
from app.repositories import user as _user_repo
from app.repositories.protocols import (
    AttendanceRepoProtocol,
    EventRepoProtocol,
    UserRepoProtocol,
)

# ── Token helpers ─────────────────────────────────────────────────────────────

def _generate_check_in_token(event_id: str, user_id: str) -> str:
    """Return a compact HMAC-SHA256-signed QR payload.

    Format: base64url(payload_json).hex_signature
    The payload carries event_id and user_id so the host-side validator
    can detect wrong-event scans without a database round-trip.
    """
    payload = json.dumps(
        {"eid": event_id, "uid": user_id, "iat": int(time.time())},
        separators=(",", ":")
    ).encode()
    b64 = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    sig = _hmac.new(settings.JWT_SECRET.encode(), b64.encode(), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


def _verify_check_in_token(token: str) -> dict | None:
    """Decode and verify a check-in token.

    Returns the payload dict on success, None if the signature is invalid
    or the token is malformed.  Timing-safe comparison prevents side-channel
    attacks.
    """
    parts = token.split(".", 1)
    if len(parts) != 2:
        return None
    b64, sig = parts
    expected = _hmac.new(settings.JWT_SECRET.encode(), b64.encode(), hashlib.sha256).hexdigest()
    if not _hmac.compare_digest(expected, sig):
        return None
    try:
        padding = "=" * (4 - len(b64) % 4)
        return json.loads(base64.urlsafe_b64decode(b64 + padding))
    except Exception:
        return None


# ── Core attendance logic ─────────────────────────────────────────────────────

def set_attendance(
    db: Client,
    event_id: str,
    user_id: str,
    target_status: str,
    *,
    attendances: AttendanceRepoProtocol = _attendance_repo,
    events: EventRepoProtocol = _event_repo,
    users: UserRepoProtocol = _user_repo,
) -> AttendanceResponse:
    if target_status != "going":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be 'going'",
        )

    event = events.get_event_by_id(db, event_id)
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
        dob_str = users.get_user_date_of_birth(db, user_id)
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

    existing = attendances.get_attendance(db, user_id, event_id)

    # Capacity check only relevant when switching to 'going'
    is_already_going = existing and existing["status"] == "going"
    if not is_already_going and event["attendee_limit"] is not None:
        if event["attendee_count"] >= event["attendee_limit"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Event attendee limit reached",
            )

    token = _generate_check_in_token(event_id, user_id)

    if not existing:
        att = attendances.insert_attendance(db, {
            "user_id": user_id,
            "event_id": event_id,
            "status": target_status,
            "check_in_token": token,
        })
    elif existing["status"] != target_status:
        att = attendances.update_attendance(db, user_id, event_id, target_status)
        att = attendances.update_attendance_token(db, user_id, event_id, token)
    else:
        # Already going — keep existing token (idempotent)
        att = existing

    return AttendanceResponse(
        id=att["id"],
        event_id=att["event_id"],
        user_id=att["user_id"],
        status=att["status"],
        marked_at=att["marked_at"]
    )


def remove_attendance(
    db: Client,
    event_id: str,
    user_id: str,
    *,
    attendances: AttendanceRepoProtocol = _attendance_repo,
) -> None:
    existing = attendances.get_attendance(db, user_id, event_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance not found")

    attendances.delete_attendance(db, user_id, event_id)


# ── QR / check-in ─────────────────────────────────────────────────────────────

def get_my_qr(
    db: Client,
    event_id: str,
    user_id: str,
    *,
    attendances: AttendanceRepoProtocol = _attendance_repo,
    events: EventRepoProtocol = _event_repo,
) -> QrTokenResponse:
    """Return the signed QR token for the authenticated Going user."""
    attendance = attendances.get_attendance(db, user_id, event_id)
    if not attendance or attendance["status"] != "going":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not going to this event",
        )

    token = attendance.get("check_in_token")
    if not token:
        # Backfill: attendance predates the QR feature — generate now.
        token = _generate_check_in_token(event_id, user_id)
        attendances.update_attendance_token(db, user_id, event_id, token)

    event = events.get_event_by_id(db, event_id)
    expires_at = datetime.fromisoformat(event["end_datetime"]) if event else None

    return QrTokenResponse(token=token, expires_at=expires_at)


def check_in(
    db: Client,
    event_id: str,
    host_user_id: str,
    body: CheckInRequest,
    *,
    attendances: AttendanceRepoProtocol = _attendance_repo,
    events: EventRepoProtocol = _event_repo,
    users: UserRepoProtocol = _user_repo,
) -> CheckInResultResponse:
    """Validate a QR scan or manual user_id and mark the attendee as checked in."""
    event = events.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event["host_id"] != host_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the event host can check in attendees",
        )

    if event["status"] not in ("published", "updated"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-in is only available for active events",
        )

    if body.token is not None:
        attendance = _resolve_by_token(body.token, event_id, db, attendances)
    elif body.user_id is not None:
        attendance = _resolve_by_user_id(str(body.user_id), event_id, db, attendances)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'token' or 'user_id'",
        )

    if attendance["checked_in_at"] is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Attendee already checked in",
        )

    updated = attendances.mark_checked_in(db, attendance["id"])
    user = users.get_user_by_id(db, attendance["user_id"])

    return CheckInResultResponse(
        user_id=updated["user_id"],
        username=user["username"] if user else attendance["user_id"],
        checked_in_at=updated["checked_in_at"],
    )


def _resolve_by_token(
    token: str, event_id: str, db: Client, attendances: AttendanceRepoProtocol
) -> dict:
    """Decode the signed token and return the attendance row, raising on any validation failure."""
    payload = _verify_check_in_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid QR code",
        )

    if payload.get("eid") != event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="QR code is for a different event",
        )

    attendance = attendances.get_attendance_by_token(db, token)
    if not attendance or attendance["status"] != "going":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendee is not on the Going list",
        )
    return attendance


def _resolve_by_user_id(
    user_id: str, event_id: str, db: Client, attendances: AttendanceRepoProtocol
) -> dict:
    """Return the going attendance for user_id, raising 404 if not found."""
    attendance = attendances.get_attendance(db, user_id, event_id)
    if not attendance or attendance["status"] != "going":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attendee is not on the Going list",
        )
    return attendance


def list_event_attendees(
    db: Client,
    event_id: str,
    host_user_id: str,
    *,
    attendances: AttendanceRepoProtocol = _attendance_repo,
    events: EventRepoProtocol = _event_repo,
) -> list[AttendeeStatusItem]:
    """Return the full going-attendee roster for the host."""
    event = events.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event["host_id"] != host_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the event host can view the attendee list",
        )

    rows = attendances.list_going_attendees_with_checkin(db, event_id)
    return [
        AttendeeStatusItem(
            user_id=row["user_id"],
            username=row["username"],
            checked_in_at=row["checked_in_at"],
        )
        for row in rows
    ]
