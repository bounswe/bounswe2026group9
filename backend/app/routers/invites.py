"""Invite & access request endpoints — HTTP layer only."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.database import get_supabase
from app.middleware.auth import get_current_user_id
from app.models.errors import (
    AUTH_RESPONSES,
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
)
from app.models.invite import (
    AccessRequestDecision,
    AccessRequestListResponse,
    AccessRequestResponse,
    InviteCreateRequest,
    InviteListResponse,
    InviteResponse,
)
from app.models.user import MessageResponse
from app.services.invite import (
    accept_invite,
    create_access_request,
    create_invite,
    decide_access_request,
    list_access_requests,
    list_invites,
)

router = APIRouter(prefix="/events/{event_id}", tags=["invites"])


# --- Invites ---

@router.post(
    "/invites",
    status_code=status.HTTP_201_CREATED,
    response_model=InviteResponse,
    summary="Issue an invite for a private event",
    description="Host-only.",
    responses={**AUTH_RESPONSES, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE, **CONFLICT_RESPONSE},
)
def create_invite_endpoint(
    event_id: UUID,
    body: InviteCreateRequest,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return create_invite(db, str(event_id), user_id, body)


@router.get(
    "/invites",
    response_model=InviteListResponse,
    summary="List invites for an event",
    description="Host-only.",
    responses={**AUTH_RESPONSES, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
def list_invites_endpoint(
    event_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return list_invites(db, str(event_id), user_id)


@router.post(
    "/invites/{token}/accept",
    response_model=MessageResponse,
    summary="Accept an invite via token",
    responses={**AUTH_RESPONSES, **NOT_FOUND_RESPONSE, **CONFLICT_RESPONSE},
)
def accept_invite_endpoint(
    event_id: UUID,
    token: str,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return accept_invite(db, str(event_id), token, user_id)


# --- Access Requests ---

@router.post(
    "/access-requests",
    status_code=status.HTTP_201_CREATED,
    response_model=AccessRequestResponse,
    summary="Request access to a private event",
    responses={**AUTH_RESPONSES, **NOT_FOUND_RESPONSE, **CONFLICT_RESPONSE},
)
def create_access_request_endpoint(
    event_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return create_access_request(db, str(event_id), user_id)


@router.get(
    "/access-requests",
    response_model=AccessRequestListResponse,
    summary="List access requests for an event",
    description="Host-only.",
    responses={**AUTH_RESPONSES, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
def list_access_requests_endpoint(
    event_id: UUID,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return list_access_requests(db, str(event_id), user_id)


@router.patch(
    "/access-requests/{request_id}",
    response_model=AccessRequestResponse,
    summary="Approve or deny an access request",
    description="Host-only.",
    responses={**AUTH_RESPONSES, **FORBIDDEN_RESPONSE, **NOT_FOUND_RESPONSE},
)
def decide_access_request_endpoint(
    event_id: UUID,
    request_id: UUID,
    body: AccessRequestDecision,
    user_id: str = Depends(get_current_user_id),
):
    db = get_supabase()
    return decide_access_request(db, str(event_id), str(request_id), user_id, body)
