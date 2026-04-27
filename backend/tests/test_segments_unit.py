"""Phase 1 unit tests for itinerary segments — schema validation only.

These tests cover the Pydantic models added in app/models/event.py and the
repository wrapper signatures that pass `p_segments` to the atomic RPCs.
They run as part of the `unit-fast` CI shard (`tests/test_*_unit.py`) and
do not touch the database.

Service-level validators (overlap / window / order) and end-to-end create/
update flows are covered by later phases.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.event import (
    EventCreateRequest,
    EventDetailResponse,
    EventUpdateRequest,
    LocationRequest,
    SegmentRequest,
    SegmentResponse,
)
from app.repositories import event as event_repo
from app.services.event import _build_segment_rows, validate_segments

# --- SegmentRequest schema ---------------------------------------------------

class TestSegmentRequestSchema:
    def _payload(self, **overrides):
        base = {
            "location_index": 0,
            "order_index": 0,
            "start_datetime": datetime.now(UTC) + timedelta(hours=1),
            "end_datetime": datetime.now(UTC) + timedelta(hours=2),
            "description": "Opening session",
        }
        base.update(overrides)
        return base

    def test_minimal_payload_parses(self):
        seg = SegmentRequest(**self._payload(description=None))
        assert seg.location_index == 0
        assert seg.order_index == 0
        assert seg.description is None

    def test_negative_location_index_rejected(self):
        with pytest.raises(ValidationError):
            SegmentRequest(**self._payload(location_index=-1))

    def test_negative_order_index_rejected(self):
        with pytest.raises(ValidationError):
            SegmentRequest(**self._payload(order_index=-1))

    def test_description_length_capped(self):
        with pytest.raises(ValidationError):
            SegmentRequest(**self._payload(description="x" * 1001))

    def test_description_at_limit_accepted(self):
        seg = SegmentRequest(**self._payload(description="x" * 1000))
        assert len(seg.description) == 1000

    def test_missing_required_fields_rejected(self):
        with pytest.raises(ValidationError):
            SegmentRequest(location_index=0, order_index=0)


# --- SegmentResponse schema --------------------------------------------------

class TestSegmentResponseSchema:
    def test_response_round_trips_uuids(self):
        sid = uuid4()
        lid = uuid4()
        now = datetime.now(UTC)
        resp = SegmentResponse(
            id=sid,
            location_id=lid,
            order_index=2,
            start_datetime=now,
            end_datetime=now + timedelta(hours=1),
            description=None,
        )
        assert resp.id == sid
        assert resp.location_id == lid
        assert resp.order_index == 2

    def test_description_optional(self):
        resp = SegmentResponse(
            id=uuid4(),
            location_id=uuid4(),
            order_index=0,
            start_datetime=datetime.now(UTC),
            end_datetime=datetime.now(UTC) + timedelta(hours=1),
        )
        assert resp.description is None


# --- EventCreate / EventUpdate accept segments -------------------------------

def _location() -> LocationRequest:
    return LocationRequest(
        name="Main hall", latitude=41.0, longitude=29.0, is_primary=True, order_index=0,
    )


def _segment(**overrides) -> SegmentRequest:
    base = {
        "location_index": 0,
        "order_index": 0,
        "start_datetime": datetime.now(UTC) + timedelta(hours=1),
        "end_datetime": datetime.now(UTC) + timedelta(hours=2),
        "description": "Welcome",
    }
    base.update(overrides)
    return SegmentRequest(**base)


class TestEventCreateAcceptsSegments:
    def _payload(self, segments):
        return EventCreateRequest(
            title="Itinerary event",
            description="Multi-stop event",
            start_datetime=datetime.now(UTC) + timedelta(hours=1),
            end_datetime=datetime.now(UTC) + timedelta(hours=4),
            visibility="public",
            is_age_restricted=False,
            attendee_limit=None,
            status="draft",
            category_ids=[uuid4()],
            locations=[_location()],
            segments=segments,
        )

    def test_segments_default_to_none(self):
        body = EventCreateRequest(
            title="No segments",
            description="ok",
            start_datetime=datetime.now(UTC) + timedelta(hours=1),
            end_datetime=datetime.now(UTC) + timedelta(hours=2),
            category_ids=[uuid4()],
            locations=[_location()],
        )
        assert body.segments is None

    def test_empty_segments_list_accepted(self):
        body = self._payload(segments=[])
        assert body.segments == []

    def test_segments_attached(self):
        body = self._payload(segments=[_segment()])
        assert len(body.segments) == 1
        assert body.segments[0].location_index == 0


class TestEventUpdateAcceptsSegments:
    def test_segments_default_to_none(self):
        body = EventUpdateRequest()
        assert body.segments is None

    def test_segments_attached(self):
        body = EventUpdateRequest(segments=[_segment(), _segment(order_index=1, start_datetime=datetime.now(UTC) + timedelta(hours=2, minutes=1), end_datetime=datetime.now(UTC) + timedelta(hours=3))])
        assert len(body.segments) == 2


# --- EventDetailResponse exposes segments ------------------------------------

class TestEventDetailResponseSegments:
    def test_segments_default_empty(self):
        now = datetime.now(UTC)
        detail = EventDetailResponse(
            id=uuid4(),
            host_id=uuid4(),
            title="t",
            description="d",
            start_datetime=now,
            end_datetime=now + timedelta(hours=1),
            visibility="public",
            is_age_restricted=False,
            attendee_limit=None,
            attendee_count=0,
            status="draft",
            created_at=now,
            updated_at=now,
        )
        assert detail.segments == []


# --- Repository RPC wrappers pass `p_segments` -------------------------------

class TestRepoCreateEventAtomicPassesSegments:
    def _exec_db(self):
        db = MagicMock()
        db.rpc.return_value.execute.return_value.data = {"id": str(uuid4())}
        return db

    def test_segments_param_forwarded(self):
        db = self._exec_db()
        seg_rows = [{
            "location_index": 0,
            "order_index": 0,
            "start_datetime": "2030-01-01T10:00:00+00:00",
            "end_datetime": "2030-01-01T11:00:00+00:00",
            "description": None,
        }]
        event_repo.create_event_atomic(
            db,
            event_data={"title": "x"},
            locations=[{"name": "L1"}],
            category_ids=["cat-id"],
            segments=seg_rows,
        )
        args, _ = db.rpc.call_args
        assert args[0] == "create_event_atomic"
        params = args[1]
        assert params["p_segments"] == seg_rows

    def test_segments_default_none(self):
        db = self._exec_db()
        event_repo.create_event_atomic(
            db,
            event_data={"title": "x"},
            locations=[{"name": "L1"}],
            category_ids=["cat-id"],
        )
        params = db.rpc.call_args[0][1]
        assert params["p_segments"] is None


class TestRepoUpdateEventAtomicPassesSegments:
    def _exec_db(self):
        db = MagicMock()
        db.rpc.return_value.execute.return_value.data = {"id": str(uuid4())}
        return db

    def test_segments_param_forwarded(self):
        db = self._exec_db()
        seg_rows = [{"location_index": 1, "order_index": 0}]
        event_repo.update_event_atomic(
            db,
            event_id=str(uuid4()),
            segments=seg_rows,
        )
        args, _ = db.rpc.call_args
        assert args[0] == "update_event_atomic"
        params = args[1]
        assert params["p_segments"] == seg_rows

    def test_segments_default_none_means_untouched(self):
        db = self._exec_db()
        event_repo.update_event_atomic(db, event_id=str(uuid4()))
        params = db.rpc.call_args[0][1]
        # NULL → leave existing segments alone (matches RPC contract).
        assert params["p_segments"] is None

    def test_segments_empty_array_means_clear_all(self):
        db = self._exec_db()
        event_repo.update_event_atomic(db, event_id=str(uuid4()), segments=[])
        params = db.rpc.call_args[0][1]
        # [] is distinct from None — RPC reads it as "delete every segment".
        assert params["p_segments"] == []


# --- Repository read helper --------------------------------------------------

class TestGetEventSegments:
    def test_orders_by_order_index_and_returns_rows(self):
        db = MagicMock()
        rows = [
            {"id": str(uuid4()), "order_index": 0},
            {"id": str(uuid4()), "order_index": 1},
        ]
        chain = db.table.return_value.select.return_value.eq.return_value.order.return_value.execute
        chain.return_value.data = rows

        result = event_repo.get_event_segments(db, "event-id")

        db.table.assert_called_with("event_segments")
        assert result == rows

    def test_returns_empty_list_when_none(self):
        db = MagicMock()
        chain = db.table.return_value.select.return_value.eq.return_value.order.return_value.execute
        chain.return_value.data = None

        assert event_repo.get_event_segments(db, "event-id") == []


# --- validate_segments (service-layer) --------------------------------------

def _seg(
    *,
    location_index: int = 0,
    order_index: int = 0,
    start_offset_min: int = 60,
    duration_min: int = 30,
    description: str | None = None,
) -> SegmentRequest:
    base = datetime(2030, 1, 1, 10, 0, 0, tzinfo=UTC)
    start = base + timedelta(minutes=start_offset_min)
    end = start + timedelta(minutes=duration_min)
    return SegmentRequest(
        location_index=location_index,
        order_index=order_index,
        start_datetime=start,
        end_datetime=end,
        description=description,
    )


_EVENT_START = datetime(2030, 1, 1, 10, 0, 0, tzinfo=UTC)
_EVENT_END = datetime(2030, 1, 1, 14, 0, 0, tzinfo=UTC)


class TestValidateSegments:
    def test_none_is_noop(self):
        validate_segments(None, location_count=1, event_start=_EVENT_START, event_end=_EVENT_END)

    def test_empty_list_is_noop(self):
        validate_segments([], location_count=1, event_start=_EVENT_START, event_end=_EVENT_END)

    def test_single_valid_segment_passes(self):
        validate_segments(
            [_seg()], location_count=1, event_start=_EVENT_START, event_end=_EVENT_END,
        )

    def test_two_back_to_back_segments_pass(self):
        # 10:30–11:00 then 11:00–11:30 — non-overlapping, contiguous order
        segments = [
            _seg(order_index=0, start_offset_min=30, duration_min=30),
            _seg(order_index=1, start_offset_min=60, duration_min=30),
        ]
        validate_segments(
            segments, location_count=1, event_start=_EVENT_START, event_end=_EVENT_END,
        )

    def test_location_index_out_of_range(self):
        with pytest.raises(HTTPException) as exc:
            validate_segments(
                [_seg(location_index=2)],
                location_count=1,
                event_start=_EVENT_START,
                event_end=_EVENT_END,
            )
        assert exc.value.status_code == 400
        assert "out of range" in exc.value.detail

    def test_location_index_at_count_rejected(self):
        # 0 < count == 1 means valid index is only 0
        with pytest.raises(HTTPException):
            validate_segments(
                [_seg(location_index=1)],
                location_count=1,
                event_start=_EVENT_START,
                event_end=_EVENT_END,
            )

    def test_inverted_time_rejected(self):
        bad = SegmentRequest(
            location_index=0,
            order_index=0,
            start_datetime=_EVENT_START + timedelta(hours=2),
            end_datetime=_EVENT_START + timedelta(hours=1),
        )
        with pytest.raises(HTTPException) as exc:
            validate_segments([bad], location_count=1, event_start=_EVENT_START, event_end=_EVENT_END)
        assert "after start_datetime" in exc.value.detail

    def test_zero_duration_rejected(self):
        same = _EVENT_START + timedelta(hours=1)
        bad = SegmentRequest(
            location_index=0,
            order_index=0,
            start_datetime=same,
            end_datetime=same,
        )
        with pytest.raises(HTTPException):
            validate_segments([bad], location_count=1, event_start=_EVENT_START, event_end=_EVENT_END)

    def test_naive_datetime_rejected(self):
        naive_start = datetime(2030, 1, 1, 11, 0, 0)
        bad = SegmentRequest(
            location_index=0,
            order_index=0,
            start_datetime=naive_start,
            end_datetime=naive_start + timedelta(hours=1),
        )
        with pytest.raises(HTTPException) as exc:
            validate_segments([bad], location_count=1, event_start=_EVENT_START, event_end=_EVENT_END)
        assert "timezone" in exc.value.detail

    def test_segment_starts_before_event(self):
        before = SegmentRequest(
            location_index=0,
            order_index=0,
            start_datetime=_EVENT_START - timedelta(minutes=30),
            end_datetime=_EVENT_START + timedelta(minutes=30),
        )
        with pytest.raises(HTTPException) as exc:
            validate_segments([before], location_count=1, event_start=_EVENT_START, event_end=_EVENT_END)
        assert "within event" in exc.value.detail

    def test_segment_ends_after_event(self):
        after = SegmentRequest(
            location_index=0,
            order_index=0,
            start_datetime=_EVENT_END - timedelta(minutes=30),
            end_datetime=_EVENT_END + timedelta(minutes=30),
        )
        with pytest.raises(HTTPException):
            validate_segments([after], location_count=1, event_start=_EVENT_START, event_end=_EVENT_END)

    def test_overlapping_segments_rejected(self):
        # 10:00–11:00 then 10:30–11:30 — overlap
        a = _seg(order_index=0, start_offset_min=0, duration_min=60)
        b = _seg(order_index=1, start_offset_min=30, duration_min=60)
        with pytest.raises(HTTPException) as exc:
            validate_segments([a, b], location_count=1, event_start=_EVENT_START, event_end=_EVENT_END)
        assert "overlap" in exc.value.detail

    def test_overlap_caught_when_segments_passed_unsorted(self):
        # Same as above but reverse order in the input list — validator must
        # sort by order_index before checking overlaps.
        a = _seg(order_index=0, start_offset_min=0, duration_min=60)
        b = _seg(order_index=1, start_offset_min=30, duration_min=60)
        with pytest.raises(HTTPException):
            validate_segments([b, a], location_count=1, event_start=_EVENT_START, event_end=_EVENT_END)

    def test_non_contiguous_order_index_rejected(self):
        # 0, 2 — skipping 1
        a = _seg(order_index=0, start_offset_min=0, duration_min=30)
        b = _seg(order_index=2, start_offset_min=60, duration_min=30)
        with pytest.raises(HTTPException) as exc:
            validate_segments([a, b], location_count=1, event_start=_EVENT_START, event_end=_EVENT_END)
        assert "contiguous order_index" in exc.value.detail

    def test_duplicate_order_index_rejected(self):
        a = _seg(order_index=0, start_offset_min=0, duration_min=30)
        b = _seg(order_index=0, start_offset_min=60, duration_min=30)
        with pytest.raises(HTTPException) as exc:
            validate_segments([a, b], location_count=1, event_start=_EVENT_START, event_end=_EVENT_END)
        assert "contiguous order_index" in exc.value.detail

    def test_overlap_rule_is_location_independent(self):
        # Issue spec says "no time overlaps" — the rule is global, not per-location.
        # Two segments at different stops still cannot overlap in time.
        a = _seg(location_index=0, order_index=0, start_offset_min=0, duration_min=60)
        b = _seg(location_index=1, order_index=1, start_offset_min=30, duration_min=60)
        with pytest.raises(HTTPException):
            validate_segments([a, b], location_count=2, event_start=_EVENT_START, event_end=_EVENT_END)


# --- _build_segment_rows -----------------------------------------------------

class TestBuildSegmentRows:
    def test_none_returns_none(self):
        assert _build_segment_rows(None) is None

    def test_empty_returns_empty_list(self):
        assert _build_segment_rows([]) == []

    def test_serialises_isoformat_and_description(self):
        seg = _seg(description="Opening")
        rows = _build_segment_rows([seg])
        assert len(rows) == 1
        row = rows[0]
        assert row["location_index"] == 0
        assert row["order_index"] == 0
        # ISO format strings only — RPC casts these to TIMESTAMPTZ
        assert isinstance(row["start_datetime"], str)
        assert "T" in row["start_datetime"]
        assert row["description"] == "Opening"

    def test_description_none_preserved(self):
        rows = _build_segment_rows([_seg(description=None)])
        assert rows[0]["description"] is None


# --- update_event segment guards ---------------------------------------------

class TestUpdateEventSegmentGuards:
    """Unit-level coverage of the new branches in update_event.

    All DB calls are mocked — these tests run in the unit-fast shard.
    """

    def _make_event(self, *, started: bool, locations_count: int = 1, status_str: str = "published"):
        from app.repositories import event as repo
        from app.services import event as svc

        host_id = str(uuid4())
        event_id = str(uuid4())
        # event start must be in the past for `started=True`
        event_start = (
            datetime.now(UTC) - timedelta(hours=1) if started
            else datetime.now(UTC) + timedelta(hours=2)
        )
        event_row = {
            "id": event_id,
            "host_id": host_id,
            "title": "T",
            "description": "D",
            "start_datetime": event_start.isoformat(),
            "end_datetime": (event_start + timedelta(hours=4)).isoformat(),
            "visibility": "public",
            "is_age_restricted": False,
            "attendee_limit": None,
            "attendee_count": 0,
            "status": status_str,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        location_rows = [{"id": str(uuid4()), "order_index": i} for i in range(locations_count)]
        return host_id, event_id, event_row, location_rows, repo, svc

    def test_segments_after_start_rejected(self, monkeypatch):
        host_id, event_id, event_row, _locs, repo, svc = self._make_event(started=True)

        monkeypatch.setattr(repo, "get_event_by_id", lambda _db, _eid: event_row)

        body = EventUpdateRequest(segments=[_seg()])
        with pytest.raises(HTTPException) as exc:
            svc.update_event(MagicMock(), event_id, host_id, body)
        assert exc.value.status_code == 400
        assert "after event has started" in exc.value.detail

    def test_replacing_locations_without_segments_when_segments_exist_rejected(self, monkeypatch):
        host_id, event_id, event_row, locs, repo, svc = self._make_event(
            started=False, locations_count=2,
        )

        monkeypatch.setattr(repo, "get_event_by_id", lambda _db, _eid: event_row)
        monkeypatch.setattr(repo, "get_event_locations", lambda _db, _eid: locs)
        monkeypatch.setattr(
            repo, "get_event_segments",
            lambda _db, _eid: [{"id": str(uuid4()), "order_index": 0}],
        )

        new_locs = [
            LocationRequest(name="L1", latitude=1.0, longitude=2.0, is_primary=True, order_index=0),
            LocationRequest(name="L2", latitude=3.0, longitude=4.0, is_primary=False, order_index=1),
        ]
        body = EventUpdateRequest(locations=new_locs)
        with pytest.raises(HTTPException) as exc:
            svc.update_event(MagicMock(), event_id, host_id, body)
        assert exc.value.status_code == 400
        assert "clears existing segments" in exc.value.detail

    def test_replacing_locations_without_segments_when_no_segments_allowed(self, monkeypatch):
        # No existing segments → the silent-clear concern doesn't apply, so
        # the location update should not be blocked by the segment guard.
        host_id, event_id, event_row, locs, repo, svc = self._make_event(
            started=False, locations_count=1,
        )

        monkeypatch.setattr(repo, "get_event_by_id", lambda _db, _eid: event_row)
        monkeypatch.setattr(repo, "get_event_locations", lambda _db, _eid: locs)
        monkeypatch.setattr(repo, "get_event_segments", lambda _db, _eid: [])
        monkeypatch.setattr(repo, "update_event_atomic", lambda *_a, **_kw: event_row)
        # Stub get_event_detail to short-circuit the response build (we only
        # care that the guard didn't raise here).
        monkeypatch.setattr(svc, "get_event_detail", lambda _db, _eid, _uid: None)

        new_locs = [
            LocationRequest(name="L1", latitude=1.0, longitude=2.0, is_primary=True, order_index=0),
        ]
        body = EventUpdateRequest(locations=new_locs)
        # Should not raise
        svc.update_event(MagicMock(), event_id, host_id, body)

    def test_time_change_after_start_rejected(self, monkeypatch):
        # Sanity-pin the existing FRS-2 guard so it doesn't regress alongside
        # the new segment guard.
        host_id, event_id, event_row, _locs, repo, svc = self._make_event(started=True)
        monkeypatch.setattr(repo, "get_event_by_id", lambda _db, _eid: event_row)
        body = EventUpdateRequest(start_datetime=datetime.now(UTC) + timedelta(hours=5))
        with pytest.raises(HTTPException) as exc:
            svc.update_event(MagicMock(), event_id, host_id, body)
        assert exc.value.status_code == 400
        assert "time after event has started" in exc.value.detail

    def test_location_change_after_start_rejected(self, monkeypatch):
        host_id, event_id, event_row, _locs, repo, svc = self._make_event(started=True)
        monkeypatch.setattr(repo, "get_event_by_id", lambda _db, _eid: event_row)
        body = EventUpdateRequest(locations=[
            LocationRequest(name="L", latitude=0.0, longitude=0.0, is_primary=True, order_index=0),
        ])
        with pytest.raises(HTTPException) as exc:
            svc.update_event(MagicMock(), event_id, host_id, body)
        assert exc.value.status_code == 400
        assert "locations after event has started" in exc.value.detail

    def test_segments_validated_against_stored_window_when_body_has_no_dates(self, monkeypatch):
        # body.segments provided, body.start_datetime / body.end_datetime omitted.
        # The validator must compare against the stored window (effective fall-back).
        host_id, event_id, event_row, locs, repo, svc = self._make_event(
            started=False, locations_count=1,
        )
        # Stored window: now+2h to now+6h. We send a segment outside that range.
        out_of_window_segment = SegmentRequest(
            location_index=0,
            order_index=0,
            start_datetime=datetime.now(UTC) + timedelta(hours=10),
            end_datetime=datetime.now(UTC) + timedelta(hours=11),
        )

        monkeypatch.setattr(repo, "get_event_by_id", lambda _db, _eid: event_row)
        monkeypatch.setattr(repo, "get_event_locations", lambda _db, _eid: locs)
        monkeypatch.setattr(repo, "get_event_segments", lambda _db, _eid: [])

        body = EventUpdateRequest(segments=[out_of_window_segment])
        with pytest.raises(HTTPException) as exc:
            svc.update_event(MagicMock(), event_id, host_id, body)
        assert exc.value.status_code == 400
        assert "within event" in exc.value.detail


# --- Duplicate-event detection: primary-location scoping --------------------

class TestFindLocationByEventAndNamePrimaryOnly:
    """find_location_by_event_and_name must filter on is_primary=True so the
    duplicate-event guard only fires on primary-location collisions
    (issue #149 FRS-2)."""

    def test_query_includes_is_primary_filter(self):
        db = MagicMock()
        # Build a chain that records each .eq() call so we can inspect them.
        chain = db.table.return_value.select.return_value
        chain.eq.return_value = chain  # eq returns the same chainable object
        chain.execute.return_value.data = []

        event_repo.find_location_by_event_and_name(db, "event-id", "Main hall")

        eq_calls = chain.eq.call_args_list
        kv = {call.args[0]: call.args[1] for call in eq_calls}
        # Must filter by event_id, name, AND is_primary=True
        assert kv["event_id"] == "event-id"
        assert kv["name"] == "Main hall"
        assert kv["is_primary"] is True

    def test_returns_empty_list_when_data_is_none(self):
        db = MagicMock()
        chain = db.table.return_value.select.return_value
        chain.eq.return_value = chain
        chain.execute.return_value.data = None

        assert event_repo.find_location_by_event_and_name(db, "e", "n") == []


class TestCheckDuplicateEvent:
    """Service-layer wrapper around find_location_by_event_and_name."""

    def test_no_collision_when_no_matching_event(self, monkeypatch):
        from app.services import event as svc

        monkeypatch.setattr(event_repo, "find_duplicate_events", lambda *_a, **_k: [])
        # No HTTPException expected
        svc.check_duplicate_event(MagicMock(), "host", "Title", "2030-01-01T10:00:00+00:00", "Main hall")

    def test_no_collision_when_primary_name_does_not_match(self, monkeypatch):
        from app.services import event as svc

        monkeypatch.setattr(
            event_repo, "find_duplicate_events", lambda *_a, **_k: [{"id": "e1"}],
        )
        # Repo is now primary-scoped — when the candidate event has a different
        # primary, the repo returns []
        monkeypatch.setattr(
            event_repo, "find_location_by_event_and_name", lambda *_a, **_k: [],
        )
        svc.check_duplicate_event(MagicMock(), "host", "Title", "2030-01-01T10:00:00+00:00", "Main hall")

    def test_collision_when_primary_name_matches(self, monkeypatch):
        from app.services import event as svc

        monkeypatch.setattr(
            event_repo, "find_duplicate_events", lambda *_a, **_k: [{"id": "e1"}],
        )
        monkeypatch.setattr(
            event_repo, "find_location_by_event_and_name",
            lambda *_a, **_k: [{"name": "Main hall"}],
        )
        with pytest.raises(HTTPException) as exc:
            svc.check_duplicate_event(MagicMock(), "host", "Title", "2030-01-01T10:00:00+00:00", "Main hall")
        assert exc.value.status_code == 409
        assert "primary location" in exc.value.detail


# --- delete_event emits event_deleted before the row is gone ----------------

class TestDeleteEventEmitsBeforeDelete:
    def _event(self, event_status="cancelled"):
        host_id = str(uuid4())
        event_id = str(uuid4())
        return host_id, event_id, {
            "id": event_id,
            "host_id": host_id,
            "title": "Doomed event",
            "status": event_status,
        }

    def test_emits_event_deleted_before_event_repo_delete(self, monkeypatch):
        from app.repositories import event as repo
        from app.repositories import image as image_repo_mod
        from app.services import event as svc
        from app.services import notification_emitter as ne

        host_id, event_id, event_row = self._event()
        monkeypatch.setattr(repo, "get_event_by_id", lambda _db, _eid: event_row)
        monkeypatch.setattr(image_repo_mod, "get_all_event_images", lambda _db, _eid: [])

        call_log: list[str] = []

        def fake_emit(_db, eid, _user, ntype, _msg):
            call_log.append(f"emit:{ntype}:{eid}")
            return 0

        def fake_delete(_db, eid):
            call_log.append(f"delete:{eid}")

        monkeypatch.setattr(ne, "emit_event_notification", fake_emit)
        monkeypatch.setattr(repo, "delete_event", fake_delete)

        svc.delete_event(MagicMock(), event_id, host_id)

        assert call_log == [f"emit:event_deleted:{event_id}", f"delete:{event_id}"]

    def test_delete_blocked_for_non_terminal_status(self, monkeypatch):
        from app.repositories import event as repo
        from app.services import event as svc

        host_id, event_id, event_row = self._event(event_status="published")
        monkeypatch.setattr(repo, "get_event_by_id", lambda _db, _eid: event_row)

        with pytest.raises(HTTPException) as exc:
            svc.delete_event(MagicMock(), event_id, host_id)
        assert exc.value.status_code == 400

    def test_only_host_can_delete(self, monkeypatch):
        from app.repositories import event as repo
        from app.services import event as svc

        host_id, event_id, event_row = self._event()
        monkeypatch.setattr(repo, "get_event_by_id", lambda _db, _eid: event_row)

        someone_else = str(uuid4())
        with pytest.raises(HTTPException) as exc:
            svc.delete_event(MagicMock(), event_id, someone_else)
        assert exc.value.status_code == 403


# --- access_rejected emission verification ---------------------------------

class TestAccessRejectedEmission:
    """Pin the existing rejection flow in services/invite.py so the
    notification row is always written when a host rejects an access request.

    Mocks every dependency; this is a pure-logic check that the rejected
    branch of update_access_request inserts a row of type 'access_rejected'.
    """

    def test_rejection_inserts_access_rejected_notification(self, monkeypatch):
        from app.models.invite import AccessRequestDecision
        from app.repositories import event as event_repo_mod
        from app.repositories import invite as invite_repo_mod
        from app.repositories import notification as notif_repo_mod
        from app.repositories import user as user_repo_mod
        from app.services import invite as invite_svc

        host_id = str(uuid4())
        event_id = str(uuid4())
        request_id = str(uuid4())
        requester_id = str(uuid4())

        event_row = {
            "id": event_id, "host_id": host_id, "title": "Private gala",
            "status": "published",
        }
        request_row = {
            "id": request_id, "event_id": event_id, "user_id": requester_id, "status": "pending",
        }
        updated_row = {
            **request_row, "status": "rejected", "resolved_at": "2030-01-01T00:00:00+00:00",
            "created_at": "2030-01-01T00:00:00+00:00",
        }

        monkeypatch.setattr(event_repo_mod, "get_event_by_id", lambda _db, _eid: event_row)
        monkeypatch.setattr(
            invite_repo_mod, "get_access_request_by_id", lambda _db, _rid: request_row,
        )
        monkeypatch.setattr(
            invite_repo_mod, "update_access_request",
            lambda _db, _rid, _data: updated_row,
        )
        monkeypatch.setattr(
            user_repo_mod, "get_user_by_id",
            lambda _db, _uid: {"id": requester_id, "username": "alice"},
        )

        inserted: list[dict] = []
        monkeypatch.setattr(
            notif_repo_mod, "insert_notification",
            lambda _db, row: inserted.append(row) or row,
        )

        invite_svc.decide_access_request(
            MagicMock(),
            event_id=event_id,
            request_id=request_id,
            user_id=host_id,
            body=AccessRequestDecision(status="rejected"),
        )

        rejected_rows = [r for r in inserted if r.get("type") == "access_rejected"]
        assert len(rejected_rows) == 1
        row = rejected_rows[0]
        assert row["user_id"] == requester_id
        assert row["event_id"] == event_id
        assert row["is_read"] is False

    def test_approval_does_not_emit_access_rejected(self, monkeypatch):
        # Make sure the rejection branch is exclusive — approving must not
        # write an 'access_rejected' row.
        from app.models.invite import AccessRequestDecision
        from app.repositories import event as event_repo_mod
        from app.repositories import invite as invite_repo_mod
        from app.repositories import notification as notif_repo_mod
        from app.repositories import user as user_repo_mod
        from app.services import invite as invite_svc

        host_id = str(uuid4())
        event_id = str(uuid4())
        request_id = str(uuid4())
        requester_id = str(uuid4())

        event_row = {"id": event_id, "host_id": host_id, "title": "T", "status": "published"}
        request_row = {
            "id": request_id, "event_id": event_id, "user_id": requester_id, "status": "pending",
        }
        updated_row = {**request_row, "status": "approved", "created_at": "2030-01-01T00:00:00+00:00"}

        monkeypatch.setattr(event_repo_mod, "get_event_by_id", lambda *_a, **_k: event_row)
        monkeypatch.setattr(invite_repo_mod, "get_access_request_by_id", lambda *_a, **_k: request_row)
        monkeypatch.setattr(invite_repo_mod, "update_access_request", lambda *_a, **_k: updated_row)
        monkeypatch.setattr(invite_repo_mod, "insert_access_grant", lambda *_a, **_k: None)
        monkeypatch.setattr(
            user_repo_mod, "get_user_by_id",
            lambda *_a, **_k: {"id": requester_id, "username": "alice"},
        )

        inserted: list[dict] = []
        monkeypatch.setattr(
            notif_repo_mod, "insert_notification",
            lambda _db, row: inserted.append(row) or row,
        )

        invite_svc.decide_access_request(
            MagicMock(),
            event_id=event_id,
            request_id=request_id,
            user_id=host_id,
            body=AccessRequestDecision(status="approved"),
        )

        assert all(r.get("type") != "access_rejected" for r in inserted)
