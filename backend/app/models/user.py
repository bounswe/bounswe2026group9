from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# --- Request Schemas ---

class UserRegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(min_length=8)
    date_of_birth: date


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str | None = None


# --- Response Schemas ---

class UserResponse(BaseModel):
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


class AuthResponse(BaseModel):
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    email_sent: bool = True  # False when SMTP is not configured


class MessageResponse(BaseModel):
    message: str
