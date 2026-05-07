"""Unit tests for `services.recommendation_emitter` (Phase 2).

Targets the early-return branches and orchestration of
`emit_event_recommendations` through the keyword-default DI seam.
The SQL-heavy internal helpers (`_get_event_category_ids`,
`_find_candidates`, etc.) still hit the database directly — those
branches stay covered by tests/test_recommendation_emitter.py
contract pins until they get DI'd in a follow-up.
"""

from unittest.mock import MagicMock

import pytest

from app.services import recommendation_emitter as rec

EVENT_ID = "00000000-0000-0000-0000-0000000000a1"
HOST_ID = "00000000-0000-0000-0000-0000000000a2"
USER_ID = "00000000-0000-0000-0000-0000000000a3"


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


@pytest.fixture
def events_repo():
    return MagicMock(name="event_repo")


@pytest.fixture
def attendances_repo():
    return MagicMock(name="attendance_repo")


@pytest.fixture
def notifications_repo():
    return MagicMock(name="notification_repo")


def _stub_event(**overrides) -> dict:
    base = {
        "id": EVENT_ID,
        "host_id": HOST_ID,
        "title": "Public Event",
        "visibility": "public",
        "status": "published",
    }
    base.update(overrides)
    return base


class TestEmitEventRecommendationsEarlyReturns:
    def test_returns_zero_when_event_missing(
        self, db, events_repo, attendances_repo, notifications_repo,
    ):
        events_repo.get_event_by_id.return_value = None

        n = rec.emit_event_recommendations(
            db, EVENT_ID, HOST_ID,
            events=events_repo, attendances=attendances_repo, notifications=notifications_repo,
        )

        assert n == 0
        notifications_repo.insert_notifications_bulk.assert_not_called()

    def test_returns_zero_for_private_event(
        self, db, events_repo, attendances_repo, notifications_repo,
    ):
        events_repo.get_event_by_id.return_value = _stub_event(visibility="private")

        n = rec.emit_event_recommendations(
            db, EVENT_ID, HOST_ID,
            events=events_repo, attendances=attendances_repo, notifications=notifications_repo,
        )

        assert n == 0
        notifications_repo.insert_notifications_bulk.assert_not_called()

    @pytest.mark.parametrize("status_value", ["draft", "cancelled", "ended"])
    def test_returns_zero_for_non_active_status(
        self, db, events_repo, attendances_repo, notifications_repo, status_value,
    ):
        events_repo.get_event_by_id.return_value = _stub_event(status=status_value)

        n = rec.emit_event_recommendations(
            db, EVENT_ID, HOST_ID,
            events=events_repo, attendances=attendances_repo, notifications=notifications_repo,
        )

        assert n == 0
        notifications_repo.insert_notifications_bulk.assert_not_called()


class TestEmitEventRecommendationsOrchestration:
    def test_returns_zero_when_event_has_no_categories(
        self, db, events_repo, attendances_repo, notifications_repo, monkeypatch,
    ):
        events_repo.get_event_by_id.return_value = _stub_event()
        monkeypatch.setattr(rec, "_get_event_category_ids", lambda *a, **k: [])

        n = rec.emit_event_recommendations(
            db, EVENT_ID, HOST_ID,
            events=events_repo, attendances=attendances_repo, notifications=notifications_repo,
        )

        assert n == 0
        notifications_repo.insert_notifications_bulk.assert_not_called()

    def test_returns_zero_when_no_candidate_users(
        self, db, events_repo, attendances_repo, notifications_repo, monkeypatch,
    ):
        events_repo.get_event_by_id.return_value = _stub_event()
        monkeypatch.setattr(rec, "_get_event_category_ids", lambda *a, **k: ["cat1"])
        monkeypatch.setattr(rec, "_find_candidates", lambda *a, **k: [])

        n = rec.emit_event_recommendations(
            db, EVENT_ID, HOST_ID,
            events=events_repo, attendances=attendances_repo, notifications=notifications_repo,
        )

        assert n == 0
        notifications_repo.insert_notifications_bulk.assert_not_called()

    def test_inserts_notifications_for_remaining_candidates(
        self, db, events_repo, attendances_repo, notifications_repo, monkeypatch,
    ):
        events_repo.get_event_by_id.return_value = _stub_event()
        monkeypatch.setattr(rec, "_get_event_category_ids", lambda *a, **k: ["cat1"])
        monkeypatch.setattr(rec, "_find_candidates", lambda *a, **k: [USER_ID, "u2"])
        monkeypatch.setattr(rec, "_drop_users_already_engaged", lambda *a, **k: [USER_ID, "u2"])
        monkeypatch.setattr(rec, "_drop_users_already_notified", lambda *a, **k: [USER_ID])
        monkeypatch.setattr(rec, "_drop_users_over_daily_cap", lambda *a, **k: [USER_ID])
        monkeypatch.setattr(rec, "_build_message", lambda *a, **k: "Recommended event")
        notifications_repo.insert_notifications_bulk.return_value = [
            {"id": "n1", "user_id": USER_ID},
        ]

        n = rec.emit_event_recommendations(
            db, EVENT_ID, HOST_ID,
            events=events_repo, attendances=attendances_repo, notifications=notifications_repo,
        )

        assert n == 1
        notifications_repo.insert_notifications_bulk.assert_called_once()
        rows = notifications_repo.insert_notifications_bulk.call_args.args[1]
        assert rows == [{
            "user_id": USER_ID, "event_id": EVENT_ID,
            "type": "event_recommended", "message": "Recommended event", "is_read": False,
        }]
