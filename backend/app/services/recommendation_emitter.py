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

from app.repositories import attendance as attendance_repo
from app.repositories import event as event_repo
from app.repositories import notification as notification_repo

logger = logging.getLogger(__name__)

# How many event_recommended notifications a user can receive in a 24h window.
MAX_RECOMMENDATIONS_PER_DAY = 3

# How far back we look for the user's attendance history when scoring matches.
ATTENDANCE_LOOKBACK_DAYS = 90


def emit_event_recommendations(db: Client, event_id: str, host_id: str) -> int:
    """Insert event_recommended notifications for users whose history matches.

    Returns the number of notifications inserted. Best-effort: callers should
    invoke this in a try/except and never let a failure block the publish path.
    """
    event = event_repo.get_event_by_id(db, event_id)
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

    candidate_ids = _find_candidates(db, category_ids, event_id, host_id)
    if not candidate_ids:
        return 0

    candidate_ids = _drop_users_already_engaged(db, candidate_ids, event_id)
    if not candidate_ids:
        return 0

    candidate_ids = _drop_users_over_daily_cap(db, candidate_ids)
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

    inserted = notification_repo.insert_notifications_bulk(db, rows)
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
    db: Client, category_ids: list[str], new_event_id: str, host_id: str,
) -> set[str]:
    """Users with going attendance on ended events that share at least one category."""
    # Step 1: events in any of these categories (exclude the new event itself)
    cat_rows = (
        db.table("event_categories")
        .select("event_id")
        .in_("category_id", category_ids)
        .execute()
    )
    overlap_event_ids = {row["event_id"] for row in (cat_rows.data or [])}
    overlap_event_ids.discard(new_event_id)
    if not overlap_event_ids:
        return set()

    # Step 2: filter to ended events within the lookback window
    cutoff = (datetime.now(UTC) - timedelta(days=ATTENDANCE_LOOKBACK_DAYS)).isoformat()
    ended_rows = (
        db.table("events")
        .select("id")
        .in_("id", list(overlap_event_ids))
        .eq("status", "ended")
        .gte("end_datetime", cutoff)
        .execute()
    )
    ended_event_ids = [row["id"] for row in (ended_rows.data or [])]
    if not ended_event_ids:
        return set()

    # Step 3: users who attended any of those ended events
    candidates = attendance_repo.find_users_going_on_events(db, ended_event_ids)
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


def _drop_users_over_daily_cap(db: Client, user_ids: set[str]) -> set[str]:
    """Skip users that already received MAX_RECOMMENDATIONS_PER_DAY today."""
    if not user_ids:
        return user_ids
    cutoff = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
    counts = notification_repo.count_by_type_for_users_since(
        db, list(user_ids), "event_recommended", cutoff,
    )
    return {uid for uid in user_ids if counts.get(uid, 0) < MAX_RECOMMENDATIONS_PER_DAY}


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
