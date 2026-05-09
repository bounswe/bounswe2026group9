"""Unit tests for `services.invite` — invites + access requests + grants."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.invite import (
    AccessRequestDecision,
    InviteCreateRequest,
)
from app.services import invite as invite_service

EVENT_ID = "00000000-0000-0000-0000-000000000070"
HOST_ID = "00000000-0000-0000-0000-000000000071"
USER_ID = "00000000-0000-0000-0000-000000000072"
INVITE_ID = "00000000-0000-0000-0000-000000000073"
REQUEST_ID = "00000000-0000-0000-0000-000000000074"


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


def _event(*, status: str = "published", visibility: str = "private", host_id: str = HOST_ID) -> dict:
    return {
        "id": EVENT_ID,
        "host_id": host_id,
        "status": status,
        "visibility": visibility,
        "title": "Private Show",
    }


def _invite(*, expires: str | None = None, max_uses: int | None = None, use_count: int = 0) -> dict:
    return {
        "id": INVITE_ID,
        "event_id": EVENT_ID,
        "token": "tok-abc",
        "expires_at": expires,
        "max_uses": max_uses,
        "use_count": use_count,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


def _request(status: str = "pending") -> dict:
    return {
        "id": REQUEST_ID,
        "event_id": EVENT_ID,
        "user_id": USER_ID,
        "status": status,
        "created_at": "2026-01-01T00:00:00+00:00",
        "resolved_at": None,
    }


@pytest.fixture
def repos():
    invites = MagicMock()
    events = MagicMock()
    users = MagicMock()
    notifications = MagicMock()
    events.get_event_by_id.return_value = _event()
    return invites, events, users, notifications


# ── create_invite ───────────────────────────────────────────────────────────


class TestCreateInvite:
    def test_404_when_event_missing(self, db, repos):
        invites, events, users, notifications = repos
        events.get_event_by_id.return_value = None
        with pytest.raises(HTTPException) as exc:
            invite_service.create_invite(
                db, EVENT_ID, HOST_ID, InviteCreateRequest(),
                invites=invites, events=events,
            )
        assert exc.value.status_code == 404

    def test_403_when_not_host(self, db, repos):
        invites, events, *_ = repos
        with pytest.raises(HTTPException) as exc:
            invite_service.create_invite(
                db, EVENT_ID, USER_ID, InviteCreateRequest(),
                invites=invites, events=events,
            )
        assert exc.value.status_code == 403

    def test_400_when_event_public(self, db, repos):
        invites, events, *_ = repos
        events.get_event_by_id.return_value = _event(visibility="public")
        with pytest.raises(HTTPException) as exc:
            invite_service.create_invite(
                db, EVENT_ID, HOST_ID, InviteCreateRequest(),
                invites=invites, events=events,
            )
        assert exc.value.status_code == 400

    def test_400_when_event_not_active(self, db, repos):
        invites, events, *_ = repos
        events.get_event_by_id.return_value = _event(status="draft")
        with pytest.raises(HTTPException) as exc:
            invite_service.create_invite(
                db, EVENT_ID, HOST_ID, InviteCreateRequest(),
                invites=invites, events=events,
            )
        assert exc.value.status_code == 400

    def test_happy_path_inserts_token_and_returns_url(self, db, repos):
        invites, events, *_ = repos
        invites.insert_invite.return_value = _invite()

        result = invite_service.create_invite(
            db, EVENT_ID, HOST_ID, InviteCreateRequest(max_uses=5),
            invites=invites, events=events,
        )
        sent = invites.insert_invite.call_args.args[1]
        assert sent["max_uses"] == 5
        assert sent["expires_at"] is None
        assert result.invite_url.endswith(f"/event/{EVENT_ID}/invite/tok-abc")


# ── list_invites ────────────────────────────────────────────────────────────


class TestListInvites:
    def test_403_when_not_host(self, db, repos):
        invites, events, *_ = repos
        with pytest.raises(HTTPException) as exc:
            invite_service.list_invites(
                db, EVENT_ID, USER_ID, invites=invites, events=events,
            )
        assert exc.value.status_code == 403

    def test_returns_responses_for_host(self, db, repos):
        invites, events, *_ = repos
        invites.get_invites_by_event.return_value = [_invite(), _invite()]
        result = invite_service.list_invites(
            db, EVENT_ID, HOST_ID, invites=invites, events=events,
        )
        assert len(result.items) == 2


# ── accept_invite ───────────────────────────────────────────────────────────


class TestAcceptInvite:
    def test_400_when_host_attempts(self, db, repos):
        invites, events, *_ = repos
        with pytest.raises(HTTPException) as exc:
            invite_service.accept_invite(
                db, EVENT_ID, "tok", HOST_ID, invites=invites, events=events,
            )
        assert exc.value.status_code == 400

    def test_400_when_already_granted(self, db, repos):
        invites, events, *_ = repos
        invites.get_access_grant.return_value = {"id": "grant-1"}
        with pytest.raises(HTTPException) as exc:
            invite_service.accept_invite(
                db, EVENT_ID, "tok", USER_ID, invites=invites, events=events,
            )
        assert exc.value.status_code == 400

    def test_404_when_token_unknown(self, db, repos):
        invites, events, *_ = repos
        invites.get_access_grant.return_value = None
        invites.get_invite_by_token.return_value = None
        with pytest.raises(HTTPException) as exc:
            invite_service.accept_invite(
                db, EVENT_ID, "tok", USER_ID, invites=invites, events=events,
            )
        assert exc.value.status_code == 404

    def test_400_when_expired(self, db, repos):
        invites, events, *_ = repos
        invites.get_access_grant.return_value = None
        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        invites.get_invite_by_token.return_value = _invite(expires=past)
        with pytest.raises(HTTPException) as exc:
            invite_service.accept_invite(
                db, EVENT_ID, "tok", USER_ID, invites=invites, events=events,
            )
        assert exc.value.status_code == 400

    def test_400_when_max_uses_reached(self, db, repos):
        invites, events, *_ = repos
        invites.get_access_grant.return_value = None
        invites.get_invite_by_token.return_value = _invite(max_uses=2, use_count=2)
        with pytest.raises(HTTPException) as exc:
            invite_service.accept_invite(
                db, EVENT_ID, "tok", USER_ID, invites=invites, events=events,
            )
        assert exc.value.status_code == 400

    def test_grants_and_increments_use_count(self, db, repos):
        invites, events, *_ = repos
        invites.get_access_grant.return_value = None
        invites.get_invite_by_token.return_value = _invite(max_uses=5, use_count=0)

        result = invite_service.accept_invite(
            db, EVENT_ID, "tok", USER_ID, invites=invites, events=events,
        )
        assert result == {"message": "Access granted successfully"}
        invites.insert_access_grant.assert_called_once()
        invites.increment_invite_use_count.assert_called_once_with(db, INVITE_ID)


# ── create_access_request ───────────────────────────────────────────────────


class TestCreateAccessRequest:
    def test_400_when_event_public(self, db, repos):
        invites, events, users, notifications = repos
        events.get_event_by_id.return_value = _event(visibility="public")
        with pytest.raises(HTTPException) as exc:
            invite_service.create_access_request(
                db, EVENT_ID, USER_ID,
                invites=invites, events=events, users=users, notifications=notifications,
            )
        assert exc.value.status_code == 400

    def test_400_when_already_granted(self, db, repos):
        invites, events, users, notifications = repos
        invites.get_access_grant.return_value = {"id": "g1"}
        with pytest.raises(HTTPException) as exc:
            invite_service.create_access_request(
                db, EVENT_ID, USER_ID,
                invites=invites, events=events, users=users, notifications=notifications,
            )
        assert exc.value.status_code == 400

    def test_400_when_already_requested(self, db, repos):
        invites, events, users, notifications = repos
        invites.get_access_grant.return_value = None
        invites.get_access_request.return_value = _request()
        with pytest.raises(HTTPException) as exc:
            invite_service.create_access_request(
                db, EVENT_ID, USER_ID,
                invites=invites, events=events, users=users, notifications=notifications,
            )
        assert exc.value.status_code == 400

    def test_creates_request_and_notifies_host(self, db, repos):
        invites, events, users, notifications = repos
        invites.get_access_grant.return_value = None
        invites.get_access_request.return_value = None
        invites.insert_access_request.return_value = _request()
        users.get_user_by_id.return_value = {"id": USER_ID, "username": "alice"}

        result = invite_service.create_access_request(
            db, EVENT_ID, USER_ID,
            invites=invites, events=events, users=users, notifications=notifications,
        )
        assert result.username == "alice"
        # Host notified.
        sent = notifications.insert_notification.call_args.args[1]
        assert sent["user_id"] == HOST_ID
        assert sent["type"] == "access_request"


# ── list_access_requests ────────────────────────────────────────────────────


class TestListAccessRequests:
    def test_403_when_not_host(self, db, repos):
        invites, events, users, _ = repos
        with pytest.raises(HTTPException) as exc:
            invite_service.list_access_requests(
                db, EVENT_ID, USER_ID,
                invites=invites, events=events, users=users,
            )
        assert exc.value.status_code == 403

    def test_resolves_usernames_from_user_repo(self, db, repos):
        invites, events, users, _ = repos
        invites.get_pending_requests_by_event.return_value = [_request()]
        users.get_users_by_ids.return_value = [
            {"id": USER_ID, "username": "alice"},
        ]

        result = invite_service.list_access_requests(
            db, EVENT_ID, HOST_ID,
            invites=invites, events=events, users=users,
        )
        assert result.items[0].username == "alice"
        users.get_users_by_ids.assert_called_once()

    def test_no_user_lookup_when_no_requests(self, db, repos):
        invites, events, users, _ = repos
        invites.get_pending_requests_by_event.return_value = []

        invite_service.list_access_requests(
            db, EVENT_ID, HOST_ID,
            invites=invites, events=events, users=users,
        )
        users.get_users_by_ids.assert_not_called()


# ── decide_access_request ───────────────────────────────────────────────────


class TestDecideAccessRequest:
    def test_403_when_not_host(self, db, repos):
        invites, events, users, notifications = repos
        with pytest.raises(HTTPException) as exc:
            invite_service.decide_access_request(
                db, EVENT_ID, REQUEST_ID, USER_ID,
                AccessRequestDecision(status="approved"),
                invites=invites, events=events, users=users, notifications=notifications,
            )
        assert exc.value.status_code == 403

    def test_404_when_request_belongs_to_different_event(self, db, repos):
        invites, events, users, notifications = repos
        invites.get_access_request_by_id.return_value = {
            **_request(),
            "event_id": "00000000-0000-0000-0000-000000000099",
        }
        with pytest.raises(HTTPException) as exc:
            invite_service.decide_access_request(
                db, EVENT_ID, REQUEST_ID, HOST_ID,
                AccessRequestDecision(status="approved"),
                invites=invites, events=events, users=users, notifications=notifications,
            )
        assert exc.value.status_code == 404

    def test_400_when_request_already_resolved(self, db, repos):
        invites, events, users, notifications = repos
        invites.get_access_request_by_id.return_value = _request(status="approved")
        with pytest.raises(HTTPException) as exc:
            invite_service.decide_access_request(
                db, EVENT_ID, REQUEST_ID, HOST_ID,
                AccessRequestDecision(status="rejected"),
                invites=invites, events=events, users=users, notifications=notifications,
            )
        assert exc.value.status_code == 400

    def test_approval_grants_access_and_notifies_user(self, db, repos):
        invites, events, users, notifications = repos
        invites.get_access_request_by_id.return_value = _request()
        invites.update_access_request.return_value = _request(status="approved")
        users.get_user_by_id.return_value = {"id": USER_ID, "username": "alice"}

        invite_service.decide_access_request(
            db, EVENT_ID, REQUEST_ID, HOST_ID,
            AccessRequestDecision(status="approved"),
            invites=invites, events=events, users=users, notifications=notifications,
        )

        invites.insert_access_grant.assert_called_once()
        sent = notifications.insert_notification.call_args.args[1]
        assert sent["type"] == "access_approved"
        assert sent["user_id"] == USER_ID

    def test_rejection_does_not_grant_and_sends_rejection_notification(self, db, repos):
        invites, events, users, notifications = repos
        invites.get_access_request_by_id.return_value = _request()
        invites.update_access_request.return_value = _request(status="rejected")
        users.get_user_by_id.return_value = {"id": USER_ID, "username": "alice"}

        invite_service.decide_access_request(
            db, EVENT_ID, REQUEST_ID, HOST_ID,
            AccessRequestDecision(status="rejected"),
            invites=invites, events=events, users=users, notifications=notifications,
        )

        invites.insert_access_grant.assert_not_called()
        sent = notifications.insert_notification.call_args.args[1]
        assert sent["type"] == "access_rejected"
