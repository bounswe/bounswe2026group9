"""Event recommendation notifications.

When a host publishes a public event, find users whose past attendance pattern
(category overlap on `going` status of `ended` events) matches the new event,
and emit `event_recommended` notifications to them.

Privacy / safety guarantees:
  - Private events never produce recommendations
  - Cancelled / ended / draft / updated events never trigger this emitter
  - The host of the event is never recommended their own event
  - Users who already bookmarked or are going on the new event are skipped
    (they will get the regular update channel instead)
  - Per-user daily cap (default 3) prevents notification fatigue
"""

import logging
from datetime import UTC, datetime, timedelta

from supabase import Client

from app.repositories import attendance as _attendance_repo
from app.repositories import event as _event_repo
from app.repositories import notification as _notification_repo
from app.repositories.protocols import (
    AttendanceRepoProtocol,
    EventRepoProtocol,
    NotificationRepoProtocol,
)
from app.services.category_clusters import expand_category_ids

logger = logging.getLogger(__name__)

# How many event_recommended notifications a user can receive in a 24h window.
MAX_RECOMMENDATIONS_PER_DAY = 3

# How far back we look for the user's attendance history when scoring matches.
ATTENDANCE_LOOKBACK_DAYS = 90

# PostgREST encodes .in_() as a URL query param; keep chunks small enough to
# stay well under the ~8 KB URL limit (36 chars per UUID + overhead).
_IN_CHUNK_SIZE = 100


def emit_event_recommendations(
    db: Client,
    event_id: str,
    host_id: str,
    *,
    events: EventRepoProtocol = _event_repo,
    attendances: AttendanceRepoProtocol = _attendance_repo,
    notifications: NotificationRepoProtocol = _notification_repo,
) -> int:
    """Insert event_recommended notifications for users whose history matches.

    Returns the number of notifications inserted. Best-effort: callers should
    invoke this in a try/except and never let a failure block the publish path.

    Helper functions still query Supabase directly through `db.table(...)`;
    extracting those into repository methods is queued for a follow-up so we
    can ship DI for the public surface without doubling the diff. Existing
    integration coverage in `tests/test_recommendation_emitter.py` exercises
    the end-to-end behaviour.
    """
    event = events.get_event_by_id(db, event_id)
    if not event:
        return 0

    # Only public, currently-active events get recommendations
    if event.get("visibility") != "public":
        return 0
    if event.get("status") not in ("published", "updated"):
        return 0

    category_ids = _get_event_category_ids(db, event_id)
    if not category_ids:
        return 0

    candidate_ids = _find_candidates(db, category_ids, event_id, host_id, attendances)
    if not candidate_ids:
        return 0

    candidate_ids = _drop_users_already_engaged(db, candidate_ids, event_id)
    if not candidate_ids:
        return 0

    candidate_ids = _drop_users_already_notified(db, candidate_ids, event_id)
    if not candidate_ids:
        return 0

    candidate_ids = _drop_users_over_daily_cap(db, candidate_ids, notifications)
    if not candidate_ids:
        return 0

    message = _build_message(db, category_ids, event["title"])
    rows = [
        {
            "user_id": uid,
            "event_id": event_id,
            "type": "event_recommended",
            "message": message,
            "is_read": False,
        }
        for uid in candidate_ids
    ]

    inserted = notifications.insert_notifications_bulk(db, rows)
    return len(inserted)


# ── helpers ────────────────────────────────────────────────────────────────

def _get_event_category_ids(db: Client, event_id: str) -> list[str]:
    result = (
        db.table("event_categories")
        .select("category_id")
        .eq("event_id", event_id)
        .execute()
    )
    return [row["category_id"] for row in (result.data or [])]


def _find_candidates(
    db: Client,
    category_ids: list[str],
    new_event_id: str,
    host_id: str,
    attendances: AttendanceRepoProtocol,
) -> set[str]:
    """Users with going attendance on ended events that share at least one category
    (exact match or cluster-similar category)."""
    # Expand exact category IDs to include cluster-similar categories so that,
    # e.g., a Sports event also reaches Health & Wellness / Outdoor attendees.
    expanded_ids = expand_category_ids(db, set(category_ids))

    # Step 1: events in any of these categories (exclude the new event itself)
    cat_rows = (
        db.table("event_categories")
        .select("event_id")
        .in_("category_id", list(expanded_ids))
        .execute()
    )
    overlap_event_ids = {row["event_id"] for row in (cat_rows.data or [])}
    overlap_event_ids.discard(new_event_id)
    if not overlap_event_ids:
        return set()

    # Step 2: filter to ended events within the lookback window.
    # Chunk to avoid PostgREST URL-length limits on large .in_() lists.
    cutoff = (datetime.now(UTC) - timedelta(days=ATTENDANCE_LOOKBACK_DAYS)).isoformat()
    overlap_list = list(overlap_event_ids)
    ended_event_ids: list[str] = []
    for i in range(0, len(overlap_list), _IN_CHUNK_SIZE):
        chunk = overlap_list[i:i + _IN_CHUNK_SIZE]
        rows = (
            db.table("events")
            .select("id")
            .in_("id", chunk)
            .eq("status", "ended")
            .gte("end_datetime", cutoff)
            .execute()
        )
        ended_event_ids.extend(row["id"] for row in (rows.data or []))
    if not ended_event_ids:
        return set()

    # Step 3: users who attended any of those ended events
    candidates = attendances.find_users_going_on_events(db, ended_event_ids)
    candidates.discard(host_id)
    return candidates


def _drop_users_already_engaged(
    db: Client, user_ids: set[str], event_id: str,
) -> set[str]:
    """Skip users who already bookmarked or are going on the new event."""
    if not user_ids:
        return user_ids

    user_id_list = list(user_ids)
    bookmark_rows = (
        db.table("bookmarks")
        .select("user_id")
        .eq("event_id", event_id)
        .in_("user_id", user_id_list)
        .execute()
    )
    attendance_rows = (
        db.table("attendances")
        .select("user_id")
        .eq("event_id", event_id)
        .in_("user_id", user_id_list)
        .execute()
    )
    engaged = {row["user_id"] for row in (bookmark_rows.data or [])}
    engaged.update(row["user_id"] for row in (attendance_rows.data or []))
    return user_ids - engaged


def _drop_users_over_daily_cap(
    db: Client,
    user_ids: set[str],
    notifications: NotificationRepoProtocol,
) -> set[str]:
    """Skip users that already received MAX_RECOMMENDATIONS_PER_DAY today."""
    if not user_ids:
        return user_ids
    cutoff = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
    counts = notifications.count_by_type_for_users_since(
        db, list(user_ids), "event_recommended", cutoff,
    )
    return {uid for uid in user_ids if counts.get(uid, 0) < MAX_RECOMMENDATIONS_PER_DAY}


def _drop_users_already_notified(
    db: Client, user_ids: set[str], event_id: str,
) -> set[str]:
    """Skip users who already have an event_recommended notification for this event."""
    if not user_ids:
        return user_ids
    result = (
        db.table("notifications")
        .select("user_id")
        .eq("event_id", event_id)
        .eq("type", "event_recommended")
        .in_("user_id", list(user_ids))
        .execute()
    )
    already_notified = {row["user_id"] for row in (result.data or [])}
    return user_ids - already_notified


def _build_message(db: Client, category_ids: list[str], event_title: str) -> str:
    """Use the first matching category name to build a human-readable reason."""
    first_id = category_ids[0]
    cat_row = (
        db.table("categories")
        .select("name")
        .eq("id", first_id)
        .limit(1)
        .execute()
    )
    if cat_row.data:
        return f"New event '{event_title}' — based on events you attended in {cat_row.data[0]['name']}"
    return f"New event '{event_title}' might match your interests"
