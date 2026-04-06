from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# --- Nested Schemas ---

class LocationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    is_primary: bool = True
    order_index: int = 0


class LocationResponse(BaseModel):
    id: UUID
    name: str
    latitude: float
    longitude: float
    is_primary: bool
    order_index: int


class VenueMetadataRequest(BaseModel):
    price: str | None = None
    language: str | None = None
    health_requirements: str | None = None
    wheelchair_access: bool = False
    accessible_restroom: bool = False
    elevator_available: bool = False
    seating_available: bool = False
    captions_support: bool = False
    quiet_friendly: bool = False


class VenueMetadataResponse(BaseModel):
    id: UUID
    price: str | None = None
    language: str | None = None
    health_requirements: str | None = None
    wheelchair_access: bool
    accessible_restroom: bool
    elevator_available: bool
    seating_available: bool
    captions_support: bool
    quiet_friendly: bool


class EquipmentRequest(BaseModel):
    item_name: str = Field(min_length=1, max_length=200)
    is_required: bool = True


class EquipmentResponse(BaseModel):
    id: UUID
    item_name: str
    is_required: bool


class CategoryResponse(BaseModel):
    id: UUID
    name: str
    is_predefined: bool
    is_approved: bool


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class EventImageResponse(BaseModel):
    id: UUID
    image_url: str
    upload_date: datetime


class AttendeeSummaryResponse(BaseModel):
    id: UUID
    username: str


# --- Event Request Schemas ---

class EventCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    start_datetime: datetime
    end_datetime: datetime
    visibility: str = Field(default="public", pattern="^(public|private)$")
    is_age_restricted: bool = False
    attendee_limit: int | None = Field(default=None, gt=0)
    status: str = Field(default="draft", pattern="^(draft|published)$")
    category_ids: list[UUID] = Field(min_length=1)
    locations: list[LocationRequest] = Field(min_length=1)
    venue_metadata: VenueMetadataRequest | None = None
    equipment_requirements: list[EquipmentRequest] | None = None


class EventUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    visibility: str | None = Field(default=None, pattern="^(public|private)$")
    is_age_restricted: bool | None = None
    attendee_limit: int | None = Field(default=None, gt=0)
    clear_attendee_limit: bool = False  # Set to true to remove the limit (unlimited)
    category_ids: list[UUID] | None = Field(default=None, min_length=1)
    locations: list[LocationRequest] | None = Field(default=None, min_length=1)
    venue_metadata: VenueMetadataRequest | None = None
    equipment_requirements: list[EquipmentRequest] | None = None


# --- Event Response Schemas ---

class EventDetailResponse(BaseModel):
    id: UUID
    host_id: UUID
    title: str
    description: str
    start_datetime: datetime
    end_datetime: datetime
    visibility: str
    is_age_restricted: bool
    attendee_limit: int | None
    attendee_count: int
    status: str
    created_at: datetime
    updated_at: datetime
    is_bookmarked: bool | None = None
    attendance_status: str | None = None
    going_count: int = 0
    bookmark_count: int = 0
    is_full: bool | None = None
    access_request_status: str | None = None
    locations: list[LocationResponse] = []
    categories: list[CategoryResponse] = []
    images: list[EventImageResponse] = []
    venue_metadata: VenueMetadataResponse | None = None
    equipment_requirements: list[EquipmentResponse] = []
    attendees: list[AttendeeSummaryResponse] = []


class StatusChangeRequest(BaseModel):
    status: str = Field(pattern="^(published|cancelled|ended)$")


class EventLimitedResponse(BaseModel):
    """Limited preview for guests and unauthorized private event viewers."""
    id: UUID
    title: str
    start_datetime: datetime
    end_datetime: datetime
    visibility: str
    is_age_restricted: bool
    status: str
    is_bookmarked: bool | None = None
    access_request_status: str | None = None
    categories: list[CategoryResponse] = []


class EventListItemResponse(BaseModel):
    """Single event card for discovery listing.

    description is None for:
    - private events (always limited in list)
    - guest users viewing public events
    primary_location is None for private events.
    """
    id: UUID
    host_id: UUID
    title: str
    description: str | None = None
    start_datetime: datetime
    end_datetime: datetime
    visibility: str
    is_age_restricted: bool
    attendee_limit: int | None
    attendee_count: int
    status: str
    is_bookmarked: bool | None = None
    attendance_status: str | None = None
    access_request_status: str | None = None
    has_access: bool | None = None
    going_count: int = 0
    bookmark_count: int = 0
    is_full: bool | None = None
    categories: list[CategoryResponse] = []
    primary_location: LocationResponse | None = None
    primary_image_url: str | None = None


class EventListResponse(BaseModel):
    """Paginated event discovery result."""
    items: list[EventListItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
