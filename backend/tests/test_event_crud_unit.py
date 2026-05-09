"""Unit tests for `services.event` CRUD (Phase 1 slice B).

Targets create_event, update_event, change_event_status, delete_event with
mocked repo modules through the keyword-default DI seam. Validators they
delegate to are covered by `test_event_validators_unit.py`; here we focus on
the CRUD-specific branches: ownership/status/lifecycle gates and orchestration.

`update_event` and `change_event_status` end in `get_event_detail`, which
still talks to the live event_repo module (slice C). Those tests
monkeypatch the function on the service so the unit stays isolated.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.event import (
    EquipmentRequest,
    EventCreateRequest,
    EventUpdateRequest,
    LocationRequest,
    SegmentRequest,
    VenueMetadataRequest,
)
from app.services import event as event_service

HOST_ID = "00000000-0000-0000-0000-0000000000a0"
OTHER_USER = "00000000-0000-0000-0000-0000000000b0"
EVENT_ID = "00000000-0000-0000-0000-0000000000a1"
CAT_A = "00000000-0000-0000-0000-0000000000a2"


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


@pytest.fixture
def events_repo():
    """Mock EventRepoProtocol implementor with sensible defaults."""
    m = MagicMock(name="event_repo")
    m.get_valid_category_ids.return_value = {CAT_A}
    m.find_duplicate_events.return_value = []
    m.get_rate_limit_config.return_value = None
    return m


@pytest.fixture
def users_repo():
    m = MagicMock(name="user_repo")
    m.get_user_email_by_id.return_value = "alice@example.com"
    return m


@pytest.fixture
def images_repo():
    m = MagicMock(name="image_repo")
    m.BUCKET_NAME = "event-images"
    m.get_all_event_images.return_value = []
    return m


def _future(hours_ahead: int = 24) -> datetime:
    return datetime.now(UTC) + timedelta(hours=hours_ahead)


def _build_create_body(*, status: str = "draft", with_segments: bool = False) -> EventCreateRequest:
    start = _future(24)
    end = start + timedelta(hours=2)
    body = EventCreateRequest(
        title="Festival",
        description="A great event",
        start_datetime=start,
        end_datetime=end,
        visibility="public",
        is_age_restricted=False,
        attendee_limit=None,
        status=status,
        category_ids=[CAT_A],
        locations=[
            LocationRequest(
                name="Main Stage",
                latitude=41.0,
                longitude=29.0,
                is_primary=True,
                order_index=0,
            ),
        ],
        venue_metadata=VenueMetadataRequest(price="free"),
        equipment_requirements=[EquipmentRequest(item_name="mic")],
        segments=(
            [
                SegmentRequest(
                    location_index=0, order_index=0,
                    start_datetime=start, end_datetime=start + timedelta(hours=1),
                ),
            ]
            if with_segments else None
        ),
    )
    return body


def _stub_event_row(**overrides) -> dict:
    base = {
        "id": EVENT_ID,
        "host_id": HOST_ID,
        "title": "Festival",
        "description": "A great event",
        "start_datetime": _future(24).isoformat(),
        "end_datetime": _future(26).isoformat(),
        "visibility": "public",
        "is_age_restricted": False,
        "attendee_limit": None,
        "attendee_count": 0,
        "status": "published",
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    base.update(overrides)
    return base


# ── create_event ────────────────────────────────────────────────────────────


class TestCreateEvent:
    def test_400_when_publishing_directly(self, db, events_repo, users_repo):
        body = _build_create_body(status="published")
        with pytest.raises(HTTPException) as exc:
            event_service.create_event(
                db, HOST_ID, body, events=events_repo, users=users_repo,
            )
        assert exc.value.status_code == 400

    def test_500_when_atomic_create_returns_falsy(self, db, events_repo, users_repo):
        events_repo.create_event_atomic.return_value = None
        body = _build_create_body()
        with pytest.raises(HTTPException) as exc:
            event_service.create_event(
                db, HOST_ID, body, events=events_repo, users=users_repo,
            )
        assert exc.value.status_code == 500

    def test_happy_path_calls_atomic_create_and_builds_response(
        self, db, events_repo, users_repo,
    ):
        events_repo.create_event_atomic.return_value = _stub_event_row(status="draft")
        events_repo.get_event_locations.return_value = []
        events_repo.get_event_categories.return_value = []
        events_repo.get_venue_metadata.return_value = None
        events_repo.get_equipment.return_value = []
        events_repo.get_event_segments.return_value = []

        body = _build_create_body()
        resp = event_service.create_event(
            db, HOST_ID, body, events=events_repo, users=users_repo,
        )

        assert str(resp.id) == EVENT_ID
        events_repo.create_event_atomic.assert_called_once()
        events_repo.get_valid_category_ids.assert_called_once()
        events_repo.find_duplicate_events.assert_called_once()

    def test_forces_primary_when_no_location_marked_primary(
        self, db, events_repo, users_repo,
    ):
        events_repo.create_event_atomic.return_value = _stub_event_row(status="draft")
        events_repo.get_event_locations.return_value = []
        events_repo.get_event_categories.return_value = []
        events_repo.get_venue_metadata.return_value = None
        events_repo.get_equipment.return_value = []
        events_repo.get_event_segments.return_value = []

        body = _build_create_body()
        # Strip the default is_primary=True so first location must be auto-promoted.
        body.locations[0].is_primary = False

        event_service.create_event(
            db, HOST_ID, body, events=events_repo, users=users_repo,
        )

        sent = events_repo.create_event_atomic.call_args.kwargs
        assert sent["locations"][0]["is_primary"] is True


# ── update_event ────────────────────────────────────────────────────────────


@pytest.fixture
def patched_get_event_detail(monkeypatch):
    """Replace `event_service.get_event_detail` with a stub that returns a sentinel
    EventDetailResponse-shaped MagicMock; lets update/status tests reach the end."""
    sentinel = MagicMock(name="event_detail_response")
    monkeypatch.setattr(event_service, "get_event_detail", lambda *a, **kw: sentinel)
    return sentinel


class TestUpdateEvent:
    def test_404_when_missing(self, db, events_repo):
        events_repo.get_event_by_id.return_value = None
        body = EventUpdateRequest(title="New")
        with pytest.raises(HTTPException) as exc:
            event_service.update_event(db, EVENT_ID, HOST_ID, body, events=events_repo)
        assert exc.value.status_code == 404

    def test_403_when_not_host(self, db, events_repo):
        events_repo.get_event_by_id.return_value = _stub_event_row()
        body = EventUpdateRequest(title="New")
        with pytest.raises(HTTPException) as exc:
            event_service.update_event(db, EVENT_ID, OTHER_USER, body, events=events_repo)
        assert exc.value.status_code == 403

    @pytest.mark.parametrize("status_value", ["cancelled", "ended"])
    def test_400_when_event_already_terminal(self, db, events_repo, status_value):
        events_repo.get_event_by_id.return_value = _stub_event_row(status=status_value)
        body = EventUpdateRequest(title="New")
        with pytest.raises(HTTPException) as exc:
            event_service.update_event(db, EVENT_ID, HOST_ID, body, events=events_repo)
        assert exc.value.status_code == 400

    def test_400_when_modifying_time_after_event_started(self, db, events_repo):
        past_start = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        events_repo.get_event_by_id.return_value = _stub_event_row(
            start_datetime=past_start,
        )
        body = EventUpdateRequest(start_datetime=_future(48))
        with pytest.raises(HTTPException) as exc:
            event_service.update_event(db, EVENT_ID, HOST_ID, body, events=events_repo)
        assert exc.value.status_code == 400

    def test_400_when_locations_replace_drops_existing_segments_silently(
        self, db, events_repo,
    ):
        events_repo.get_event_by_id.return_value = _stub_event_row()
        events_repo.get_event_segments.return_value = [{"id": "seg1"}]
        body = EventUpdateRequest(
            locations=[LocationRequest(name="New", latitude=1.0, longitude=1.0)],
            # segments left None -> service must reject
        )
        with pytest.raises(HTTPException) as exc:
            event_service.update_event(db, EVENT_ID, HOST_ID, body, events=events_repo)
        assert exc.value.status_code == 400

    def test_happy_path_published_event_flips_to_updated_status(
        self, db, events_repo, patched_get_event_detail, monkeypatch,
    ):
        events_repo.get_event_by_id.return_value = _stub_event_row(status="published")
        # No-op the notification emitter side effect.
        from app.services import notification_emitter
        monkeypatch.setattr(notification_emitter, "emit_event_notification", lambda *a, **k: None)

        body = EventUpdateRequest(title="Renamed")
        result = event_service.update_event(
            db, EVENT_ID, HOST_ID, body, events=events_repo,
        )

        assert result is patched_get_event_detail
        sent = events_repo.update_event_atomic.call_args.kwargs
        assert sent["event_data"]["status"] == "updated"
        assert sent["event_data"]["title"] == "Renamed"


# ── change_event_status ─────────────────────────────────────────────────────


class TestChangeEventStatus:
    def test_404_when_missing(self, db, events_repo):
        events_repo.get_event_by_id.return_value = None
        with pytest.raises(HTTPException) as exc:
            event_service.change_event_status(
                db, EVENT_ID, HOST_ID, "published", events=events_repo,
            )
        assert exc.value.status_code == 404

    def test_403_when_not_host(self, db, events_repo):
        events_repo.get_event_by_id.return_value = _stub_event_row(status="draft")
        with pytest.raises(HTTPException) as exc:
            event_service.change_event_status(
                db, EVENT_ID, OTHER_USER, "published", events=events_repo,
            )
        assert exc.value.status_code == 403

    def test_400_on_invalid_transition(self, db, events_repo):
        events_repo.get_event_by_id.return_value = _stub_event_row(status="draft")
        with pytest.raises(HTTPException) as exc:
            event_service.change_event_status(
                db, EVENT_ID, HOST_ID, "cancelled", events=events_repo,
            )
        assert exc.value.status_code == 400

    def test_400_publish_with_past_start(self, db, events_repo):
        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        events_repo.get_event_by_id.return_value = _stub_event_row(
            status="draft", start_datetime=past,
        )
        with pytest.raises(HTTPException) as exc:
            event_service.change_event_status(
                db, EVENT_ID, HOST_ID, "published", events=events_repo,
            )
        assert exc.value.status_code == 400

    def test_400_publish_without_locations(self, db, events_repo):
        events_repo.get_event_by_id.return_value = _stub_event_row(status="draft")
        events_repo.get_event_locations.return_value = []
        with pytest.raises(HTTPException) as exc:
            event_service.change_event_status(
                db, EVENT_ID, HOST_ID, "published", events=events_repo,
            )
        assert exc.value.status_code == 400

    def test_400_publish_without_categories(self, db, events_repo):
        events_repo.get_event_by_id.return_value = _stub_event_row(status="draft")
        events_repo.get_event_locations.return_value = [{"id": "loc1"}]
        events_repo.get_event_categories.return_value = []
        with pytest.raises(HTTPException) as exc:
            event_service.change_event_status(
                db, EVENT_ID, HOST_ID, "published", events=events_repo,
            )
        assert exc.value.status_code == 400

    def test_400_publish_without_images(self, db, events_repo):
        events_repo.get_event_by_id.return_value = _stub_event_row(status="draft")
        events_repo.get_event_locations.return_value = [{"id": "loc1"}]
        events_repo.get_event_categories.return_value = [{"id": "cat1"}]
        events_repo.get_event_images.return_value = []
        with pytest.raises(HTTPException) as exc:
            event_service.change_event_status(
                db, EVENT_ID, HOST_ID, "published", events=events_repo,
            )
        assert exc.value.status_code == 400

    def test_cancel_emits_notification(
        self, db, events_repo, patched_get_event_detail, monkeypatch,
    ):
        events_repo.get_event_by_id.return_value = _stub_event_row(status="published")
        emitted = []
        from app.services import notification_emitter
        monkeypatch.setattr(
            notification_emitter,
            "emit_event_notification",
            lambda *args, **kw: emitted.append(args),
        )

        result = event_service.change_event_status(
            db, EVENT_ID, HOST_ID, "cancelled", events=events_repo,
        )

        assert result is patched_get_event_detail
        events_repo.update_event_status.assert_called_once_with(db, EVENT_ID, "cancelled")
        assert len(emitted) == 1


# ── delete_event ────────────────────────────────────────────────────────────


class TestDeleteEvent:
    def test_404_when_missing(self, db, events_repo, images_repo):
        events_repo.get_event_by_id.return_value = None
        with pytest.raises(HTTPException) as exc:
            event_service.delete_event(
                db, EVENT_ID, HOST_ID, events=events_repo, images=images_repo,
            )
        assert exc.value.status_code == 404

    def test_403_when_not_host(self, db, events_repo, images_repo):
        events_repo.get_event_by_id.return_value = _stub_event_row(status="cancelled")
        with pytest.raises(HTTPException) as exc:
            event_service.delete_event(
                db, EVENT_ID, OTHER_USER, events=events_repo, images=images_repo,
            )
        assert exc.value.status_code == 403

    @pytest.mark.parametrize("status_value", ["draft", "published", "updated"])
    def test_400_for_non_terminal_event(self, db, events_repo, images_repo, status_value):
        events_repo.get_event_by_id.return_value = _stub_event_row(status=status_value)
        with pytest.raises(HTTPException) as exc:
            event_service.delete_event(
                db, EVENT_ID, HOST_ID, events=events_repo, images=images_repo,
            )
        assert exc.value.status_code == 400

    def test_happy_path_emits_notification_cleans_storage_then_deletes(
        self, db, events_repo, images_repo, monkeypatch,
    ):
        events_repo.get_event_by_id.return_value = _stub_event_row(status="cancelled")
        images_repo.get_all_event_images.return_value = [
            {"image_url": "https://supabase.example/storage/event-images/abc.jpg"},
        ]
        emitted = []
        from app.services import notification_emitter
        monkeypatch.setattr(
            notification_emitter,
            "emit_event_notification",
            lambda *args, **kw: emitted.append(args[3]),  # type
        )

        event_service.delete_event(
            db, EVENT_ID, HOST_ID, events=events_repo, images=images_repo,
        )

        assert emitted == ["event_deleted"]
        images_repo.delete_from_storage.assert_called_once_with(db, "abc.jpg")
        events_repo.delete_event.assert_called_once_with(db, EVENT_ID)

    def test_storage_failure_does_not_block_db_delete(
        self, db, events_repo, images_repo, monkeypatch,
    ):
        events_repo.get_event_by_id.return_value = _stub_event_row(status="ended")
        images_repo.get_all_event_images.return_value = [
            {"image_url": "https://supabase.example/storage/event-images/abc.jpg"},
        ]
        images_repo.delete_from_storage.side_effect = RuntimeError("storage timeout")
        from app.services import notification_emitter
        monkeypatch.setattr(notification_emitter, "emit_event_notification", lambda *a, **k: None)

        event_service.delete_event(
            db, EVENT_ID, HOST_ID, events=events_repo, images=images_repo,
        )

        events_repo.delete_event.assert_called_once_with(db, EVENT_ID)
