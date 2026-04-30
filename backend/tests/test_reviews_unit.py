"""Phase 1 unit tests for issue #235 (free-text reviews on ratings).

Covers Pydantic validation, repository read/write contracts, and the
whitespace-normalisation logic in the service layer. All DB calls are
mocked — these run in the `unit-fast` CI shard via `tests/test_*_unit.py`.

Integration tests (real Supabase, eligibility, end-to-end POST/GET) are
covered separately in tests/test_users.py.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.rating import (
    RatingRequest,
    RatingResponse,
    ReviewListItemResponse,
    ReviewListResponse,
)
from app.repositories import rating as rating_repo
from app.services.rating import _normalise_review_text


# Override the autouse cleanup_test_users fixture from conftest.py: these
# tests never touch real Supabase (db is mocked everywhere), so the
# session-scoped `db` dependency would otherwise force a connection on
# every teardown — fragile when run locally without DB env, and pointless
# even in CI. Replace with a no-op so the unit shard is truly DB-free.
@pytest.fixture(autouse=True)
def cleanup_test_users():
    yield


# --- RatingRequest schema --------------------------------------------------

class TestRatingRequestSchema:
    def test_score_only_payload_back_compat(self):
        # Existing clients that don't know about review_text must keep working.
        body = RatingRequest(score=Decimal("4.5"))
        assert body.review_text is None

    def test_score_with_text(self):
        body = RatingRequest(score=Decimal("5.0"), review_text="Great host!")
        assert body.review_text == "Great host!"

    def test_text_at_max_length_accepted(self):
        body = RatingRequest(score=Decimal("4.0"), review_text="x" * 1000)
        assert len(body.review_text) == 1000

    def test_text_over_max_length_rejected(self):
        with pytest.raises(ValidationError):
            RatingRequest(score=Decimal("4.0"), review_text="x" * 1001)

    def test_review_text_can_be_explicit_null(self):
        body = RatingRequest(score=Decimal("4.0"), review_text=None)
        assert body.review_text is None

    def test_score_below_floor_rejected(self):
        with pytest.raises(ValidationError):
            RatingRequest(score=Decimal("0.5"))

    def test_score_above_ceiling_rejected(self):
        with pytest.raises(ValidationError):
            RatingRequest(score=Decimal("5.5"))


# --- Response shapes -------------------------------------------------------

class TestRatingResponseShape:
    def test_round_trips_with_text(self):
        rid = uuid4()
        rater = uuid4()
        host = uuid4()
        now = datetime.now(UTC)
        resp = RatingResponse(
            id=rid, rater_id=rater, host_id=host,
            score=Decimal("4.5"), review_text="Walk was excellent",
            created_at=now,
        )
        assert resp.review_text == "Walk was excellent"

    def test_review_text_optional(self):
        resp = RatingResponse(
            id=uuid4(), rater_id=uuid4(), host_id=uuid4(),
            score=Decimal("3.5"), created_at=datetime.now(UTC),
        )
        assert resp.review_text is None


class TestReviewListResponseShape:
    def test_empty_list(self):
        resp = ReviewListResponse(items=[], total=0, page=1, page_size=20, total_pages=0)
        assert resp.items == []

    def test_item_with_username_and_null_text(self):
        item = ReviewListItemResponse(
            id=uuid4(),
            rater_id=uuid4(),
            rater_username="alice",
            score=Decimal("4.0"),
            review_text=None,
            created_at=datetime.now(UTC),
        )
        # Star-only reviews surface in the list with review_text=None
        # (locked decision #1).
        assert item.review_text is None
        assert item.rater_username == "alice"


# --- Whitespace normalisation (locked decision #4) -------------------------

class TestNormaliseReviewText:
    def test_none_passthrough(self):
        assert _normalise_review_text(None) is None

    def test_empty_string_becomes_none(self):
        assert _normalise_review_text("") is None

    def test_whitespace_only_becomes_none(self):
        assert _normalise_review_text("   \t\n  ") is None

    def test_strips_surrounding_whitespace(self):
        assert _normalise_review_text("  good walk  ") == "good walk"

    def test_preserves_inner_whitespace(self):
        assert _normalise_review_text("very  helpful   leader") == "very  helpful   leader"

    def test_unicode_text_preserved(self):
        assert _normalise_review_text("çok iyi 👍") == "çok iyi 👍"


# --- Repository: list_reviews_for_host -------------------------------------

class TestListReviewsForHost:
    def _db_with_count_and_rows(self, count, rows):
        db = MagicMock()

        # Two distinct chains: one for count, one for paged data. We tell
        # them apart by checking which `select` overload fires.
        def select_side_effect(*args, **kwargs):
            chain = MagicMock()
            if "count" in kwargs:
                # count path: db.table(..).select("id", count="exact").eq(..).execute()
                chain.eq.return_value.execute.return_value = MagicMock(
                    count=count, data=[{"id": "x"}] * count,
                )
            else:
                # data path: select(_RATING_COLS).eq.order.order.range.execute
                page = chain.eq.return_value.order.return_value.order.return_value.range.return_value
                page.execute.return_value.data = rows
            return chain

        db.table.return_value.select.side_effect = select_side_effect
        return db

    def test_zero_total_returns_empty(self):
        db = self._db_with_count_and_rows(0, [])
        rows, total = rating_repo.list_reviews_for_host(db, "host-id", page=1, page_size=20)
        assert rows == []
        assert total == 0

    def test_offset_past_end_returns_empty_list_but_keeps_total(self):
        db = self._db_with_count_and_rows(2, [])
        rows, total = rating_repo.list_reviews_for_host(db, "host-id", page=99, page_size=20)
        assert rows == []
        assert total == 2

    def test_returns_rows_and_total(self):
        sample = [
            {"id": str(uuid4()), "rater_id": str(uuid4()), "host_id": "h",
             "score": 5.0, "review_text": "a", "created_at": "2030-01-02T00:00:00+00:00"},
            {"id": str(uuid4()), "rater_id": str(uuid4()), "host_id": "h",
             "score": 4.0, "review_text": None, "created_at": "2030-01-01T00:00:00+00:00"},
        ]
        db = self._db_with_count_and_rows(2, sample)
        rows, total = rating_repo.list_reviews_for_host(db, "h", page=1, page_size=20)
        assert total == 2
        assert rows == sample

    def test_query_parameters_are_passed_in_order(self):
        # Pin: filter first by host_id, order by created_at desc then id desc.
        db = MagicMock()
        sel = db.table.return_value.select
        # Make both invocations return the same chain so we can observe calls.
        chain = sel.return_value
        chain.eq.return_value = chain
        chain.execute.return_value = MagicMock(count=1, data=[{"id": "x"}])
        chain.order.return_value = chain
        chain.range.return_value = chain

        rating_repo.list_reviews_for_host(db, "host-id", page=1, page_size=10)

        # Check eq("host_id", ...) was called on both queries.
        eq_calls = [c.args for c in chain.eq.call_args_list]
        assert ("host_id", "host-id") in eq_calls
        # Check the ordering on the data query: created_at desc, id desc.
        order_calls = [(c.args, c.kwargs) for c in chain.order.call_args_list]
        assert (("created_at",), {"desc": True}) in order_calls
        assert (("id",), {"desc": True}) in order_calls


# --- Repository: upsert_rating now carries review_text ---------------------

class TestUpsertRatingCarriesReviewText:
    def test_review_text_in_payload(self):
        db = MagicMock()
        db.table.return_value.upsert.return_value.execute.return_value.data = [
            {"id": str(uuid4()), "rater_id": "r", "host_id": "h",
             "score": 4.0, "review_text": "Nice!", "created_at": "2030-01-01T00:00:00+00:00"},
        ]
        rating_repo.upsert_rating(db, {
            "rater_id": "r", "host_id": "h", "score": 4.0, "review_text": "Nice!",
        })
        upsert_args, upsert_kwargs = db.table.return_value.upsert.call_args
        assert upsert_args[0] == {
            "rater_id": "r", "host_id": "h", "score": 4.0, "review_text": "Nice!",
        }
        # on_conflict must remain the composite unique key
        assert upsert_kwargs["on_conflict"] == "rater_id,host_id"

    def test_review_text_null_in_payload(self):
        db = MagicMock()
        db.table.return_value.upsert.return_value.execute.return_value.data = [
            {"id": str(uuid4()), "rater_id": "r", "host_id": "h",
             "score": 5.0, "review_text": None, "created_at": "2030-01-01T00:00:00+00:00"},
        ]
        rating_repo.upsert_rating(db, {
            "rater_id": "r", "host_id": "h", "score": 5.0, "review_text": None,
        })
        upsert_args, _ = db.table.return_value.upsert.call_args
        assert upsert_args[0]["review_text"] is None


# --- Service: rate_host trims and forwards review_text correctly -----------

class TestRateHostService:
    """Pin rate_host's interaction with the repo layer.

    All eligibility-chain dependencies are mocked so we focus on the new
    review_text wiring: the upsert payload must contain trimmed text (or
    None), and the response must surface the same text.
    """

    def _setup(self, monkeypatch, *, captured_payload):
        from app.repositories import attendance as attendance_repo
        from app.repositories import profile as profile_repo
        from app.repositories import user as user_repo
        from app.services import rating as rating_svc

        monkeypatch.setattr(
            user_repo, "get_user_by_id",
            lambda _db, _uid: {"id": _uid, "username": "host"},
        )
        monkeypatch.setattr(
            profile_repo, "get_hosted_events", lambda _db, _hid: [{"id": "e1"}],
        )
        monkeypatch.setattr(
            attendance_repo, "has_attended_ended_event_by_host",
            lambda _db, _rid, _hid: True,
        )

        def fake_upsert(_db, payload):
            captured_payload.append(payload)
            return {
                "id": str(uuid4()),
                "rater_id": payload["rater_id"],
                "host_id": payload["host_id"],
                "score": payload["score"],
                "review_text": payload["review_text"],
                "created_at": "2030-01-01T00:00:00+00:00",
            }

        monkeypatch.setattr(rating_repo, "upsert_rating", fake_upsert)
        return rating_svc

    def test_trims_surrounding_whitespace_and_forwards_text(self, monkeypatch):
        captured: list[dict] = []
        svc = self._setup(monkeypatch, captured_payload=captured)

        # RatingResponse validates rater_id/host_id as UUIDs, so the test
        # must pass real UUID strings end-to-end.
        rater_id = str(uuid4())
        host_id = str(uuid4())
        resp = svc.rate_host(
            MagicMock(), rater_id=rater_id, host_id=host_id,
            score=Decimal("4.5"), review_text="  Walk was excellent  ",
        )

        assert captured[0]["review_text"] == "Walk was excellent"
        assert resp.review_text == "Walk was excellent"
        assert resp.score == Decimal("4.5")

    def test_whitespace_only_text_normalised_to_null_in_repo_call(self, monkeypatch):
        captured: list[dict] = []
        svc = self._setup(monkeypatch, captured_payload=captured)

        rater_id = str(uuid4())
        host_id = str(uuid4())
        resp = svc.rate_host(
            MagicMock(), rater_id=rater_id, host_id=host_id,
            score=Decimal("3.0"), review_text="   \n\t  ",
        )

        assert captured[0]["review_text"] is None
        assert resp.review_text is None

    def test_missing_review_text_defaults_to_null(self, monkeypatch):
        captured: list[dict] = []
        svc = self._setup(monkeypatch, captured_payload=captured)

        rater_id = str(uuid4())
        host_id = str(uuid4())
        resp = svc.rate_host(
            MagicMock(), rater_id=rater_id, host_id=host_id, score=Decimal("5.0"),
        )

        assert captured[0]["review_text"] is None
        assert resp.review_text is None

    def test_self_rating_blocked_before_repo_call(self, monkeypatch):
        from fastapi import HTTPException

        from app.services import rating as rating_svc
        captured: list[dict] = []
        # Even with eligibility chain mocked, rater_id == host_id must short-circuit
        # (raises before the RatingResponse build, so any string id is fine here).
        monkeypatch.setattr(rating_repo, "upsert_rating",
                            lambda _db, p: captured.append(p) or {"id": "x"})

        same_id = str(uuid4())
        with pytest.raises(HTTPException) as exc:
            rating_svc.rate_host(
                MagicMock(), rater_id=same_id, host_id=same_id,
                score=Decimal("4.0"), review_text="hi",
            )
        assert exc.value.status_code == 400
        assert captured == []  # never reached the repo


# --- Service: list_reviews paginates + maps usernames ----------------------

class TestListReviewsService:
    def _patch_chain(self, monkeypatch, *, host_exists=True, rows=None, total=0):
        from app.repositories import user as user_repo
        from app.services import rating as rating_svc

        if host_exists:
            monkeypatch.setattr(
                user_repo, "get_user_by_id",
                lambda _db, _uid: {"id": _uid, "username": "host"},
            )
        else:
            monkeypatch.setattr(user_repo, "get_user_by_id", lambda _db, _uid: None)

        monkeypatch.setattr(
            rating_repo, "list_reviews_for_host",
            lambda _db, _hid, *, page, page_size: (rows or [], total),
        )

        # Maps each rater_id to "user-<short>" for stable assertions
        def fake_users_by_ids(_db, ids):
            return [{"id": uid, "username": f"user-{uid[:4]}"} for uid in ids]

        monkeypatch.setattr(user_repo, "get_users_by_ids", fake_users_by_ids)
        return rating_svc

    def test_unknown_host_returns_404(self, monkeypatch):
        from fastapi import HTTPException
        svc = self._patch_chain(monkeypatch, host_exists=False)
        with pytest.raises(HTTPException) as exc:
            svc.list_reviews(MagicMock(), "missing-id")
        assert exc.value.status_code == 404

    def test_known_host_no_ratings_returns_200_empty(self, monkeypatch):
        # Locked decision #3: existing host with no ratings → 200 + empty items
        svc = self._patch_chain(monkeypatch, host_exists=True, rows=[], total=0)
        resp = svc.list_reviews(MagicMock(), "host-id", page=1, page_size=20)
        assert resp.total == 0
        assert resp.items == []
        assert resp.total_pages == 0

    def test_pagination_math(self, monkeypatch):
        # 3 reviews, page_size=2 → total_pages=2
        rid_a, rid_b = str(uuid4()), str(uuid4())
        rows = [
            {"id": str(uuid4()), "rater_id": rid_a, "host_id": "h", "score": 5.0,
             "review_text": "a", "created_at": "2030-01-02T00:00:00+00:00"},
            {"id": str(uuid4()), "rater_id": rid_b, "host_id": "h", "score": 4.0,
             "review_text": None, "created_at": "2030-01-01T00:00:00+00:00"},
        ]
        svc = self._patch_chain(monkeypatch, host_exists=True, rows=rows, total=3)
        resp = svc.list_reviews(MagicMock(), "h", page=1, page_size=2)
        assert resp.total == 3
        assert resp.page == 1
        assert resp.page_size == 2
        assert resp.total_pages == 2
        assert len(resp.items) == 2

    def test_username_mapping_is_correct(self, monkeypatch):
        rid_a = str(uuid4())
        rid_b = str(uuid4())
        rows = [
            {"id": str(uuid4()), "rater_id": rid_a, "host_id": "h", "score": 5.0,
             "review_text": "great", "created_at": "2030-01-02T00:00:00+00:00"},
            {"id": str(uuid4()), "rater_id": rid_b, "host_id": "h", "score": 4.0,
             "review_text": None, "created_at": "2030-01-01T00:00:00+00:00"},
        ]
        svc = self._patch_chain(monkeypatch, host_exists=True, rows=rows, total=2)
        resp = svc.list_reviews(MagicMock(), "h")

        by_rater = {item.rater_id: item for item in resp.items}
        # Locked decision #1: star-only ratings show up with review_text=None
        assert by_rater[uuid4_to_uuid(rid_b)].review_text is None
        assert by_rater[uuid4_to_uuid(rid_a)].review_text == "great"
        # Username mapped from get_users_by_ids stub
        assert resp.items[0].rater_username == f"user-{rows[0]['rater_id'][:4]}"
        assert resp.items[1].rater_username == f"user-{rows[1]['rater_id'][:4]}"

    def test_unknown_rater_falls_back_to_unknown_username(self, monkeypatch):
        # If user lookup returns no row for a rater_id, surface "unknown"
        # rather than crashing. Defensive — a CASCADE-deleted user could
        # leave an orphan rating in flight.
        from app.repositories import user as user_repo
        from app.services import rating as rating_svc

        monkeypatch.setattr(
            user_repo, "get_user_by_id",
            lambda _db, _uid: {"id": _uid, "username": "host"},
        )
        rid_orphan = str(uuid4())
        rows = [{
            "id": str(uuid4()), "rater_id": rid_orphan, "host_id": "h",
            "score": 4.0, "review_text": "hi",
            "created_at": "2030-01-01T00:00:00+00:00",
        }]
        monkeypatch.setattr(
            rating_repo, "list_reviews_for_host",
            lambda _db, _hid, *, page, page_size: (rows, 1),
        )
        # No matching user returned
        monkeypatch.setattr(user_repo, "get_users_by_ids", lambda _db, _ids: [])

        resp = rating_svc.list_reviews(MagicMock(), "h")
        assert resp.items[0].rater_username == "unknown"


def uuid4_to_uuid(s: str):
    """Convenience: ReviewListItemResponse.rater_id is UUID; raw rows hold str."""
    from uuid import UUID
    return UUID(s)
