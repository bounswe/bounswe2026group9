"""Snapshot tests for the response shapes that consumers actually parse.

Snapshots pin the exact JSON skeleton — not the values, but the keys
present, the types, and the structure — so an accidental rename or
reorder gets caught before the frontend has to chase a regression.
syrupy stores the expected output beside this file in
``__snapshots__/`` and asserts against it.

To regenerate after an intentional change:

    pytest tests/test_event_responses_snapshot.py --snapshot-update
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.services import event as event_service

EVENT_ID = "00000000-0000-0000-0000-000000000001"
HOST_ID = "00000000-0000-0000-0000-000000000002"
LOC_ID = "00000000-0000-0000-0000-000000000003"
CAT_ID = "00000000-0000-0000-0000-000000000004"


@pytest.fixture
def db() -> MagicMock:
    return MagicMock(name="supabase_client")


@pytest.fixture
def events_repo() -> MagicMock:
    return MagicMock(name="event_repo")


@pytest.fixture
def users_repo() -> MagicMock:
    m = MagicMock(name="user_repo")
    m.get_user_by_id.return_value = {"id": HOST_ID, "username": "host"}
    m.get_users_by_ids.return_value = []
    m.get_user_default_area.return_value = (None, None)
    return m


@pytest.fixture
def bookmarks_repo() -> MagicMock:
    m = MagicMock(name="bookmark_repo")
    m.get_bookmark.return_value = None
    m.get_bookmark_count_for_event.return_value = 0
    m.get_bookmark_counts_for_events.return_value = {}
    m.get_bookmark_status_for_events.return_value = set()
    return m


@pytest.fixture
def attendances_repo() -> MagicMock:
    m = MagicMock(name="attendance_repo")
    m.get_attendance.return_value = None
    m.get_going_user_ids_for_event.return_value = []
    m.get_attendance_status_for_events.return_value = {}
    m.get_attended_ended_event_categories.return_value = set()
    return m


@pytest.fixture
def invites_repo() -> MagicMock:
    m = MagicMock(name="invite_repo")
    m.get_access_request.return_value = None
    m.get_access_grant.return_value = None
    m.get_access_request_status_for_events.return_value = {}
    m.get_access_granted_event_ids.return_value = set()
    return m


def _stub_event(**overrides: object) -> dict:
    base: dict[str, object] = {
        "id": EVENT_ID,
        "host_id": HOST_ID,
        "title": "Snapshot Event",
        "description": "Snapshot description",
        "start_datetime": "2030-06-01T10:00:00+00:00",
        "end_datetime": "2030-06-01T12:00:00+00:00",
        "visibility": "public",
        "is_age_restricted": False,
        "attendee_limit": None,
        "attendee_count": 5,
        "status": "published",
        "created_at": "2030-05-01T00:00:00+00:00",
        "updated_at": "2030-05-15T00:00:00+00:00",
    }
    base.update(overrides)
    return base


def _all_repos(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo):
    return {
        "events": events_repo,
        "users": users_repo,
        "bookmarks": bookmarks_repo,
        "attendances": attendances_repo,
        "invites": invites_repo,
    }


def _normalise(payload):  # type: ignore[no-untyped-def]
    """Replace UUIDs/datetimes that aren't part of the contract.

    Snapshots compare against the *shape* of the response, not the
    runtime values. Strip out the IDs/created_at/updated_at fields the
    repo would normally fill so the snapshot doesn't churn between
    runs."""
    if isinstance(payload, dict):
        return {k: ("<*>" if k in ("id", "host_id", "rater_id") else _normalise(v))
                for k, v in payload.items()}
    if isinstance(payload, list):
        return [_normalise(item) for item in payload]
    return payload


def test_event_detail_shape(
    db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo, snapshot,
) -> None:
    events_repo.get_event_by_id.return_value = _stub_event()
    events_repo.get_event_categories.return_value = [
        {"id": CAT_ID, "name": "Music", "is_predefined": True, "is_approved": True},
    ]
    events_repo.get_event_locations.return_value = [
        {
            "id": LOC_ID, "name": "Main Stage", "latitude": 41.0, "longitude": 29.0,
            "is_primary": True, "order_index": 0, "location_address": None,
        },
    ]
    events_repo.get_event_images.return_value = []
    events_repo.get_venue_metadata.return_value = None
    events_repo.get_equipment.return_value = []
    events_repo.get_event_segments.return_value = []

    resp = event_service.get_event_detail(
        db, EVENT_ID, HOST_ID,
        **_all_repos(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
    )

    assert _normalise(resp.model_dump(mode="json")) == snapshot


def test_event_list_shape(
    db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo, snapshot,
) -> None:
    events_repo.list_events.return_value = ([_stub_event()], 1)
    events_repo.get_primary_locations_for_events.return_value = {
        EVENT_ID: {
            "id": LOC_ID, "name": "Main Stage", "latitude": 41.0, "longitude": 29.0,
            "is_primary": True, "order_index": 0, "location_address": None,
        },
    }
    events_repo.get_categories_for_events.return_value = {
        EVENT_ID: [
            {"id": CAT_ID, "name": "Music", "is_predefined": True, "is_approved": True},
        ],
    }
    events_repo.get_primary_images_for_events.return_value = {}

    resp = event_service.list_events(
        db, user_id=HOST_ID,
        **_all_repos(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
    )

    assert _normalise(resp.model_dump(mode="json")) == snapshot


def test_event_geojson_feature_shape(
    db, events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo, snapshot,
) -> None:
    events_repo.list_events.return_value = ([_stub_event()], 1)
    events_repo.get_primary_locations_for_events.return_value = {
        EVENT_ID: {
            "id": LOC_ID, "name": "Main Stage", "latitude": 41.0, "longitude": 29.0,
            "is_primary": True, "order_index": 0, "location_address": None,
        },
    }
    events_repo.get_categories_for_events.return_value = {
        EVENT_ID: [{"id": CAT_ID, "name": "Music", "is_predefined": True, "is_approved": True}],
    }
    events_repo.get_primary_images_for_events.return_value = {}

    resp = event_service.list_events_geojson(
        db,
        **_all_repos(events_repo, users_repo, bookmarks_repo, attendances_repo, invites_repo),
    )

    assert _normalise(resp.model_dump(mode="json")) == snapshot
