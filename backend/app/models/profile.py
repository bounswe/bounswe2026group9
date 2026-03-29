"""Profile Pydantic schemas."""

from datetime import date

from pydantic import BaseModel, EmailStr

from app.models.event import EventListItemResponse


class ProfileUpdateRequest(BaseModel):
    date_of_birth: date | None = None
    phone_number: str | None = None
    email_visibility: str | None = None
    default_location_name: str | None = None
    default_location_lat: float | None = None
    default_location_lng: float | None = None


class HostProfileResponse(BaseModel):
    id: str
    username: str
    email: EmailStr | None = None
    phone_number: str | None = None
    average_rating: float | None = None
    hosted_events_count: int
    hosted_events: list[EventListItemResponse]
