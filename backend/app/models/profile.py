"""Profile Pydantic schemas."""

from datetime import date

from pydantic import EmailStr

from app.models.base import AppBaseModel
from app.models.event import EventListItemResponse


class ProfileUpdateRequest(AppBaseModel):
    date_of_birth: date | None = None
    phone_number: str | None = None
    email_visibility: str | None = None
    phone_visibility: str | None = None
    default_location_name: str | None = None
    default_location_lat: float | None = None
    default_location_lng: float | None = None


class HostProfileResponse(AppBaseModel):
    id: str
    username: str
    email: EmailStr | None = None
    phone_number: str | None = None
    average_rating: float | None = None
    hosted_events_count: int
    hosted_events: list[EventListItemResponse]
    can_rate: bool = False
