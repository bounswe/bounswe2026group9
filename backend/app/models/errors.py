"""Standard error response schemas used across the OpenAPI spec.

FastAPI raises ``HTTPException`` with a ``detail`` payload for all error
cases. Documenting that shape here gives every client a single, predictable
error contract instead of an opaque ``string``.
"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Uniform error envelope returned for non-2xx responses."""

    detail: str = Field(
        description="Human-readable explanation of the error.",
        examples=["Invalid email or password"],
    )


class ValidationErrorItem(BaseModel):
    loc: list[str | int] = Field(
        description="Path to the offending field, e.g. ['body', 'email'].",
        examples=[["body", "email"]],
    )
    msg: str = Field(
        description="Validation message.",
        examples=["value is not a valid email address"],
    )
    type: str = Field(
        description="Pydantic error type.",
        examples=["value_error.email"],
    )


class ValidationErrorResponse(BaseModel):
    """Pydantic validation failure (HTTP 422)."""

    detail: list[ValidationErrorItem]


# Reusable response dictionaries for ``responses=`` on endpoints.
# Compose with ``{**AUTH_RESPONSES, ...}``  per-endpoint.
COMMON_RESPONSES: dict[int, dict[str, Any]] = {
    422: {"model": ValidationErrorResponse, "description": "Request validation failed."},
}

AUTH_RESPONSES: dict[int, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing, invalid, or expired access token."},
}

FORBIDDEN_RESPONSE: dict[int, dict[str, Any]] = {
    403: {"model": ErrorResponse, "description": "Authenticated but not allowed to perform this action."},
}

NOT_FOUND_RESPONSE: dict[int, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Resource not found."},
}

CONFLICT_RESPONSE: dict[int, dict[str, Any]] = {
    409: {"model": ErrorResponse, "description": "Conflict with current resource state (e.g. duplicate)."},
}

RATE_LIMIT_RESPONSE = {
    429: {"model": ErrorResponse, "description": "Rate limit exceeded — retry later."},
}
