"""Invite & access request service — business logic."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from supabase import Client

from app.config import settings
from app.models.invite import (
    AccessRequestDecision,
    AccessRequestListResponse,
    AccessRequestResponse,
    InviteCreateRequest,
    InviteListResponse,
    InviteResponse,
)
from app.repositories import event as event_repo
from app.repositories import invite as invite_repo


def _build_invite_url(event_id: str, token: str) -> str:
    return f"{settings.FRONTEND_URL}/event/{event_id}/invite/{token}"


def _invite_to_response(invite: dict) -> InviteResponse:
    return InviteResponse(
        id=invite["id"],
        event_id=invite["event_id"],
        token=invite["token"],
        invite_url=_build_invite_url(invite["event_id"], invite["token"]),
        expires_at=invite.get("expires_at"),
        max_uses=invite.get("max_uses"),
        use_count=invite["use_count"],
        created_at=invite["created_at"],
    )


# --- Invite Endpoints ---

def create_invite(
    db: Client, event_id: str, user_id: str, body: InviteCreateRequest
) -> InviteResponse:
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event["host_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can create invites")

    if event["visibility"] != "private":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invites are only for private events")

    if event["status"] not in ("published", "updated"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event must be published to create invites")

    token = secrets.token_urlsafe(32)
    expires_at = None
    if body.expires_in_hours:
        expires_at = (datetime.now(UTC) + timedelta(hours=body.expires_in_hours)).isoformat()

    invite = invite_repo.insert_invite(db, {
        "event_id": event_id,
        "created_by": user_id,
        "token": token,
        "expires_at": expires_at,
        "max_uses": body.max_uses,
    })

    return _invite_to_response(invite)


def list_invites(db: Client, event_id: str, user_id: str) -> InviteListResponse:
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event["host_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can view invites")

    invites = invite_repo.get_invites_by_event(db, event_id)
    return InviteListResponse(items=[_invite_to_response(i) for i in invites])


def accept_invite(db: Client, event_id: str, token: str, user_id: str) -> dict:
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event["status"] not in ("published", "updated"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event is not active")

    if event["host_id"] == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Host already has access")

    # Check if already granted
    existing_grant = invite_repo.get_access_grant(db, event_id, user_id)
    if existing_grant:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Access already granted")

    invite = invite_repo.get_invite_by_token(db, token)
    if not invite or invite["event_id"] != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite link")

    # Check expiry
    if invite.get("expires_at"):
        expires = datetime.fromisoformat(invite["expires_at"].replace("Z", "+00:00"))
        if datetime.now(UTC) > expires:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite link has expired")

    # Check max uses
    if invite.get("max_uses") and invite["use_count"] >= invite["max_uses"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite link has reached maximum uses")

    # Grant access
    invite_repo.insert_access_grant(db, {
        "event_id": event_id,
        "user_id": user_id,
        "granted_via": "invite",
    })
    invite_repo.increment_invite_use_count(db, invite["id"])

    return {"message": "Access granted successfully"}


# --- Access Request Endpoints ---

def create_access_request(db: Client, event_id: str, user_id: str) -> AccessRequestResponse:
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event["visibility"] != "private":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Access requests are only for private events")

    if event["status"] not in ("published", "updated"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Event is not active")

    if event["host_id"] == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Host already has access")

    # Check if already granted
    existing_grant = invite_repo.get_access_grant(db, event_id, user_id)
    if existing_grant:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Access already granted")

    # Check if already requested
    existing_request = invite_repo.get_access_request(db, event_id, user_id)
    if existing_request:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Access request already exists")

    request = invite_repo.insert_access_request(db, {
        "event_id": event_id,
        "user_id": user_id,
        "status": "pending",
    })

    # Get username for response
    from app.repositories import user as user_repo
    user = user_repo.get_user_by_id(db, user_id)

    from app.repositories import notification as notification_repo
    notification_repo.insert_notification(db, {
        "user_id": event["host_id"],
        "event_id": event_id,
        "type": "access_request",
        "message": (
            f"User '{user['username'] if user else 'unknown'}' requested access "
            f"to your event '{event['title']}'"
        ),
        "is_read": False,
    })

    return AccessRequestResponse(
        id=request["id"],
        event_id=request["event_id"],
        user_id=request["user_id"],
        username=user["username"] if user else "unknown",
        status=request["status"],
        created_at=request["created_at"],
        resolved_at=request.get("resolved_at"),
    )


def list_access_requests(db: Client, event_id: str, user_id: str) -> AccessRequestListResponse:
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event["host_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can view access requests")

    requests = invite_repo.get_pending_requests_by_event(db, event_id)

    user_ids = list({r["user_id"] for r in requests})
    users = {}
    if user_ids:
        result = db.table("users").select("id, username").in_("id", user_ids).execute()
        users = {row["id"]: row for row in (result.data or [])}

    items = [
        AccessRequestResponse(
            id=r["id"],
            event_id=r["event_id"],
            user_id=r["user_id"],
            username=users.get(r["user_id"], {}).get("username", "unknown"),
            status=r["status"],
            created_at=r["created_at"],
            resolved_at=r.get("resolved_at"),
        )
        for r in requests
    ]

    return AccessRequestListResponse(items=items)


def decide_access_request(
    db: Client, event_id: str, request_id: str, user_id: str, body: AccessRequestDecision
) -> AccessRequestResponse:
    event = event_repo.get_event_by_id(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event["host_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the host can manage access requests")

    request = invite_repo.get_access_request_by_id(db, request_id)
    if not request or request["event_id"] != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found")

    if request["status"] != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request already resolved")

    now = datetime.now(UTC).isoformat()
    updated = invite_repo.update_access_request(db, request_id, {
        "status": body.status,
        "resolved_at": now,
    })

    from app.repositories import notification as notification_repo
    from app.repositories import user as user_repo

    if body.status == "approved":
        invite_repo.insert_access_grant(db, {
            "event_id": event_id,
            "user_id": request["user_id"],
            "granted_via": "request",
        })
        notification_repo.insert_notification(db, {
            "user_id": request["user_id"],
            "event_id": event_id,
            "type": "access_approved",
            "message": f"Your access request for '{event['title']}' has been approved. You can now view and attend this event.",
            "is_read": False,
        })
    else:
        notification_repo.insert_notification(db, {
            "user_id": request["user_id"],
            "event_id": event_id,
            "type": "access_rejected",
            "message": f"Your access request for '{event['title']}' has been declined.",
            "is_read": False,
        })

    user = user_repo.get_user_by_id(db, request["user_id"])

    return AccessRequestResponse(
        id=updated["id"],
        event_id=updated["event_id"],
        user_id=updated["user_id"],
        username=user["username"] if user else "unknown",
        status=updated["status"],
        created_at=updated["created_at"],
        resolved_at=updated.get("resolved_at"),
    )
