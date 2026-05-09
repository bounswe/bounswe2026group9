"""Structured (JSON-line) logging for the backend.

Issue #152 / NFR-07 calls for "structured logging for key actions
(publish, update, cancel, delete) and errors with timestamp, event ID,
and user ID". Bare ``logger.info("Cancelled %s", event_id)`` lines
satisfy *some* of that, but they're hard to filter and aggregate. This
module installs a JSON formatter so every record is a single line of
machine-parseable JSON with stable field names.

Why a custom formatter, not ``python-json-logger``
==================================================

We could pull in another dependency, but the formatter is small enough
(~30 lines) that the maintenance cost of a third-party shim is higher
than the cost of owning it. Stable field names matter more than the
implementation details, and pinning them in our own code lets us
evolve the format on our schedule.

Field contract
==============

Every record carries at minimum:

  - ``timestamp`` — ISO-8601 UTC with millisecond precision
  - ``level``     — DEBUG / INFO / WARNING / ERROR
  - ``logger``    — the dotted name (``app.services.event``, …)
  - ``message``   — the formatted message string

Records emitted from ``log_action`` / ``log_error`` carry additional
top-level fields rather than nesting them under ``extra``:

  - ``action``    — short verb (e.g. ``event.publish``)
  - ``event_id``  — UUID, if applicable
  - ``user_id``   — UUID of the actor
  - ``error``     — exception class name (only on errors)

Anything else passed to ``logger.info(..., extra={"key": "value"})``
is also flattened to the top level.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

# Reserved attribute names on a ``logging.LogRecord`` — we never copy
# these into the JSON output (they're internal state).
_RESERVED = frozenset({
    "args", "asctime", "created", "exc_info", "exc_text", "filename",
    "funcName", "levelname", "levelno", "lineno", "message", "module",
    "msecs", "msg", "name", "pathname", "process", "processName",
    "relativeCreated", "stack_info", "thread", "threadName", "taskName",
})


class JsonFormatter(logging.Formatter):
    """Render each ``LogRecord`` as a single JSON line.

    Top-level fields: ``timestamp``, ``level``, ``logger``, ``message``,
    plus any non-reserved attribute the caller attached via ``extra=``.
    Exception info, if present, is flattened to ``error`` (class name) and
    ``error_detail`` (formatted traceback).
    """

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds")
        payload: dict[str, Any] = {
            "timestamp": ts,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Non-reserved attributes — these are the keys callers set via
        # ``logger.info("...", extra={"event_id": ...})``.
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            exc_type, exc_value, _ = record.exc_info
            payload["error"] = exc_type.__name__ if exc_type else "Exception"
            payload["error_detail"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)


def configure(level: int | str = logging.INFO) -> None:
    """Install the JSON formatter on the root logger.

    Idempotent — repeated calls replace the existing handlers, which
    matters for the tests that patch logging mid-session.
    """
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    # Quiet a couple of noisy third-party loggers we don't own.
    for name in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)


def log_action(
    logger: logging.Logger,
    action: str,
    *,
    event_id: str | None = None,
    user_id: str | None = None,
    **fields: Any,
) -> None:
    """Emit a structured INFO record for a key business action.

    Use sparingly — only the events the operator wants to see in
    production logs (publish / update / cancel / delete are the
    canonical four for issue #152 / NFR-07).
    """
    extra = {"action": action, **fields}
    if event_id is not None:
        extra["event_id"] = event_id
    if user_id is not None:
        extra["user_id"] = user_id
    # Pass `extra=...` so the record carries the fields as attributes
    # the JsonFormatter picks up — formatted via `getMessage()` would
    # not work because we want them as separate top-level keys.
    logger.info(action, extra=extra)


def log_error(
    logger: logging.Logger,
    action: str,
    *,
    event_id: str | None = None,
    user_id: str | None = None,
    exc_info: bool = True,
    **fields: Any,
) -> None:
    """Emit a structured ERROR record. ``exc_info=True`` captures the
    current exception's type + traceback into ``error`` / ``error_detail``."""
    extra = {"action": action, **fields}
    if event_id is not None:
        extra["event_id"] = event_id
    if user_id is not None:
        extra["user_id"] = user_id
    logger.error(action, extra=extra, exc_info=exc_info)
