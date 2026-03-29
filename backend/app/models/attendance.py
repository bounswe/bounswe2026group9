"""Attendance Pydantic schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AttendanceStatusRequest(BaseModel):
    status: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"status": "going"}
        }
    )


class AttendanceResponse(BaseModel):
    id: UUID
    event_id: UUID
    user_id: UUID
    status: str
    marked_at: datetime
