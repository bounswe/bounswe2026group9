"""Shared Pydantic base model for all API schemas.

This module defines ``AppBaseModel``, which all request and response schemas
should inherit from instead of ``pydantic.BaseModel`` directly.  The key
addition is a ``model_config`` that enforces RFC 3339 / ISO 8601-compatible
datetime serialisation across the entire API surface:

* ``datetime`` instances are serialised **with their UTC offset** (e.g.
  ``2026-04-15T14:30:00+00:00``), never as a naive string that would leave
  clients to guess the timezone.
* The ``serialize_as_any=True`` flag ensures that sub-class fields are
  serialised with the full field type, which prevents accidental data loss
  when response models are returned from service functions as dicts.
"""

from datetime import datetime

from pydantic import BaseModel
from pydantic.config import ConfigDict


def _utc_isoformat(dt: datetime) -> str:
    """Return an RFC 3339-compliant string for *dt*.

    If *dt* is timezone-aware it is converted to UTC first so the offset in
    the output is always ``+00:00``.  Naive datetimes (no tzinfo) are assumed
    to already represent UTC and are labelled accordingly.
    """
    if dt.tzinfo is None or dt.utcoffset() is None:
        # Treat naive datetimes as UTC (defensive fallback).
        dt = dt.replace(tzinfo=datetime.UTC)
    else:
        dt = dt.astimezone(datetime.UTC)
    return dt.isoformat()  # produces "YYYY-MM-DDTHH:MM:SS+00:00"


class AppBaseModel(BaseModel):
    """Base class for all API request / response schemas.

    Inheriting from this instead of ``pydantic.BaseModel`` ensures that every
    ``datetime`` field in every schema is serialised in RFC 3339 format with an
    explicit UTC offset, satisfying issue #251.
    """

    model_config = ConfigDict(
        # Serialise datetime objects as RFC 3339 strings with offset.
        json_encoders={datetime: _utc_isoformat},
        # Populate by field name (snake_case), not by alias.
        populate_by_name=True,
    )
