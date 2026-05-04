from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.models.base import AppBaseModel

# --- Invite ---

class InviteCreateRequest(AppBaseModel):
    max_uses: int | None = Field(default=None, gt=0)
    expires_in_hours: int | None = Field(default=None, gt=0, le=720)  # max 30 days


class InviteResponse(AppBaseModel):
    id: UUID
    event_id: UUID
    token: str
    invite_url: str
    expires_at: datetime | None
    max_uses: int | None
    use_count: int
    created_at: datetime


class InviteListResponse(AppBaseModel):
    items: list[InviteResponse]


# --- Access Request ---

class AccessRequestResponse(AppBaseModel):
    id: UUID
    event_id: UUID
    user_id: UUID
    username: str
    status: str
    created_at: datetime
    resolved_at: datetime | None


class AccessRequestListResponse(AppBaseModel):
    items: list[AccessRequestResponse]


class AccessRequestDecision(AppBaseModel):
    status: str = Field(pattern="^(approved|rejected)$")


# --- Access Grant ---

class AccessGrantResponse(AppBaseModel):
    id: UUID
    event_id: UUID
    user_id: UUID
    granted_via: str
    created_at: datetime
