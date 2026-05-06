"""Attendance Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict

from app.models.base import AppBaseModel


class AttendanceStatusRequest(AppBaseModel):
    status: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"status": "going"}
        }
    )


class AttendanceResponse(AppBaseModel):
    id: UUID
    event_id: UUID
    user_id: UUID
    status: str
    marked_at: datetime


# ── QR / check-in ─────────────────────────────────────────────────────────────

class QrTokenResponse(AppBaseModel):
    """Returned by GET /attendances/me/{event_id}/qr."""
    token: str
    expires_at: datetime | None = None


class CheckInRequest(AppBaseModel):
    """Body for POST /events/{event_id}/check-in.

    Exactly one of `token` (scanned QR payload) or `user_id` (manual fallback)
    must be provided.
    """
    token: str | None = None
    user_id: UUID | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"token": "<signed-qr-payload>"}
        }
    )


class CheckInResultResponse(AppBaseModel):
    """Returned on a successful check-in (HTTP 200)."""
    user_id: UUID
    username: str
    checked_in_at: datetime


class AttendeeStatusItem(AppBaseModel):
    """One row in GET /events/{event_id}/attendees."""
    user_id: UUID
    username: str
    checked_in_at: datetime | None = None
