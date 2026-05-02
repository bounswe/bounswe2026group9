from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class GeoJSONPoint(BaseModel):
    """GeoJSON Point Geometry (RFC 7946 section 3.1.2)"""
    type: Literal["Point"] = "Point"
    # coordinates MUST be [longitude, latitude]
    coordinates: list[float] = Field(min_length=2, max_length=2)


class EventGeoJSONProperties(BaseModel):
    """Properties for an Event Feature."""
    id: UUID
    host_id: UUID
    title: str
    start_datetime: str  # Kept as str to match exactly the serialized format, though AppBaseModel handles datetime natively.
    status: str
    visibility: str
    primary_category: str | None = None
    attendee_count: int = 0
    attendee_limit: int | None = None
    is_bookmarked: bool | None = None
    attendance_status: str | None = None
    going_count: int = 0
    bookmark_count: int = 0
    primary_image_url: str | None = None


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature Object (RFC 7946 section 3.2)"""
    type: Literal["Feature"] = "Feature"
    geometry: GeoJSONPoint
    properties: EventGeoJSONProperties


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection Object (RFC 7946 section 3.3)"""
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[GeoJSONFeature]
