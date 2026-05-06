"""Unit tests for `services.profile` — exercises the keyword-DI seam."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.profile import ProfileUpdateRequest
from app.services import profile as profile_service


HOST_ID = "00000000-0000-0000-0000-000000000040"
VIEWER_ID = "00000000-0000-0000-0000-000000000041"
EVENT_UPCOMING = "00000000-0000-0000-0000-000000000042"
EVENT_ENDED = "00000000-0000-0000-0000-000000000043"


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


def _user(public_email: bool = False, public_phone: bool = False) -> dict:
    return {
        "id": HOST_ID,
        "username": "alice",
        "email": "alice@example.com",
        "email_visibility": public_email,
        "phone_number": "+1-555-0100",
        "phone_visibility": public_phone,
        "is_active": True,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "role": "registered",
        "auth_provider": "local",
        "email_verified": True,
    }


def _event(id_: str, status: str, start: str = "2026-06-01T10:00:00+00:00") -> dict:
    return {
        "id": id_,
        "host_id": HOST_ID,
        "title": f"Event {id_[-1]}",
        "description": "desc",
        "start_datetime": start,
        "end_datetime": "2026-06-01T12:00:00+00:00",
        "visibility": "public",
        "is_age_restricted": False,
        "attendee_limit": None,
        "attendee_count": 0,
        "status": status,
    }


@pytest.fixture
def repos():
    profiles = MagicMock()
    ratings = MagicMock()
    events = MagicMock()
    attendances = MagicMock()
    profiles.get_full_user_profile.return_value = _user()
    ratings.get_host_rating_stats.return_value = {"average": 4.2}
    profiles.get_hosted_events.return_value = []
    events.get_primary_locations_for_events.return_value = {}
    events.get_categories_for_events.return_value = {}
    events.get_primary_images_for_events.return_value = {}
    attendances.has_attended_ended_event_by_host.return_value = False
    return profiles, ratings, events, attendances


# ── get_host_profile ────────────────────────────────────────────────────────


class TestGetHostProfile:
    def test_404_when_user_missing(self, db, repos):
        profiles, ratings, events, attendances = repos
        profiles.get_full_user_profile.return_value = None
        with pytest.raises(HTTPException) as exc:
            profile_service.get_host_profile(
                db, HOST_ID,
                profiles=profiles, ratings=ratings, events=events, attendances=attendances,
            )
        assert exc.value.status_code == 404

    def test_orders_upcoming_before_past(self, db, repos):
        profiles, ratings, events, attendances = repos
        profiles.get_hosted_events.return_value = [
            _event(EVENT_ENDED, "ended", start="2025-06-01T10:00:00+00:00"),
            _event(EVENT_UPCOMING, "published", start="2026-12-01T10:00:00+00:00"),
        ]

        result = profile_service.get_host_profile(
            db, HOST_ID,
            profiles=profiles, ratings=ratings, events=events, attendances=attendances,
        )

        # Upcoming comes first regardless of input order.
        assert [str(e.id) for e in result.hosted_events] == [EVENT_UPCOMING, EVENT_ENDED]

    def test_redacts_email_and_phone_when_private(self, db, repos):
        profiles, ratings, events, attendances = repos
        profiles.get_full_user_profile.return_value = _user(public_email=False, public_phone=False)

        result = profile_service.get_host_profile(
            db, HOST_ID,
            profiles=profiles, ratings=ratings, events=events, attendances=attendances,
        )

        assert result.email is None
        assert result.phone_number is None

    def test_exposes_email_and_phone_when_public(self, db, repos):
        profiles, ratings, events, attendances = repos
        profiles.get_full_user_profile.return_value = _user(public_email=True, public_phone=True)

        result = profile_service.get_host_profile(
            db, HOST_ID,
            profiles=profiles, ratings=ratings, events=events, attendances=attendances,
        )

        assert result.email == "alice@example.com"
        assert result.phone_number == "+1-555-0100"

    def test_can_rate_only_when_viewer_attended_ended_event(self, db, repos):
        profiles, ratings, events, attendances = repos
        attendances.has_attended_ended_event_by_host.return_value = True

        result = profile_service.get_host_profile(
            db, HOST_ID, current_user_id=VIEWER_ID,
            profiles=profiles, ratings=ratings, events=events, attendances=attendances,
        )
        assert result.can_rate is True

    def test_can_rate_false_when_owner_views_self(self, db, repos):
        profiles, ratings, events, attendances = repos
        attendances.has_attended_ended_event_by_host.return_value = True  # would say yes

        result = profile_service.get_host_profile(
            db, HOST_ID, current_user_id=HOST_ID,
            profiles=profiles, ratings=ratings, events=events, attendances=attendances,
        )
        assert result.can_rate is False

    def test_drafts_only_visible_to_owner(self, db, repos):
        profiles, ratings, events, attendances = repos
        profile_service.get_host_profile(
            db, HOST_ID, current_user_id=HOST_ID,
            profiles=profiles, ratings=ratings, events=events, attendances=attendances,
        )
        # owner view → include_drafts=True
        profiles.get_hosted_events.assert_called_once_with(db, HOST_ID, include_drafts=True)

        profiles.get_hosted_events.reset_mock()
        profile_service.get_host_profile(
            db, HOST_ID, current_user_id=VIEWER_ID,
            profiles=profiles, ratings=ratings, events=events, attendances=attendances,
        )
        # other-viewer → include_drafts=False
        profiles.get_hosted_events.assert_called_once_with(db, HOST_ID, include_drafts=False)


# ── update_profile ──────────────────────────────────────────────────────────


class TestUpdateProfile:
    def test_400_when_no_fields_provided(self, db):
        profiles = MagicMock()
        with pytest.raises(HTTPException) as exc:
            profile_service.update_profile(
                db, HOST_ID, ProfileUpdateRequest(), profiles=profiles,
            )
        assert exc.value.status_code == 400
        profiles.update_user_profile.assert_not_called()

    def test_translates_visibility_strings_to_booleans(self, db):
        profiles = MagicMock()
        profiles.update_user_profile.return_value = {
            **_user(public_email=True),
            "id": HOST_ID,
        }

        profile_service.update_profile(
            db, HOST_ID,
            ProfileUpdateRequest(email_visibility="public", phone_visibility="private"),
            profiles=profiles,
        )

        sent = profiles.update_user_profile.call_args.args[2]
        assert sent["email_visibility"] is True
        assert sent["phone_visibility"] is False
