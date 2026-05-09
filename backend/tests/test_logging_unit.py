"""Unit tests for the structured logging surface (NFR-07).

Issue #152's first deliverable is "structured logging for key actions
(publish, update, cancel, delete) and errors with timestamp, event_id,
and user_id". The five tests below pin:

  1. JsonFormatter emits a single JSON line with the required top-level
     fields and any extras the caller attached.
  2. log_action / log_error attach event_id and user_id as top-level
     fields rather than nesting them under ``extra``.
  3. The four service functions (create / update / change_status /
     delete) emit a structured INFO record with the right action verb.

The service-side checks drive the real services with mocks so we
exercise the actual code path the production logger sees, not a
hand-rolled record.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.logging_config import JsonFormatter, log_action, log_error


@pytest.fixture
def db() -> MagicMock:
    """Override the conftest session-scoped ``db`` so this file doesn't
    contact a real Supabase. The autouse ``cleanup_test_users`` fixture
    requests ``db`` and would otherwise resolve the real client at
    ``SUPABASE_URL=fake``, which fails before any test runs."""
    return MagicMock(name="supabase_client")


# ── JsonFormatter contract ─────────────────────────────────────────────────


def _format_record(record: logging.LogRecord) -> dict:
    formatter = JsonFormatter()
    line = formatter.format(record)
    return json.loads(line)


def test_formatter_emits_required_top_level_fields() -> None:
    record = logging.LogRecord(
        name="app.services.event",
        level=logging.INFO,
        pathname="event.py",
        lineno=42,
        msg="event.publish",
        args=(),
        exc_info=None,
    )
    record.event_id = "00000000-0000-0000-0000-0000000000a1"
    record.user_id = "00000000-0000-0000-0000-0000000000a2"
    record.action = "event.publish"

    payload = _format_record(record)

    assert set(payload).issuperset({"timestamp", "level", "logger", "message"})
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.services.event"
    assert payload["event_id"] == record.event_id
    assert payload["user_id"] == record.user_id
    assert payload["action"] == "event.publish"
    # Timestamp is ISO-8601 UTC.
    datetime.fromisoformat(payload["timestamp"])


def test_formatter_attaches_exception_info_when_present() -> None:
    try:
        raise ValueError("synthetic")
    except ValueError:
        import sys

        record = logging.LogRecord(
            name="app",
            level=logging.ERROR,
            pathname="x.py",
            lineno=1,
            msg="boom",
            args=(),
            exc_info=sys.exc_info(),
        )

    payload = _format_record(record)
    assert payload["error"] == "ValueError"
    assert "synthetic" in payload["error_detail"]


# ── log_action / log_error helpers ─────────────────────────────────────────


def test_log_action_attaches_event_id_user_id_as_top_level_fields(caplog) -> None:
    logger = logging.getLogger("app.test.helpers")
    with caplog.at_level(logging.INFO, logger="app.test.helpers"):
        log_action(
            logger, "event.publish",
            event_id="evt-1", user_id="usr-1",
            visibility="public",
        )

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.action == "event.publish"
    assert record.event_id == "evt-1"
    assert record.user_id == "usr-1"
    assert record.visibility == "public"


def test_log_error_captures_current_exception(caplog) -> None:
    logger = logging.getLogger("app.test.helpers")
    with caplog.at_level(logging.ERROR, logger="app.test.helpers"):
        try:
            raise RuntimeError("bang")
        except RuntimeError:
            log_error(
                logger, "event.recommendation_emit_failed",
                event_id="evt-1", user_id="usr-1",
            )

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelname == "ERROR"
    assert record.action == "event.recommendation_emit_failed"
    assert record.exc_info is not None
    assert record.exc_info[0] is RuntimeError


# ── Service-side action emission ───────────────────────────────────────────


def _stub_event(**overrides) -> dict:
    base = {
        "id": "00000000-0000-0000-0000-0000000000a1",
        "host_id": "00000000-0000-0000-0000-0000000000a2",
        "title": "Logged event",
        "description": "desc",
        "start_datetime": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
        "end_datetime": (datetime.now(UTC) + timedelta(hours=26)).isoformat(),
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


def test_change_event_status_logs_publish_action(caplog, monkeypatch) -> None:
    """draft → published flips action verb to ``event.publish``."""
    from app.services import event as event_service

    db = MagicMock()
    monkeypatch.setattr(
        event_service.event_repo,
        "get_event_by_id",
        lambda *a, **k: _stub_event(status="draft"),
    )
    monkeypatch.setattr(
        event_service.event_repo,
        "get_event_locations",
        lambda *a, **k: [{"id": "loc1"}],
    )
    monkeypatch.setattr(
        event_service.event_repo,
        "get_event_categories",
        lambda *a, **k: [{"id": "cat1"}],
    )
    monkeypatch.setattr(
        event_service.event_repo,
        "get_event_images",
        lambda *a, **k: [{"id": "img1"}],
    )
    # _parse_stored_datetime path needs a future start to allow publish.
    monkeypatch.setattr(
        event_service,
        "_parse_stored_datetime",
        lambda v: datetime.now(UTC) + timedelta(hours=24),
    )
    update_calls: list[tuple] = []
    monkeypatch.setattr(
        event_service.event_repo,
        "update_event_status",
        lambda *a, **k: update_calls.append((a, k)),
    )
    # No-op the recommendation emitter import path + downstream get_event_detail.
    monkeypatch.setattr(event_service, "get_event_detail", lambda *a, **k: object())

    import app.services.recommendation_emitter as rec_module

    monkeypatch.setattr(
        rec_module, "emit_event_recommendations", lambda *a, **k: 0,
    )

    with caplog.at_level(logging.INFO, logger="app.services.event"):
        event_service.change_event_status(
            db, "00000000-0000-0000-0000-0000000000a1",
            "00000000-0000-0000-0000-0000000000a2",
            "published",
        )

    actions = [
        getattr(r, "action", None)
        for r in caplog.records
        if r.name == "app.services.event"
    ]
    assert "event.publish" in actions
    publish = next(
        r for r in caplog.records
        if getattr(r, "action", None) == "event.publish"
    )
    assert publish.event_id == "00000000-0000-0000-0000-0000000000a1"
    assert publish.user_id == "00000000-0000-0000-0000-0000000000a2"
    assert publish.previous_status == "draft"
    assert publish.new_status == "published"


def test_delete_event_logs_event_delete_action(caplog, monkeypatch) -> None:
    from app.services import event as event_service

    db = MagicMock()
    monkeypatch.setattr(
        event_service.event_repo,
        "get_event_by_id",
        lambda *a, **k: _stub_event(status="cancelled"),
    )
    monkeypatch.setattr(event_service.event_repo, "delete_event", lambda *a, **k: None)
    monkeypatch.setattr(
        event_service.image_repo, "get_all_event_images", lambda *a, **k: [],
    )

    import app.services.notification_emitter as notif

    monkeypatch.setattr(
        notif, "emit_event_notification", lambda *a, **k: 0,
    )

    with caplog.at_level(logging.INFO, logger="app.services.event"):
        event_service.delete_event(
            db, "00000000-0000-0000-0000-0000000000a1",
            "00000000-0000-0000-0000-0000000000a2",
        )

    actions = [
        getattr(r, "action", None)
        for r in caplog.records
        if r.name == "app.services.event"
    ]
    assert "event.delete" in actions
    rec = next(
        r for r in caplog.records
        if getattr(r, "action", None) == "event.delete"
    )
    assert rec.event_id == "00000000-0000-0000-0000-0000000000a1"
    assert rec.user_id == "00000000-0000-0000-0000-0000000000a2"
    assert rec.previous_status == "cancelled"


def test_change_event_status_rejects_invalid_transition(caplog, monkeypatch) -> None:
    """The 400 path must not emit a success action — the structured log
    is only for the ``did happen`` side, not for validation rejections."""
    from app.services import event as event_service

    db = MagicMock()
    monkeypatch.setattr(
        event_service.event_repo,
        "get_event_by_id",
        lambda *a, **k: _stub_event(status="draft"),
    )

    with caplog.at_level(logging.INFO, logger="app.services.event"):
        with pytest.raises(HTTPException) as exc:
            event_service.change_event_status(
                db, "evt", "00000000-0000-0000-0000-0000000000a2", "cancelled",
            )

    assert exc.value.status_code == 400
    actions = [
        getattr(r, "action", None)
        for r in caplog.records
        if r.name == "app.services.event"
    ]
    assert not any(a and a.startswith("event.") for a in actions)
