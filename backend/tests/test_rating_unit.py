"""Unit tests for `services.rating` — exercises the keyword-DI seam."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.services import rating as rating_service

HOST_ID = "00000000-0000-0000-0000-000000000030"
RATER_ID = "00000000-0000-0000-0000-000000000031"
RATING_ID = "00000000-0000-0000-0000-000000000032"
OTHER_RATER_ID = "00000000-0000-0000-0000-000000000033"


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


@pytest.fixture
def repos():
    """Return the four DI handles every rating-service call needs."""
    users = MagicMock()
    profiles = MagicMock()
    attendances = MagicMock()
    ratings = MagicMock()
    # Sensible defaults — happy path; tests override the bits they care about.
    users.get_user_by_id.return_value = {"id": HOST_ID, "username": "host"}
    profiles.get_hosted_events.return_value = [{"id": "evt-1"}]
    attendances.has_attended_ended_event_by_host.return_value = True
    ratings.upsert_rating.return_value = {
        "id": RATING_ID,
        "rater_id": RATER_ID,
        "host_id": HOST_ID,
        "score": 4.5,
        "review_text": None,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    return users, profiles, attendances, ratings


# ── rate_host ───────────────────────────────────────────────────────────────


class TestRateHost:
    def test_400_when_rater_equals_host(self, db, repos):
        users, profiles, attendances, ratings = repos
        with pytest.raises(HTTPException) as exc:
            rating_service.rate_host(
                db, HOST_ID, HOST_ID, Decimal("4.0"),
                users=users, profiles=profiles, attendances=attendances, ratings=ratings,
            )
        assert exc.value.status_code == 400
        # Bail before any repo write.
        ratings.upsert_rating.assert_not_called()

    def test_404_when_host_missing(self, db, repos):
        users, profiles, attendances, ratings = repos
        users.get_user_by_id.return_value = None
        with pytest.raises(HTTPException) as exc:
            rating_service.rate_host(
                db, RATER_ID, HOST_ID, Decimal("4.0"),
                users=users, profiles=profiles, attendances=attendances, ratings=ratings,
            )
        assert exc.value.status_code == 404
        ratings.upsert_rating.assert_not_called()

    def test_400_when_target_has_never_hosted(self, db, repos):
        users, profiles, attendances, ratings = repos
        profiles.get_hosted_events.return_value = []
        with pytest.raises(HTTPException) as exc:
            rating_service.rate_host(
                db, RATER_ID, HOST_ID, Decimal("4.0"),
                users=users, profiles=profiles, attendances=attendances, ratings=ratings,
            )
        assert exc.value.status_code == 400
        ratings.upsert_rating.assert_not_called()

    def test_403_when_rater_did_not_attend_ended_event(self, db, repos):
        users, profiles, attendances, ratings = repos
        attendances.has_attended_ended_event_by_host.return_value = False
        with pytest.raises(HTTPException) as exc:
            rating_service.rate_host(
                db, RATER_ID, HOST_ID, Decimal("4.0"),
                users=users, profiles=profiles, attendances=attendances, ratings=ratings,
            )
        assert exc.value.status_code == 403
        ratings.upsert_rating.assert_not_called()

    def test_happy_path_upserts_normalised_review(self, db, repos):
        users, profiles, attendances, ratings = repos

        result = rating_service.rate_host(
            db, RATER_ID, HOST_ID, Decimal("4.5"), review_text="  great host  ",
            users=users, profiles=profiles, attendances=attendances, ratings=ratings,
        )

        assert result.score == Decimal("4.5")
        # Whitespace must be trimmed before hitting the DB.
        ratings.upsert_rating.assert_called_once_with(db, {
            "rater_id": RATER_ID,
            "host_id": HOST_ID,
            "score": 4.5,
            "review_text": "great host",
        })

    def test_whitespace_only_review_becomes_none(self, db, repos):
        users, profiles, attendances, ratings = repos

        rating_service.rate_host(
            db, RATER_ID, HOST_ID, Decimal("3.0"), review_text="   ",
            users=users, profiles=profiles, attendances=attendances, ratings=ratings,
        )

        sent = ratings.upsert_rating.call_args.args[1]
        assert sent["review_text"] is None


# ── list_reviews ────────────────────────────────────────────────────────────


class TestListReviews:
    def test_404_when_host_missing(self, db):
        users = MagicMock()
        users.get_user_by_id.return_value = None
        ratings = MagicMock()

        with pytest.raises(HTTPException) as exc:
            rating_service.list_reviews(db, HOST_ID, users=users, ratings=ratings)
        assert exc.value.status_code == 404
        # No ratings query when the host doesn't exist.
        ratings.list_reviews_for_host.assert_not_called()

    def test_empty_response_when_no_reviews(self, db):
        users = MagicMock()
        users.get_user_by_id.return_value = {"id": HOST_ID}
        ratings = MagicMock()
        ratings.list_reviews_for_host.return_value = ([], 0)

        result = rating_service.list_reviews(db, HOST_ID, users=users, ratings=ratings)

        assert result.total == 0
        assert result.items == []
        assert result.total_pages == 0

    def test_resolves_rater_usernames(self, db):
        users = MagicMock()
        users.get_user_by_id.return_value = {"id": HOST_ID}
        users.get_users_by_ids.return_value = [
            {"id": RATER_ID, "username": "alice"},
            {"id": OTHER_RATER_ID, "username": "bob"},
        ]
        ratings = MagicMock()
        ratings.list_reviews_for_host.return_value = ([
            {
                "id": RATING_ID,
                "rater_id": RATER_ID,
                "score": 5.0,
                "review_text": "great",
                "created_at": "2026-01-01T00:00:00+00:00",
            },
            {
                "id": "00000000-0000-0000-0000-000000000034",
                "rater_id": OTHER_RATER_ID,
                "score": 3.0,
                "review_text": None,
                "created_at": "2026-01-02T00:00:00+00:00",
            },
        ], 2)

        result = rating_service.list_reviews(db, HOST_ID, users=users, ratings=ratings)

        assert [item.rater_username for item in result.items] == ["alice", "bob"]

    def test_unknown_rater_falls_back_to_unknown(self, db):
        # If a user id ends up dangling (deleted user, etc.) the listing
        # must not crash — the placeholder string keeps the response shape.
        users = MagicMock()
        users.get_user_by_id.return_value = {"id": HOST_ID}
        users.get_users_by_ids.return_value = []  # nothing found
        ratings = MagicMock()
        ratings.list_reviews_for_host.return_value = ([{
            "id": RATING_ID,
            "rater_id": RATER_ID,
            "score": 4.0,
            "review_text": None,
            "created_at": "2026-01-01T00:00:00+00:00",
        }], 1)

        result = rating_service.list_reviews(db, HOST_ID, users=users, ratings=ratings)

        assert result.items[0].rater_username == "unknown"
