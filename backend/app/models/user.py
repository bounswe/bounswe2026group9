from datetime import date, datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.models.base import AppBaseModel

# --- Request Schemas ---

class UserRegisterRequest(AppBaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(min_length=8)
    date_of_birth: date


class UserLoginRequest(AppBaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(AppBaseModel):
    refresh_token: str | None = None


# --- Response Schemas ---

class UserResponse(AppBaseModel):
    id: UUID
    username: str
    email: str
    phone_number: str | None = None
    date_of_birth: date | None = None
    email_visibility: bool = False
    phone_visibility: bool = False
    role: str
    auth_provider: str
    email_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AuthResponse(AppBaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    email_sent: bool = True  # False when SMTP is not configured


class MessageResponse(AppBaseModel):
    message: str
