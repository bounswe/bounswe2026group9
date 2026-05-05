"""Unit tests for the similar events service function.

All DB calls are mocked — no network/Supabase required.
"""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.event import get_similar_events

# Stable category UUIDs shared across tests
CAT1 = str(uuid4())
CAT2 = str(uuid4())
CAT3 = str(uuid4())


def _cat_row(cid: str) -> dict:
    return {"id": cid, "name": f"cat-{cid[:8]}", "is_predefined": True, "is_approved": True}


def _event(
    event_id: str | None = None,
    host_id: str | None = None,
    cat_ids: list[str] | None = None,
    lat: float | None = None,
    lng: float | None = None,
    hours_from_now: int = 24,
) -> dict:
    now = datetime.now(UTC)
    return {
        "id": event_id or str(uuid4()),
        "host_id": host_id or str(uuid4()),
        "title": "Event",
        "description": "desc",
        "start_datetime": (now + timedelta(hours=hours_from_now)).isoformat(),
        "end_datetime": (now + timedelta(hours=hours_from_now + 2)).isoformat(),
        "visibility": "public",
        "is_age_restricted": False,
        "attendee_limit": None,
        "attendee_count": 0,
        "status": "published",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "_cat_ids": cat_ids or [],
        "_lat": lat,
        "_lng": lng,
    }


@contextmanager
def _mock_db_for(source: dict, candidates: list[dict]):
    """Build a mock Supabase Client whose queries return scripted data."""
    db = MagicMock()

    source_cat_rows = [_cat_row(cid) for cid in source["_cat_ids"]]
    source_loc_rows = (
        [{"latitude": source["_lat"], "longitude": source["_lng"]}]
        if source["_lat"] is not None else []
    )

    cats_by_event: dict[str, list[dict]] = {}
    locs_by_event: dict[str, dict] = {}
    for cand in candidates:
        cats_by_event[cand["id"]] = [_cat_row(cid) for cid in cand["_cat_ids"]]
        if cand["_lat"] is not None:
            locs_by_event[cand["id"]] = {
                "latitude": cand["_lat"],
                "longitude": cand["_lng"],
                "event_id": cand["id"],
                "id": str(uuid4()),
                "name": "Location",
                "is_primary": True,
                "order_index": 0,
            }

    clean_candidates = [{k: v for k, v in c.items() if not k.startswith("_")} for c in candidates]
    clean_source = {k: v for k, v in source.items() if not k.startswith("_")}

    table_mock = MagicMock()
    table_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = source_loc_rows
    db.table.return_value = table_mock

    with (
        patch("app.services.event.event_repo.get_event_by_id", return_value=clean_source),
        patch("app.services.event.event_repo.get_event_categories", return_value=source_cat_rows),
        patch("app.services.event.event_repo.get_similar_candidates", return_value=clean_candidates),
        patch("app.services.event.event_repo.get_categories_for_events", return_value=cats_by_event),
        patch("app.services.event.event_repo.get_primary_locations_for_events", return_value=locs_by_event),
        patch("app.services.event.event_repo.get_primary_images_for_events", return_value={}),
        patch("app.services.event.bookmark_repo.get_bookmark_counts_for_events", return_value={}),
        patch("app.services.event.bookmark_repo.get_bookmark_status_for_events", return_value=set()),
        # Discovery-parity: similar events surfaces private listings with a
        # teaser; the access-state batch lookups must be mocked even when
        # tests don't pass user_id (the service only calls them when user_id
        # is set, so default empties keep guest-flow tests intact).
        patch("app.services.event.invite_repo.get_access_request_status_for_events", return_value={}),
        patch("app.services.event.invite_repo.get_access_granted_event_ids", return_value=set()),
    ):
        yield db


class TestGetSimilarEvents:
    def test_raises_404_when_source_not_found(self):
        db = MagicMock()
        with patch("app.services.event.event_repo.get_event_by_id", return_value=None):
            with pytest.raises(HTTPException) as exc:
                get_similar_events(db, "nonexistent-id")
        assert exc.value.status_code == 404

    def test_returns_empty_when_no_candidates(self):
        source = _event(cat_ids=[CAT1])
        with _mock_db_for(source, []) as db:
            result = get_similar_events(db, source["id"])
        assert result == []

    def test_category_overlap_drives_ranking(self):
        source_id = str(uuid4())
        source = _event(event_id=source_id, cat_ids=[CAT1, CAT2, CAT3])

        high_overlap = _event(event_id=str(uuid4()), cat_ids=[CAT1, CAT2, CAT3])
        low_overlap = _event(event_id=str(uuid4()), cat_ids=[CAT1])

        with _mock_db_for(source, [low_overlap, high_overlap]) as db:
            result = get_similar_events(db, source_id)

        assert len(result) == 2
        assert str(result[0].id) == high_overlap["id"]

    def test_host_match_contributes_to_score(self):
        host = str(uuid4())
        source = _event(host_id=host, cat_ids=[CAT1])

        same_host_no_cats = _event(host_id=host, cat_ids=[])       # score = 2
        diff_host_one_cat = _event(host_id=str(uuid4()), cat_ids=[CAT1])  # score = 3

        with _mock_db_for(source, [same_host_no_cats, diff_host_one_cat]) as db:
            result = get_similar_events(db, source["id"])

        # diff_host_one_cat (score=3) should rank above same_host_no_cats (score=2)
        assert str(result[0].id) == diff_host_one_cat["id"]

    def test_proximity_bonus_within_50km(self):
        source = _event(cat_ids=[], lat=41.0, lng=28.9)  # Istanbul

        nearby = _event(cat_ids=[], lat=41.05, lng=28.95)  # ~6 km → bonus (+1)
        far_away = _event(cat_ids=[], lat=50.0, lng=14.0)  # Prague → no bonus

        with _mock_db_for(source, [far_away, nearby]) as db:
            result = get_similar_events(db, source["id"])

        assert str(result[0].id) == nearby["id"]

    def test_limits_results_to_five(self):
        source = _event(cat_ids=[CAT1])
        candidates = [_event(cat_ids=[CAT1]) for _ in range(10)]

        with _mock_db_for(source, candidates) as db:
            result = get_similar_events(db, source["id"])

        assert len(result) <= 5

    def test_guest_has_no_bookmark_state(self):
        source = _event(cat_ids=[CAT1])
        cand = _event(cat_ids=[CAT1])

        with _mock_db_for(source, [cand]) as db:
            result = get_similar_events(db, source["id"], user_id=None)

        assert result[0].is_bookmarked is None

    def test_authenticated_user_gets_bookmark_state(self):
        source = _event(cat_ids=[CAT1])
        cand = _event(cat_ids=[CAT1])
        user_id = str(uuid4())

        with _mock_db_for(source, [cand]) as db:
            with patch(
                "app.services.event.bookmark_repo.get_bookmark_status_for_events",
                return_value={cand["id"]},
            ):
                result = get_similar_events(db, source["id"], user_id=user_id)

        assert result[0].is_bookmarked is True

    def test_private_candidate_appears_with_redacted_description(self):
        # Discovery parity: private events show up in the list with a teaser
        # (no description) so the viewer can tap through and request access,
        # rather than being filtered out entirely.
        source = _event(cat_ids=[CAT1])
        private_cand = _event(cat_ids=[CAT1])
        private_cand["visibility"] = "private"
        private_cand["description"] = "secret guest list"
        user_id = str(uuid4())

        with _mock_db_for(source, [private_cand]) as db:
            result = get_similar_events(db, source["id"], user_id=user_id)

        # Private candidate is surfaced (not filtered out)
        assert len(result) == 1
        assert str(result[0].id) == private_cand["id"]
        # ...but description is redacted
        assert result[0].description is None
        # visibility flag is preserved so the client can render a "private" badge
        assert result[0].visibility == "private"

    def test_private_candidate_visible_to_guest_with_teaser(self):
        # Same redaction applies for unauthenticated viewers.
        source = _event(cat_ids=[CAT1])
        private_cand = _event(cat_ids=[CAT1])
        private_cand["visibility"] = "private"
        private_cand["description"] = "secret guest list"

        with _mock_db_for(source, [private_cand]) as db:
            result = get_similar_events(db, source["id"], user_id=None)

        assert len(result) == 1
        assert result[0].description is None
        # Guests have no notion of access state — `has_access` and
        # `access_request_status` remain None for them.
        assert result[0].has_access is None
        assert result[0].access_request_status is None

    def test_authed_user_with_access_grant_sees_has_access_true(self):
        # An authenticated user with a granted access record on a private
        # candidate should see has_access=True so the UI can route them
        # straight into the event without prompting a request.
        source = _event(cat_ids=[CAT1])
        private_cand = _event(cat_ids=[CAT1])
        private_cand["visibility"] = "private"
        user_id = str(uuid4())

        with _mock_db_for(source, [private_cand]) as db:
            with patch(
                "app.services.event.invite_repo.get_access_granted_event_ids",
                return_value={private_cand["id"]},
            ):
                result = get_similar_events(db, source["id"], user_id=user_id)

        assert result[0].has_access is True
