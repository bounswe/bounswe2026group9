from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# --- Invite ---

class InviteCreateRequest(BaseModel):
    max_uses: int | None = Field(default=None, gt=0)
    expires_in_hours: int | None = Field(default=None, gt=0, le=720)  # max 30 days


class InviteResponse(BaseModel):
    id: UUID
    event_id: UUID
    token: str
    invite_url: str
    expires_at: datetime | None
    max_uses: int | None
    use_count: int
    created_at: datetime


class InviteListResponse(BaseModel):
    items: list[InviteResponse]


# --- Access Request ---

class AccessRequestResponse(BaseModel):
    id: UUID
    event_id: UUID
    user_id: UUID
    username: str
    status: str
    created_at: datetime
    resolved_at: datetime | None


class AccessRequestListResponse(BaseModel):
    items: list[AccessRequestResponse]


class AccessRequestDecision(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")


# --- Access Grant ---

class AccessGrantResponse(BaseModel):
    id: UUID
    event_id: UUID
    user_id: UUID
    granted_via: str
    created_at: datetime
