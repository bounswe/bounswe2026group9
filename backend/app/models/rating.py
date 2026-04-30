"""Rating Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RatingRequest(BaseModel):
    score: Decimal = Field(ge=1.00, le=5.00, max_digits=3, decimal_places=2)
    review_text: str | None = Field(default=None, max_length=1000)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "score": 4.5,
                "review_text": "Walk was excellent — leader was clear and friendly.",
            }
        }
    )


class RatingResponse(BaseModel):
    id: UUID
    rater_id: UUID
    host_id: UUID
    score: Decimal
    review_text: str | None = None
    created_at: datetime


class ReviewListItemResponse(BaseModel):
    """Single review row for the host's reviews-list endpoint.

    `review_text` is None for star-only ratings; the frontend renders a
    "No written review" placeholder for those rows. `rater_username` lets
    the UI show the rater's name without a separate user lookup.
    """
    id: UUID
    rater_id: UUID
    rater_username: str
    score: Decimal
    review_text: str | None = None
    created_at: datetime


class ReviewListResponse(BaseModel):
    """Paginated reviews-by-host result, ordered newest-first."""
    items: list[ReviewListItemResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
