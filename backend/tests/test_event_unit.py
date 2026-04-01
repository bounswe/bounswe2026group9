"""Fast unit tests for event service business rules."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.services.event import auto_end_event_if_past, validate_event_datetime


class TestValidateEventDatetime:
    def test_rejects_past_start_by_default(self):
        start = datetime.now(UTC) - timedelta(hours=1)
        end = datetime.now(UTC) + timedelta(hours=1)

        with pytest.raises(HTTPException) as exc_info:
            validate_event_datetime(start, end)

        assert exc_info.value.status_code == 400
        assert "future" in exc_info.value.detail

    def test_rejects_end_before_start(self):
        start = datetime.now(UTC) + timedelta(hours=2)
        end = datetime.now(UTC) + timedelta(hours=1)

        with pytest.raises(HTTPException) as exc_info:
            validate_event_datetime(start, end)

        assert exc_info.value.status_code == 400
        assert "after start_datetime" in exc_info.value.detail

    def test_allows_past_start_when_explicitly_enabled(self):
        start = datetime.now(UTC) - timedelta(hours=2)
        end = datetime.now(UTC) - timedelta(hours=1)

        validate_event_datetime(start, end, allow_past=True)


class TestAutoEndEventIfPast:
    @patch("app.services.event.event_repo.update_event_status")
    def test_marks_published_past_event_as_ended(self, mock_update_event_status):
        db = object()
        event = {
            "id": "event-1",
            "status": "published",
            "end_datetime": (datetime.now(UTC) - timedelta(minutes=30)).isoformat(),
        }

        updated_event = auto_end_event_if_past(db=db, event=event)

        assert updated_event["status"] == "ended"
        mock_update_event_status.assert_called_once_with(db, "event-1", "ended")

    @patch("app.services.event.event_repo.update_event_status")
    def test_leaves_future_event_unchanged(self, mock_update_event_status):
        db = object()
        event = {
            "id": "event-1",
            "status": "published",
            "end_datetime": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        }

        updated_event = auto_end_event_if_past(db=db, event=event)

        assert updated_event["status"] == "published"
        mock_update_event_status.assert_not_called()
