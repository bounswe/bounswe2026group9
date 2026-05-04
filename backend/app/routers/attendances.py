"""Attendance endpoints — HTTP layer only."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.database import get_supabase
from app.middleware.auth import get_current_user_id
from app.models.attendance import AttendanceResponse, AttendanceStatusRequest
from app.models.errors import AUTH_RESPONSES, NOT_FOUND_RESPONSE
from app.models.user import MessageResponse
from app.services.attendance import remove_attendance, set_attendance

router = APIRouter(prefix="/events/{event_id}/attendance", tags=["attendances"])


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    response_model=AttendanceResponse,
    summary="Set attendance status",
    description="Idempotent — repeating with the same status is a no-op.",
    responses={**AUTH_RESPONSES, **NOT_FOUND_RESPONSE},
)
def set_attendance_endpoint(
    event_id: UUID,
    body: AttendanceStatusRequest,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return set_attendance(db, str(event_id), user_id, body.status)


@router.delete(
    "",
    response_model=MessageResponse,
    summary="Clear attendance status",
    responses={**AUTH_RESPONSES, **NOT_FOUND_RESPONSE},
)
def remove_attendance_endpoint(
    event_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    remove_attendance(db, str(event_id), user_id)
    return MessageResponse(message="Attendance removed successfully")
