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
