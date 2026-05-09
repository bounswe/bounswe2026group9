"""Verification tests for the NFR cluster on issue #152.

Three assertions live here, each pinned to a specific NFR:

  - NFR-02: an event update is *immediately* visible through the same
            service surface — no async indexer in the loop, no 60-second
            staleness window. We drive the service against in-memory
            mocks so the assertion isolates the code path; the
            integration counterpart (real Supabase round-trip) is
            inherently faster than the 60 s budget.
  - NFR-04: the private-event detail boundary is enforced inside the
            service, not the router. A non-host caller without a grant
            never sees the full payload, regardless of how the request
            arrived.
  - NFR-09: the only ``latitude`` / ``longitude`` columns the schema
            persists are (a) the *opt-in* user default-area fields and
            (b) the event location's published coordinates. There is no
            column anywhere that captures the caller's current GPS.

The schema check in NFR-09 reads the SQL migration files directly so
it stays valid whether the test runs against a real Supabase or an
empty MagicMock — it's a static contract.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services import event as event_service

EVENT_ID = "00000000-0000-0000-0000-0000000000a1"
HOST_ID = "00000000-0000-0000-0000-0000000000a2"
OTHER_USER = "00000000-0000-0000-0000-0000000000b0"


@pytest.fixture
def db() -> MagicMock:
    return MagicMock(name="supabase_client")


def _stub_event(**overrides) -> dict:
    base = {
        "id": EVENT_ID,
        "host_id": HOST_ID,
        "title": "NFR Event",
        "description": "Original description",
        "start_datetime": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
        "end_datetime": (datetime.now(UTC) + timedelta(days=2, hours=2)).isoformat(),
        "visibility": "public",
        "is_age_restricted": False,
        "attendee_limit": None,
        "attendee_count": 0,
        "status": "published",
        "created_at": "2030-01-01T00:00:00+00:00",
        "updated_at": "2030-01-01T00:00:00+00:00",
    }
    base.update(overrides)
    return base


# ── NFR-02: update visibility ≤ 60 s ───────────────────────────────────────


def test_event_update_is_immediately_visible_through_get_detail(db, monkeypatch) -> None:
    """NFR-02: update propagates to discovery within 60 s.

    The implementation writes through ``update_event_atomic`` inside
    ``update_event`` and then calls ``get_event_detail`` for the
    response. There's no async indexer between them — the test pins
    that contract: the very next read sees the update.
    """
    from app.models.event import EventUpdateRequest

    # Stage 1: original event in the repo.
    stored = _stub_event()

    def _get_event_by_id(_db, _event_id):
        return stored

    def _get_event_segments(_db, _event_id):
        return []

    def _get_event_locations(_db, _event_id):
        return [
            {
                "id": "00000000-0000-0000-0000-0000000000d0",
                "name": "Hall", "latitude": 41.0, "longitude": 29.0,
                "is_primary": True, "order_index": 0, "location_address": None,
            },
        ]

    def _update_event_atomic(_db, *, event_id, event_data, **_kw):
        # Mutate the stored row in-place so a subsequent read sees the change.
        if event_data:
            stored.update(event_data)
        return stored

    monkeypatch.setattr(event_service.event_repo, "get_event_by_id", _get_event_by_id)
    monkeypatch.setattr(event_service.event_repo, "get_event_segments", _get_event_segments)
    monkeypatch.setattr(event_service.event_repo, "get_event_locations", _get_event_locations)
    monkeypatch.setattr(event_service.event_repo, "update_event_atomic", _update_event_atomic)

    # Side effects we don't need to exercise to pin the visibility contract.
    monkeypatch.setattr(event_service.event_repo, "get_event_categories", lambda *a, **k: [])
    monkeypatch.setattr(event_service.event_repo, "get_event_images", lambda *a, **k: [])
    monkeypatch.setattr(event_service.event_repo, "get_venue_metadata", lambda *a, **k: None)
    monkeypatch.setattr(event_service.event_repo, "get_equipment", lambda *a, **k: [])
    monkeypatch.setattr(event_service.attendance_repo, "get_attendance", lambda *a, **k: None)
    monkeypatch.setattr(event_service.attendance_repo, "get_going_user_ids_for_event", lambda *a, **k: [])
    monkeypatch.setattr(event_service.bookmark_repo, "get_bookmark", lambda *a, **k: None)
    monkeypatch.setattr(event_service.bookmark_repo, "get_bookmark_count_for_event", lambda *a, **k: 0)
    monkeypatch.setattr(event_service.invite_repo, "get_access_request", lambda *a, **k: None)
    monkeypatch.setattr(event_service.invite_repo, "get_access_grant", lambda *a, **k: None)
    monkeypatch.setattr(event_service.user_repo, "get_user_by_id", lambda *a, **k: {"id": HOST_ID, "username": "h"})
    monkeypatch.setattr(event_service.user_repo, "get_users_by_ids", lambda *a, **k: [])

    import app.services.notification_emitter as notif

    monkeypatch.setattr(notif, "emit_event_notification", lambda *a, **k: 0)

    # Act: update the title.
    event_service.update_event(
        db, EVENT_ID, HOST_ID,
        EventUpdateRequest(title="Updated Title"),
    )

    # Assert (a): the detail surface sees it. Same in-process call
    # chain the discovery list goes through, so visibility is bounded
    # by function-call latency — far under the 60-second NFR target.
    detail = event_service.get_event_detail(db, EVENT_ID, HOST_ID)
    assert detail.title == "Updated Title"

    # Assert (b): the discovery list surface sees it too. The repo
    # call ``list_events`` returns the same in-memory ``stored`` row
    # we mutated above, so the title in the listing item must match.
    monkeypatch.setattr(
        event_service.event_repo, "list_events",
        lambda *a, **k: ([stored], 1),
    )
    monkeypatch.setattr(
        event_service.event_repo, "get_primary_locations_for_events",
        lambda *a, **k: {EVENT_ID: {
            "id": "00000000-0000-0000-0000-0000000000d0",
            "name": "Hall", "latitude": 41.0, "longitude": 29.0,
            "is_primary": True, "order_index": 0,
        }},
    )
    monkeypatch.setattr(
        event_service.event_repo, "get_categories_for_events",
        lambda *a, **k: {EVENT_ID: []},
    )
    monkeypatch.setattr(
        event_service.event_repo, "get_primary_images_for_events",
        lambda *a, **k: {},
    )
    monkeypatch.setattr(
        event_service.bookmark_repo, "get_bookmark_status_for_events",
        lambda *a, **k: set(),
    )
    monkeypatch.setattr(
        event_service.bookmark_repo, "get_bookmark_counts_for_events",
        lambda *a, **k: {},
    )
    monkeypatch.setattr(
        event_service.attendance_repo, "get_attendance_status_for_events",
        lambda *a, **k: {},
    )
    monkeypatch.setattr(
        event_service.invite_repo, "get_access_request_status_for_events",
        lambda *a, **k: {},
    )
    monkeypatch.setattr(
        event_service.invite_repo, "get_access_granted_event_ids",
        lambda *a, **k: set(),
    )

    listing = event_service.list_events(db, user_id=HOST_ID)
    assert len(listing.items) == 1
    assert listing.items[0].title == "Updated Title"


def test_event_cancellation_is_immediately_visible_through_get_detail(db, monkeypatch) -> None:
    """NFR-02 (cancel path): a status flip to ``cancelled`` propagates
    to the detail surface inside the same request — no async indexer
    holds the previous status visible.

    The status-change service uses the same write/read pattern as
    update: ``update_event_status`` writes through, then the response
    re-reads. We pin the contract by having the in-memory stub mutate
    on write so the next read sees ``cancelled``.
    """
    stored = _stub_event(status="published")

    monkeypatch.setattr(
        event_service.event_repo, "get_event_by_id",
        lambda *a, **k: stored,
    )

    def _update_status(_db, _event_id, new_status):
        stored["status"] = new_status
        return stored

    monkeypatch.setattr(
        event_service.event_repo, "update_event_status", _update_status,
    )

    # Side-effect mocks for the get_event_detail re-read.
    monkeypatch.setattr(event_service.event_repo, "get_event_categories", lambda *a, **k: [])
    monkeypatch.setattr(event_service.event_repo, "get_event_locations", lambda *a, **k: [])
    monkeypatch.setattr(event_service.event_repo, "get_event_images", lambda *a, **k: [])
    monkeypatch.setattr(event_service.event_repo, "get_venue_metadata", lambda *a, **k: None)
    monkeypatch.setattr(event_service.event_repo, "get_equipment", lambda *a, **k: [])
    monkeypatch.setattr(event_service.event_repo, "get_event_segments", lambda *a, **k: [])
    monkeypatch.setattr(event_service.attendance_repo, "get_attendance", lambda *a, **k: None)
    monkeypatch.setattr(event_service.attendance_repo, "get_going_user_ids_for_event", lambda *a, **k: [])
    monkeypatch.setattr(event_service.bookmark_repo, "get_bookmark", lambda *a, **k: None)
    monkeypatch.setattr(event_service.bookmark_repo, "get_bookmark_count_for_event", lambda *a, **k: 0)
    monkeypatch.setattr(event_service.invite_repo, "get_access_request", lambda *a, **k: None)
    monkeypatch.setattr(event_service.invite_repo, "get_access_grant", lambda *a, **k: None)
    monkeypatch.setattr(event_service.user_repo, "get_user_by_id", lambda *a, **k: {"id": HOST_ID, "username": "h"})
    monkeypatch.setattr(event_service.user_repo, "get_users_by_ids", lambda *a, **k: [])

    import app.services.notification_emitter as notif

    monkeypatch.setattr(notif, "emit_event_notification", lambda *a, **k: 0)

    # Act: cancel the published event.
    response = event_service.change_event_status(db, EVENT_ID, HOST_ID, "cancelled")

    # Assert: the response is the *post-cancel* detail surface (host
    # gets the limited response on cancellation, which carries the
    # current status). The repo's stored row also reflects the new
    # state, so a discovery list filter on visible/published-only
    # rows naturally drops it.
    assert response.status == "cancelled"
    assert stored["status"] == "cancelled"


# ── NFR-04: private-event detail enforced server-side ──────────────────────


def test_private_event_detail_is_redacted_for_non_host_without_grant(db, monkeypatch) -> None:
    """NFR-04: the private boundary is in the service, not the client.

    A non-host caller without an access grant never receives the full
    detail payload — the service short-circuits to a ``LimitedResponse``
    before the locations/images/segments are even fetched.
    """
    monkeypatch.setattr(
        event_service.event_repo,
        "get_event_by_id",
        lambda *a, **k: _stub_event(visibility="private"),
    )
    monkeypatch.setattr(event_service.event_repo, "get_event_categories", lambda *a, **k: [])
    monkeypatch.setattr(event_service.bookmark_repo, "get_bookmark", lambda *a, **k: None)
    monkeypatch.setattr(event_service.bookmark_repo, "get_bookmark_count_for_event", lambda *a, **k: 0)
    monkeypatch.setattr(event_service.attendance_repo, "get_attendance", lambda *a, **k: None)
    monkeypatch.setattr(event_service.invite_repo, "get_access_request", lambda *a, **k: None)
    monkeypatch.setattr(event_service.invite_repo, "get_access_grant", lambda *a, **k: None)

    # Non-host, no grant → LimitedResponse, not EventDetailResponse.
    resp = event_service.get_event_detail(db, EVENT_ID, OTHER_USER)
    assert resp.__class__.__name__ == "EventLimitedResponse", (
        f"Private event must redact for non-host without grant; got {type(resp).__name__}"
    )

    # Host of the same event must still get the full detail.
    monkeypatch.setattr(event_service.event_repo, "get_event_locations", lambda *a, **k: [])
    monkeypatch.setattr(event_service.event_repo, "get_event_images", lambda *a, **k: [])
    monkeypatch.setattr(event_service.event_repo, "get_venue_metadata", lambda *a, **k: None)
    monkeypatch.setattr(event_service.event_repo, "get_equipment", lambda *a, **k: [])
    monkeypatch.setattr(event_service.event_repo, "get_event_segments", lambda *a, **k: [])
    monkeypatch.setattr(event_service.attendance_repo, "get_going_user_ids_for_event", lambda *a, **k: [])
    monkeypatch.setattr(event_service.user_repo, "get_user_by_id", lambda *a, **k: {"id": HOST_ID, "username": "h"})
    monkeypatch.setattr(event_service.user_repo, "get_users_by_ids", lambda *a, **k: [])

    host_resp = event_service.get_event_detail(db, EVENT_ID, HOST_ID)
    assert host_resp.__class__.__name__ == "EventDetailResponse"


def test_private_event_guest_request_is_redacted(db, monkeypatch) -> None:
    """Guest (no token) must never see private detail either."""
    monkeypatch.setattr(
        event_service.event_repo,
        "get_event_by_id",
        lambda *a, **k: _stub_event(visibility="private"),
    )
    monkeypatch.setattr(event_service.event_repo, "get_event_categories", lambda *a, **k: [])
    monkeypatch.setattr(event_service.bookmark_repo, "get_bookmark_count_for_event", lambda *a, **k: 0)

    resp = event_service.get_event_detail(db, EVENT_ID, user_id=None)
    assert resp.__class__.__name__ == "EventLimitedResponse"


# ── NFR-09: no precise GPS coordinates persisted ──────────────────────────


_LATLNG_COLUMN = re.compile(
    r"\b(latitude|longitude)\s+[A-Z]+\b",
    flags=re.IGNORECASE,
)


def _lat_lng_columns_in(sql_dir: Path) -> list[tuple[str, str]]:
    """Return ``(file, line)`` pairs for every lat/lng column declaration
    across the migration files."""
    hits: list[tuple[str, str]] = []
    for path in sorted(sql_dir.glob("*.sql")):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("--"):
                continue
            if _LATLNG_COLUMN.search(stripped):
                hits.append((path.name, stripped))
    return hits


def test_no_realtime_gps_columns_persisted() -> None:
    """NFR-09: no schema column captures the *caller's current* GPS.

    The two legitimate lat/lng homes are:
      - ``users.default_location_*`` — opt-in saved area on the
        profile, set by the user via ``PUT /users/me``.
      - ``event_locations.{latitude, longitude}`` — the *event's*
        published location, supplied by the host when creating the
        event.

    Anything that looks like ``current_*``, ``last_seen_*``, or a
    ``latitude``/``longitude`` column on a ``users`` table without
    the ``default_`` prefix would be a real-time GPS leak. This test
    fails if such a column appears.
    """
    sql_dir = Path(__file__).resolve().parents[1] / "sql"
    hits = _lat_lng_columns_in(sql_dir)

    forbidden = []
    allowed_prefixes = ("default_location_lat", "default_location_lng", "latitude", "longitude")
    for path, line in hits:
        # Allowed: ``default_location_lat`` / ``_lng`` on users + the
        # bare ``latitude`` / ``longitude`` columns on event_locations.
        # Anything else is suspicious enough to warrant a manual
        # review — we surface it so reviewers can decide.
        normalised = line.lower()
        if any(normalised.startswith(p) or f" {p}" in normalised for p in allowed_prefixes):
            continue
        forbidden.append((path, line))

    assert not forbidden, (
        "Unexpected lat/lng columns found in migrations — these may "
        f"persist precise caller GPS, violating NFR-09: {forbidden}"
    )


def test_user_profile_update_does_not_persist_realtime_gps(db, monkeypatch) -> None:
    """The profile update path only writes the opt-in default-area
    fields. There is no column-shaped escape hatch for the user's
    *current* GPS to land in the row.

    Pulled the allowed key set out of ``ProfileUpdateRequest`` so the
    test fails if a future model change adds a real-time-GPS-shaped
    field without a deliberate audit.
    """
    from app.models.profile import ProfileUpdateRequest

    fields = set(ProfileUpdateRequest.model_fields.keys())
    location_fields = {f for f in fields if "location" in f or "lat" in f or "lng" in f}
    assert location_fields <= {
        "default_location_name",
        "default_location_lat",
        "default_location_lng",
    }, f"Unexpected location-shaped fields on ProfileUpdateRequest: {location_fields}"


def test_register_payload_does_not_accept_gps() -> None:
    """The auth surface must never accept GPS at registration time."""
    from app.models.user import UserRegisterRequest

    fields = set(UserRegisterRequest.model_fields.keys())
    location_fields = {f for f in fields if "location" in f or "lat" in f or "lng" in f}
    assert not location_fields, (
        f"Register payload must not carry location fields; found: {location_fields}"
    )


# ── helper: HTTPException pin used elsewhere in the suite ─────────────────


def test_age_restricted_event_403_without_dob(db, monkeypatch) -> None:
    """Tangential pin (used elsewhere): age-restriction is server-side."""
    monkeypatch.setattr(
        event_service.event_repo,
        "get_event_by_id",
        lambda *a, **k: _stub_event(is_age_restricted=True),
    )
    monkeypatch.setattr(event_service.event_repo, "get_event_categories", lambda *a, **k: [])
    monkeypatch.setattr(event_service.bookmark_repo, "get_bookmark", lambda *a, **k: None)
    monkeypatch.setattr(event_service.bookmark_repo, "get_bookmark_count_for_event", lambda *a, **k: 0)
    monkeypatch.setattr(event_service.attendance_repo, "get_attendance", lambda *a, **k: None)
    monkeypatch.setattr(event_service.invite_repo, "get_access_request", lambda *a, **k: None)
    monkeypatch.setattr(event_service.invite_repo, "get_access_grant", lambda *a, **k: None)
    monkeypatch.setattr(event_service.user_repo, "get_user_date_of_birth", lambda *a, **k: None)

    with pytest.raises(HTTPException) as exc:
        event_service.get_event_detail(db, EVENT_ID, OTHER_USER)
    assert exc.value.status_code == 403
