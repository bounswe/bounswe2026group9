"""Attendance endpoints — HTTP layer only."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.database import get_supabase
from app.middleware.auth import get_current_user_id
from app.models.attendance import AttendanceResponse, AttendanceStatusRequest, QrTokenResponse
from app.models.errors import AUTH_RESPONSES, NOT_FOUND_RESPONSE
from app.models.user import MessageResponse
from app.services.attendance import get_my_qr, remove_attendance, set_attendance

router = APIRouter(prefix="/events/{event_id}/attendance", tags=["attendances"])

_qr_router = APIRouter(prefix="/attendances", tags=["attendances"])


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


@_qr_router.get(
    "/me/{event_id}/qr",
    response_model=QrTokenResponse,
    summary="Get my check-in QR token",
    description=(
        "Returns the signed QR payload for the authenticated Going user. "
        "Render the `token` field as a QR code. "
        "Returns 404 if the caller is not Going for this event."
    ),
    responses={**AUTH_RESPONSES, **NOT_FOUND_RESPONSE},
)
def get_my_qr_endpoint(
    event_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return get_my_qr(db, str(event_id), user_id)
