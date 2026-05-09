"""Unit tests for `services.attendance` — exercises the keyword-DI seam.

The token-helper internals (`_generate_check_in_token` /
`_verify_check_in_token`) stay live because they're pure HMAC logic that
runs without I/O. The repository handles are mocked through the new kwargs.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.attendance import CheckInRequest
from app.services import attendance as att_service

EVENT_ID = "00000000-0000-0000-0000-000000000060"
USER_ID = "00000000-0000-0000-0000-000000000061"
HOST_ID = "00000000-0000-0000-0000-000000000062"
ATTENDANCE_ID = "00000000-0000-0000-0000-000000000063"


@pytest.fixture
def db():
    return MagicMock(name="supabase_client")


def _event(
    *,
    status: str = "published",
    host_id: str = HOST_ID,
    age_restricted: bool = False,
    limit: int | None = None,
    count: int = 0,
) -> dict:
    return {
        "id": EVENT_ID,
        "host_id": host_id,
        "status": status,
        "is_age_restricted": age_restricted,
        "attendee_limit": limit,
        "attendee_count": count,
        "end_datetime": "2026-12-31T23:59:00+00:00",
    }


def _attendance(*, status: str = "going", token: str | None = None, checked_in: str | None = None) -> dict:
    return {
        "id": ATTENDANCE_ID,
        "user_id": USER_ID,
        "event_id": EVENT_ID,
        "status": status,
        "marked_at": "2026-01-01T00:00:00+00:00",
        "check_in_token": token,
        "checked_in_at": checked_in,
    }


@pytest.fixture
def repos():
    attendances = MagicMock()
    events = MagicMock()
    users = MagicMock()
    events.get_event_by_id.return_value = _event()
    return attendances, events, users


# ── set_attendance ──────────────────────────────────────────────────────────


class TestSetAttendance:
    def test_400_for_unsupported_status(self, db, repos):
        a, e, u = repos
        with pytest.raises(HTTPException) as exc:
            att_service.set_attendance(
                db, EVENT_ID, USER_ID, "interested",
                attendances=a, events=e, users=u,
            )
        assert exc.value.status_code == 400

    def test_404_when_event_missing(self, db, repos):
        a, e, u = repos
        e.get_event_by_id.return_value = None
        with pytest.raises(HTTPException) as exc:
            att_service.set_attendance(
                db, EVENT_ID, USER_ID, "going",
                attendances=a, events=e, users=u,
            )
        assert exc.value.status_code == 404

    def test_400_when_event_not_active(self, db, repos):
        a, e, u = repos
        e.get_event_by_id.return_value = _event(status="cancelled")
        with pytest.raises(HTTPException) as exc:
            att_service.set_attendance(
                db, EVENT_ID, USER_ID, "going",
                attendances=a, events=e, users=u,
            )
        assert exc.value.status_code == 400

    def test_400_when_host_attempts_self_attendance(self, db, repos):
        a, e, u = repos
        e.get_event_by_id.return_value = _event(host_id=USER_ID)
        with pytest.raises(HTTPException) as exc:
            att_service.set_attendance(
                db, EVENT_ID, USER_ID, "going",
                attendances=a, events=e, users=u,
            )
        assert exc.value.status_code == 400

    def test_403_when_age_restricted_and_dob_missing(self, db, repos):
        a, e, u = repos
        e.get_event_by_id.return_value = _event(age_restricted=True)
        u.get_user_date_of_birth.return_value = None
        with pytest.raises(HTTPException) as exc:
            att_service.set_attendance(
                db, EVENT_ID, USER_ID, "going",
                attendances=a, events=e, users=u,
            )
        assert exc.value.status_code == 403

    def test_403_when_underage(self, db, repos):
        a, e, u = repos
        e.get_event_by_id.return_value = _event(age_restricted=True)
        # 17 years and 1 month ago
        ago = datetime.now(UTC).date() - timedelta(days=365 * 17 + 30)
        u.get_user_date_of_birth.return_value = ago.isoformat()
        with pytest.raises(HTTPException) as exc:
            att_service.set_attendance(
                db, EVENT_ID, USER_ID, "going",
                attendances=a, events=e, users=u,
            )
        assert exc.value.status_code == 403

    def test_400_when_capacity_reached(self, db, repos):
        a, e, u = repos
        e.get_event_by_id.return_value = _event(limit=10, count=10)
        a.get_attendance.return_value = None
        with pytest.raises(HTTPException) as exc:
            att_service.set_attendance(
                db, EVENT_ID, USER_ID, "going",
                attendances=a, events=e, users=u,
            )
        assert exc.value.status_code == 400

    def test_first_going_inserts_with_token(self, db, repos):
        a, e, u = repos
        a.get_attendance.return_value = None
        a.insert_attendance.return_value = _attendance(token="t1")

        att_service.set_attendance(
            db, EVENT_ID, USER_ID, "going",
            attendances=a, events=e, users=u,
        )

        sent = a.insert_attendance.call_args.args[1]
        assert sent["status"] == "going"
        assert sent["check_in_token"]  # non-empty signed token

    def test_idempotent_when_already_going(self, db, repos):
        a, e, u = repos
        existing = _attendance(token="existing-token")
        a.get_attendance.return_value = existing

        result = att_service.set_attendance(
            db, EVENT_ID, USER_ID, "going",
            attendances=a, events=e, users=u,
        )

        # Already going → no insert / no update / no token rotation.
        a.insert_attendance.assert_not_called()
        a.update_attendance.assert_not_called()
        a.update_attendance_token.assert_not_called()
        assert str(result.id) == ATTENDANCE_ID


# ── remove_attendance ───────────────────────────────────────────────────────


class TestRemoveAttendance:
    def test_404_when_no_attendance(self, db, repos):
        a, _, _ = repos
        a.get_attendance.return_value = None
        with pytest.raises(HTTPException) as exc:
            att_service.remove_attendance(db, EVENT_ID, USER_ID, attendances=a)
        assert exc.value.status_code == 404

    def test_deletes_when_present(self, db, repos):
        a, _, _ = repos
        a.get_attendance.return_value = _attendance()

        att_service.remove_attendance(db, EVENT_ID, USER_ID, attendances=a)

        a.delete_attendance.assert_called_once_with(db, USER_ID, EVENT_ID)


# ── get_my_qr ───────────────────────────────────────────────────────────────


class TestGetMyQr:
    def test_404_when_not_going(self, db, repos):
        a, e, _ = repos
        a.get_attendance.return_value = None
        with pytest.raises(HTTPException) as exc:
            att_service.get_my_qr(db, EVENT_ID, USER_ID, attendances=a, events=e)
        assert exc.value.status_code == 404

    def test_returns_existing_token(self, db, repos):
        a, e, _ = repos
        a.get_attendance.return_value = _attendance(token="existing")

        result = att_service.get_my_qr(
            db, EVENT_ID, USER_ID, attendances=a, events=e
        )

        assert result.token == "existing"
        a.update_attendance_token.assert_not_called()

    def test_backfills_when_token_missing(self, db, repos):
        a, e, _ = repos
        a.get_attendance.return_value = _attendance(token=None)

        result = att_service.get_my_qr(
            db, EVENT_ID, USER_ID, attendances=a, events=e
        )

        assert result.token  # generated
        a.update_attendance_token.assert_called_once()


# ── check_in ────────────────────────────────────────────────────────────────


class TestCheckIn:
    def test_404_when_event_missing(self, db, repos):
        a, e, u = repos
        e.get_event_by_id.return_value = None
        with pytest.raises(HTTPException) as exc:
            att_service.check_in(
                db, EVENT_ID, HOST_ID, CheckInRequest(user_id=USER_ID),
                attendances=a, events=e, users=u,
            )
        assert exc.value.status_code == 404

    def test_403_when_caller_is_not_host(self, db, repos):
        a, e, u = repos
        e.get_event_by_id.return_value = _event()
        with pytest.raises(HTTPException) as exc:
            att_service.check_in(
                db, EVENT_ID, "not-the-host", CheckInRequest(user_id=USER_ID),
                attendances=a, events=e, users=u,
            )
        assert exc.value.status_code == 403

    def test_400_when_event_not_active(self, db, repos):
        a, e, u = repos
        e.get_event_by_id.return_value = _event(status="ended")
        with pytest.raises(HTTPException) as exc:
            att_service.check_in(
                db, EVENT_ID, HOST_ID, CheckInRequest(user_id=USER_ID),
                attendances=a, events=e, users=u,
            )
        assert exc.value.status_code == 400

    def test_400_when_neither_token_nor_user_id_provided(self, db, repos):
        a, e, u = repos
        with pytest.raises(HTTPException) as exc:
            att_service.check_in(
                db, EVENT_ID, HOST_ID, CheckInRequest(),
                attendances=a, events=e, users=u,
            )
        assert exc.value.status_code == 400

    def test_409_when_already_checked_in(self, db, repos):
        a, e, u = repos
        a.get_attendance.return_value = _attendance(checked_in="2026-01-01T00:00:00+00:00")
        with pytest.raises(HTTPException) as exc:
            att_service.check_in(
                db, EVENT_ID, HOST_ID, CheckInRequest(user_id=USER_ID),
                attendances=a, events=e, users=u,
            )
        assert exc.value.status_code == 409

    def test_404_when_user_id_path_finds_no_attendance(self, db, repos):
        a, e, u = repos
        a.get_attendance.return_value = None
        with pytest.raises(HTTPException) as exc:
            att_service.check_in(
                db, EVENT_ID, HOST_ID, CheckInRequest(user_id=USER_ID),
                attendances=a, events=e, users=u,
            )
        assert exc.value.status_code == 404

    def test_invalid_token_returns_400(self, db, repos):
        a, e, u = repos
        with pytest.raises(HTTPException) as exc:
            att_service.check_in(
                db, EVENT_ID, HOST_ID, CheckInRequest(token="not-a-real-token"),
                attendances=a, events=e, users=u,
            )
        assert exc.value.status_code == 400

    def test_wrong_event_token_returns_400(self, db, repos):
        a, e, u = repos
        # Generate a token for a different event id.
        bad_token = att_service._generate_check_in_token(
            "00000000-0000-0000-0000-0000000000ff", USER_ID
        )
        with pytest.raises(HTTPException) as exc:
            att_service.check_in(
                db, EVENT_ID, HOST_ID, CheckInRequest(token=bad_token),
                attendances=a, events=e, users=u,
            )
        assert exc.value.status_code == 400

    def test_happy_path_marks_and_returns_username(self, db, repos):
        a, e, u = repos
        a.get_attendance.return_value = _attendance()
        a.mark_checked_in.return_value = _attendance(
            checked_in="2026-06-01T18:00:00+00:00"
        )
        u.get_user_by_id.return_value = {"id": USER_ID, "username": "alice"}

        result = att_service.check_in(
            db, EVENT_ID, HOST_ID, CheckInRequest(user_id=USER_ID),
            attendances=a, events=e, users=u,
        )
        assert result.username == "alice"
        a.mark_checked_in.assert_called_once_with(db, ATTENDANCE_ID)


# ── list_event_attendees ────────────────────────────────────────────────────


class TestListEventAttendees:
    def test_404_when_event_missing(self, db, repos):
        a, e, _ = repos
        e.get_event_by_id.return_value = None
        with pytest.raises(HTTPException) as exc:
            att_service.list_event_attendees(
                db, EVENT_ID, HOST_ID, attendances=a, events=e
            )
        assert exc.value.status_code == 404

    def test_403_when_caller_not_host(self, db, repos):
        a, e, _ = repos
        with pytest.raises(HTTPException) as exc:
            att_service.list_event_attendees(
                db, EVENT_ID, "stranger", attendances=a, events=e
            )
        assert exc.value.status_code == 403

    def test_returns_rows_when_host(self, db, repos):
        a, e, _ = repos
        a.list_going_attendees_with_checkin.return_value = [
            {"user_id": USER_ID, "username": "alice", "checked_in_at": None},
        ]

        result = att_service.list_event_attendees(
            db, EVENT_ID, HOST_ID, attendances=a, events=e
        )
        assert len(result) == 1
        assert str(result[0].user_id) == USER_ID
