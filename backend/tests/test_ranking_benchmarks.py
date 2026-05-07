"""Microbenchmarks for the in-memory ranking paths.

`list_events` (sort=distance/category) and `get_similar_events` both
materialise the full filtered set and rank in Python — the database
can't order by the joined-aggregate column in a single round-trip.
The 10k-event NFR target sets the budget, so a regression that
slows the in-memory sort by an order of magnitude needs to fail CI
loudly. pytest-benchmark stores per-test timing so a regression
shows up in the diff against ``.benchmarks/Linux-CPython-3.12/``.

To regenerate the baseline after a deliberate algorithm change:

    pytest tests/test_ranking_benchmarks.py --benchmark-save=baseline

To compare a new run against it:

    pytest tests/test_ranking_benchmarks.py --benchmark-compare=baseline
"""
from __future__ import annotations

import math
import random
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.services import event as event_service

# Synthetic dataset size — generous enough that O(N log N) is visible
# but small enough that the test stays under the per-shard budget.
_N = 5_000


@pytest.fixture
def db() -> MagicMock:
    return MagicMock(name="supabase_client")


def _uuid_from_int(seed: int) -> str:
    """Deterministic UUID from a seed int — formed as 32 hex chars in groups."""
    h = f"{seed:032x}"
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


@pytest.fixture(scope="session")
def synthetic_events() -> list[dict[str, Any]]:
    """A deterministic set of synthetic events with valid UUIDs.

    Seeded RNG so runs are reproducible across CI hosts; the dataset
    only needs to be _representative_, not realistic.
    """
    rng = random.Random(0xC0FFEE)
    rows: list[dict[str, Any]] = []
    for i in range(_N):
        rows.append(
            {
                "id": _uuid_from_int(i),
                "host_id": _uuid_from_int(rng.randint(0, 0xFFFFFFFF)),
                "title": f"Event {i}",
                "description": "synthetic",
                "start_datetime": "2030-06-01T10:00:00+00:00",
                "end_datetime": "2030-06-01T12:00:00+00:00",
                "visibility": "public",
                "is_age_restricted": False,
                "attendee_limit": None,
                "attendee_count": rng.randint(0, 200),
                "status": "published",
                "created_at": "2030-05-01T00:00:00+00:00",
                "updated_at": "2030-05-15T00:00:00+00:00",
            },
        )
    return rows


@pytest.fixture(scope="session")
def synthetic_locations(synthetic_events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """A primary-location entry per event, points scattered around (41, 29)."""
    rng = random.Random(0xBADCAFE)
    out: dict[str, dict[str, Any]] = {}
    for i, event in enumerate(synthetic_events):
        out[event["id"]] = {
            "id": _uuid_from_int(0x10_00_00_00 + i),
            "name": "loc",
            "latitude": 41.0 + rng.uniform(-0.5, 0.5),
            "longitude": 29.0 + rng.uniform(-0.5, 0.5),
            "is_primary": True,
            "order_index": 0,
        }
    return out


@pytest.fixture
def synthetic_categories(
    synthetic_events: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """A single random category per event drawn from a small pool."""
    rng = random.Random(0xFEEDFACE)
    pool = [
        {
            "id": _uuid_from_int(0x20_00_00_00 + i),
            "name": f"Cat {i}",
            "is_predefined": True,
            "is_approved": True,
        }
        for i in range(8)
    ]
    return {e["id"]: [rng.choice(pool)] for e in synthetic_events}


def _all_repos(events_repo: MagicMock) -> dict[str, MagicMock]:
    users = MagicMock(name="user_repo")
    users.get_user_default_area.return_value = (None, None)
    bookmarks = MagicMock(name="bookmark_repo")
    bookmarks.get_bookmark_status_for_events.return_value = set()
    bookmarks.get_bookmark_counts_for_events.return_value = {}
    attendances = MagicMock(name="attendance_repo")
    attendances.get_attendance_status_for_events.return_value = {}
    attendances.get_attended_ended_event_categories.return_value = set()
    invites = MagicMock(name="invite_repo")
    invites.get_access_request_status_for_events.return_value = {}
    invites.get_access_granted_event_ids.return_value = set()
    return {
        "events": events_repo,
        "users": users,
        "bookmarks": bookmarks,
        "attendances": attendances,
        "invites": invites,
    }


def test_list_events_distance_sort_5k(
    benchmark,
    db: MagicMock,
    synthetic_events: list[dict[str, Any]],
    synthetic_locations: dict[str, dict[str, Any]],
    synthetic_categories: dict[str, list[dict[str, Any]]],
) -> None:
    """Distance-sort path on 5k events — covers the in-memory haversine rank."""
    events_repo = MagicMock(name="event_repo")
    events_repo.list_events.return_value = (synthetic_events, _N)
    events_repo.get_primary_locations_for_events.return_value = synthetic_locations
    events_repo.get_categories_for_events.return_value = synthetic_categories
    events_repo.get_primary_images_for_events.return_value = {}

    def _run() -> None:
        event_service.list_events(
            db,
            near_lat=41.0,
            near_lng=29.0,
            sort="distance",
            page=1,
            page_size=20,
            **_all_repos(events_repo),
        )

    benchmark(_run)


def test_get_similar_events_30_candidates(
    benchmark,
    db: MagicMock,
    synthetic_events: list[dict[str, Any]],
    synthetic_locations: dict[str, dict[str, Any]],
    synthetic_categories: dict[str, list[dict[str, Any]]],
) -> None:
    """Score path on the standard 30-candidate window."""
    events_repo = MagicMock(name="event_repo")
    source = synthetic_events[0]
    candidates = synthetic_events[:30]

    events_repo.get_event_by_id.return_value = source
    events_repo.get_event_categories.return_value = synthetic_categories[source["id"]]
    events_repo.get_primary_locations_for_events.return_value = {
        cid: synthetic_locations[cid] for cid in [source["id"]] + [c["id"] for c in candidates]
    }
    events_repo.get_similar_candidates.return_value = candidates
    events_repo.get_categories_for_events.return_value = {
        c["id"]: synthetic_categories[c["id"]] for c in candidates
    }
    events_repo.get_primary_images_for_events.return_value = {}

    bookmarks = MagicMock(name="bookmark_repo")
    bookmarks.get_bookmark_counts_for_events.return_value = {}
    bookmarks.get_bookmark_status_for_events.return_value = set()
    invites = MagicMock(name="invite_repo")
    invites.get_access_request_status_for_events.return_value = {}
    invites.get_access_granted_event_ids.return_value = set()

    def _run() -> None:
        event_service.get_similar_events(
            db, source["id"],
            user_id=None, limit=5,
            events=events_repo, bookmarks=bookmarks, invites=invites,
        )

    benchmark(_run)


def test_haversine_pure_function() -> None:
    """The pure haversine helper itself — sub-microsecond per call.

    Anchors the unit so the benchmarks above can be diffed against a
    fixed reference point. Not parameterised by `benchmark` because
    benchmarking a single-arithmetic function is noisy below CPU
    counter resolution; this just pins the math is correct.
    """
    # Istanbul → Tokyo, ~8945 km (great-circle, mean Earth radius 6371 km).
    distance = event_service._haversine_km(41.0, 29.0, 35.68, 139.69)
    assert math.isclose(distance, 8944.7, abs_tol=5)
