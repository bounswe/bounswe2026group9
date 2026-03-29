"""Rating Pydantic schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RatingRequest(BaseModel):
    score: Decimal = Field(ge=1.00, le=5.00, max_digits=3, decimal_places=2)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"score": 4.5}
        }
    )


class RatingResponse(BaseModel):
    id: UUID
    rater_id: UUID
    host_id: UUID
    score: Decimal
    created_at: datetime
