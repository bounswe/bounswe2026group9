"""Unit tests for `services.event` validators + helpers (Phase 1 slice A).

Pure validators (validate_event_datetime, validate_segments) need no
mocks — they're datetime arithmetic. DI helpers (validate_categories_exist,
check_duplicate_event, check_rate_limit, auto_end_event_if_past) take
their repo collaborators through the new keyword-default seam.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.event import SegmentRequest
from app.services import event as event_service

HOST_ID = "00000000-0000-0000-0000-0000000000a0"
EVENT_ID = "00000000-0000-0000-0000-0000000000a1"
CAT_A = "00000000-0000-0000-0000-0000000000a2"
CAT_B = "00000000-0000-0000-0000-0000000000a3"


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


def _aware(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


# ── validate_event_datetime ─────────────────────────────────────────────────


class TestValidateEventDatetime:
    def test_passes_when_end_after_start_and_in_future(self):
        start = datetime.now(UTC) + timedelta(days=1)
        end = start + timedelta(hours=2)
        # No exception
        event_service.validate_event_datetime(start, end)

    def test_400_when_naive_datetime(self):
        naive = datetime(2026, 6, 1, 12)  # no tzinfo
        with pytest.raises(HTTPException) as exc:
            event_service.validate_event_datetime(naive, _aware(2026, 6, 1, 14))
        assert exc.value.status_code == 400

    def test_400_when_start_in_past_without_allow_past(self):
        past = datetime.now(UTC) - timedelta(days=1)
        future = past + timedelta(hours=2)
        with pytest.raises(HTTPException) as exc:
            event_service.validate_event_datetime(past, future)
        assert exc.value.status_code == 400

    def test_400_when_end_before_or_equal_start(self):
        start = datetime.now(UTC) + timedelta(days=1)
        with pytest.raises(HTTPException) as exc:
            event_service.validate_event_datetime(start, start)
        assert exc.value.status_code == 400

    def test_allow_past_skips_future_check(self):
        past = datetime.now(UTC) - timedelta(days=1)
        future = past + timedelta(hours=2)
        # Should not raise — explicit allow_past for edit-after-start workflow.
        event_service.validate_event_datetime(past, future, allow_past=True)


# ── validate_categories_exist ────────────────────────────────────────────────


class TestValidateCategoriesExist:
    def test_passes_when_all_present(self, db):
        events = MagicMock()
        events.get_valid_category_ids.return_value = {CAT_A, CAT_B}
        # No exception
        event_service.validate_categories_exist(db, [CAT_A, CAT_B], events=events)

    def test_400_when_any_missing(self, db):
        events = MagicMock()
        events.get_valid_category_ids.return_value = {CAT_A}  # B is missing
        with pytest.raises(HTTPException) as exc:
            event_service.validate_categories_exist(db, [CAT_A, CAT_B], events=events)
        assert exc.value.status_code == 400


# ── validate_segments ──────────────────────────────────────────────────────


def _seg(loc_idx: int, order_idx: int, start: datetime, end: datetime, desc: str | None = None) -> SegmentRequest:
    return SegmentRequest(
        location_index=loc_idx,
        order_index=order_idx,
        start_datetime=start,
        end_datetime=end,
        description=desc,
    )


class TestValidateSegments:
    def test_no_op_when_segments_empty(self):
        event_service.validate_segments(None, 1, _aware(2026, 6, 1, 10), _aware(2026, 6, 1, 14))
        event_service.validate_segments([], 1, _aware(2026, 6, 1, 10), _aware(2026, 6, 1, 14))

    def test_400_when_location_index_out_of_range(self):
        with pytest.raises(HTTPException) as exc:
            event_service.validate_segments(
                [_seg(5, 0, _aware(2026, 6, 1, 10), _aware(2026, 6, 1, 11))],
                location_count=2,
                event_start=_aware(2026, 6, 1, 10),
                event_end=_aware(2026, 6, 1, 14),
            )
        assert exc.value.status_code == 400

    def test_400_when_segment_outside_event_window(self):
        with pytest.raises(HTTPException) as exc:
            event_service.validate_segments(
                [_seg(0, 0, _aware(2026, 6, 1, 9), _aware(2026, 6, 1, 11))],
                location_count=1,
                event_start=_aware(2026, 6, 1, 10),
                event_end=_aware(2026, 6, 1, 14),
            )
        assert exc.value.status_code == 400

    def test_400_when_order_index_not_contiguous(self):
        # 0 then 2 → gap.
        with pytest.raises(HTTPException) as exc:
            event_service.validate_segments(
                [
                    _seg(0, 0, _aware(2026, 6, 1, 10), _aware(2026, 6, 1, 11)),
                    _seg(0, 2, _aware(2026, 6, 1, 12), _aware(2026, 6, 1, 13)),
                ],
                location_count=1,
                event_start=_aware(2026, 6, 1, 10),
                event_end=_aware(2026, 6, 1, 14),
            )
        assert exc.value.status_code == 400

    def test_400_when_segments_overlap_in_time(self):
        with pytest.raises(HTTPException) as exc:
            event_service.validate_segments(
                [
                    _seg(0, 0, _aware(2026, 6, 1, 10), _aware(2026, 6, 1, 12)),
                    _seg(0, 1, _aware(2026, 6, 1, 11, 30), _aware(2026, 6, 1, 13)),
                ],
                location_count=1,
                event_start=_aware(2026, 6, 1, 10),
                event_end=_aware(2026, 6, 1, 14),
            )
        assert exc.value.status_code == 400


# ── check_duplicate_event ────────────────────────────────────────────────────


class TestCheckDuplicateEvent:
    def test_passes_when_no_duplicates(self, db):
        events = MagicMock()
        events.find_duplicate_events.return_value = []
        event_service.check_duplicate_event(
            db, HOST_ID, "Festival", "2026-06-01T10:00:00+00:00", "Main Stage", events=events,
        )

    def test_409_only_when_primary_location_matches(self, db):
        events = MagicMock()
        events.find_duplicate_events.return_value = [{"id": EVENT_ID}]
        events.find_location_by_event_and_name.return_value = [{"id": "loc1"}]

        with pytest.raises(HTTPException) as exc:
            event_service.check_duplicate_event(
                db, HOST_ID, "Festival", "2026-06-01T10:00:00+00:00", "Main Stage",
                events=events,
            )
        assert exc.value.status_code == 409

    def test_passes_when_duplicate_has_different_primary_location(self, db):
        events = MagicMock()
        events.find_duplicate_events.return_value = [{"id": EVENT_ID}]
        # Same title + start_datetime, but the primary location lookup returns
        # nothing — issue #149 explicitly allows non-primary collisions.
        events.find_location_by_event_and_name.return_value = []

        event_service.check_duplicate_event(
            db, HOST_ID, "Festival", "2026-06-01T10:00:00+00:00", "Main Stage",
            events=events,
        )


# ── check_rate_limit ────────────────────────────────────────────────────────


class TestCheckRateLimit:
    def test_passes_for_exempt_email(self, db):
        events = MagicMock()
        users = MagicMock()
        users.get_user_email_by_id.return_value = "muhittin0koybasi@gmail.com"

        event_service.check_rate_limit(db, HOST_ID, events=events, users=users)

        # Exempt → don't even fetch the rate-limit config.
        events.get_rate_limit_config.assert_not_called()

    def test_passes_when_no_config_set(self, db):
        events = MagicMock()
        users = MagicMock()
        users.get_user_email_by_id.return_value = "alice@example.com"
        events.get_rate_limit_config.return_value = None

        event_service.check_rate_limit(db, HOST_ID, events=events, users=users)
        events.count_events_by_host_since.assert_not_called()

    def test_429_when_count_at_or_over_limit(self, db):
        events = MagicMock()
        users = MagicMock()
        users.get_user_email_by_id.return_value = "alice@example.com"
        events.get_rate_limit_config.return_value = {
            "max_events_per_user": 3, "time_window_hours": 24,
        }
        events.count_events_by_host_since.return_value = 3

        with pytest.raises(HTTPException) as exc:
            event_service.check_rate_limit(db, HOST_ID, events=events, users=users)
        assert exc.value.status_code == 429

    def test_passes_when_count_below_limit(self, db):
        events = MagicMock()
        users = MagicMock()
        users.get_user_email_by_id.return_value = "alice@example.com"
        events.get_rate_limit_config.return_value = {
            "max_events_per_user": 5, "time_window_hours": 24,
        }
        events.count_events_by_host_since.return_value = 2

        event_service.check_rate_limit(db, HOST_ID, events=events, users=users)


# ── auto_end_event_if_past ──────────────────────────────────────────────────


class TestAutoEndEventIfPast:
    def test_no_op_for_non_active_status(self, db):
        events = MagicMock()
        event = {"id": EVENT_ID, "status": "draft", "end_datetime": "2020-01-01T00:00:00+00:00"}

        result = event_service.auto_end_event_if_past(db, event, events=events)

        assert result["status"] == "draft"
        events.update_event_status.assert_not_called()

    def test_updates_to_ended_when_past_end_datetime(self, db):
        events = MagicMock()
        past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
        event = {"id": EVENT_ID, "status": "published", "end_datetime": past}

        result = event_service.auto_end_event_if_past(db, event, events=events)

        assert result["status"] == "ended"
        events.update_event_status.assert_called_once_with(db, EVENT_ID, "ended")

    def test_no_op_when_end_datetime_is_in_future(self, db):
        events = MagicMock()
        future = (datetime.now(UTC) + timedelta(days=7)).isoformat()
        event = {"id": EVENT_ID, "status": "published", "end_datetime": future}

        result = event_service.auto_end_event_if_past(db, event, events=events)

        assert result["status"] == "published"
        events.update_event_status.assert_not_called()
