"""Attendance repository — database operations for event attendance."""

from supabase import Client


def get_attendance(db: Client, user_id: str, event_id: str) -> dict | None:
    result = (
        db.table("attendances")
        .select("id,user_id,event_id,status,marked_at,check_in_token,checked_in_at")
        .eq("user_id", user_id)
        .eq("event_id", event_id)
        .execute()
    )
    return result.data[0] if result.data else None


def insert_attendance(db: Client, data: dict) -> dict:
    result = db.table("attendances").insert(data).execute()
    return result.data[0]


def update_attendance(db: Client, user_id: str, event_id: str, status: str) -> dict:
    result = (
        db.table("attendances")
        .update({"status": status, "marked_at": "now()"})
        .eq("user_id", user_id)
        .eq("event_id", event_id)
        .execute()
    )
    return result.data[0]


def update_attendance_token(db: Client, user_id: str, event_id: str, token: str | None) -> dict:
    """Set or clear the check-in token for an attendance record."""
    result = (
        db.table("attendances")
        .update({"check_in_token": token})
        .eq("user_id", user_id)
        .eq("event_id", event_id)
        .execute()
    )
    return result.data[0]


def delete_attendance(db: Client, user_id: str, event_id: str) -> None:
    db.table("attendances").delete().eq("user_id", user_id).eq("event_id", event_id).execute()


def get_attendance_by_token(db: Client, token: str) -> dict | None:
    """Look up an attendance record by its check-in token."""
    result = (
        db.table("attendances")
        .select("id,user_id,event_id,status,marked_at,check_in_token,checked_in_at")
        .eq("check_in_token", token)
        .execute()
    )
    return result.data[0] if result.data else None


def mark_checked_in(db: Client, attendance_id: str) -> dict:
    """Set checked_in_at = now() for the given attendance row."""
    result = (
        db.table("attendances")
        .update({"checked_in_at": "now()"})
        .eq("id", attendance_id)
        .execute()
    )
    return result.data[0]


def list_going_attendees_with_checkin(db: Client, event_id: str) -> list[dict]:
    """Return all going attendees for the event, with their check-in status.

    Joins with users to get usernames.
    """
    result = (
        db.table("attendances")
        .select("user_id,checked_in_at,users!inner(username)")
        .eq("event_id", event_id)
        .eq("status", "going")
        .order("marked_at")
        .execute()
    )
    rows = []
    for row in (result.data or []):
        rows.append({
            "user_id": row["user_id"],
            "username": row["users"]["username"],
            "checked_in_at": row["checked_in_at"],
        })
    return rows


def get_going_user_ids_for_event(db: Client, event_id: str) -> list[str]:
    result = (
        db.table("attendances")
        .select("user_id")
        .eq("event_id", event_id)
        .eq("status", "going")
        .order("marked_at")
        .execute()
    )
    return [row["user_id"] for row in (result.data or [])]


def get_attendance_status_for_events(db: Client, user_id: str, event_ids: list[str]) -> dict[str, str]:
    if not event_ids:
        return {}

    result = (
        db.table("attendances")
        .select("event_id, status")
        .eq("user_id", user_id)
        .in_("event_id", event_ids)
        .execute()
    )

    return {row["event_id"]: row["status"] for row in (result.data or [])}


def has_attended_ended_event_by_host(db: Client, user_id: str, host_id: str) -> bool:
    """Returns True if user_id has a 'going' attendance on at least one ended event hosted by host_id."""
    result = (
        db.table("attendances")
        .select("event_id, events!inner(host_id, status)")
        .eq("user_id", user_id)
        .eq("status", "going")
        .eq("events.host_id", host_id)
        .eq("events.status", "ended")
        .limit(1)
        .execute()
    )
    return bool(result.data)


_IN_CHUNK_SIZE = 100


def find_users_going_on_events(db: Client, event_ids: list[str]) -> set[str]:
    """Return user_ids that have status='going' on any of event_ids."""
    if not event_ids:
        return set()
    users: set[str] = set()
    for i in range(0, len(event_ids), _IN_CHUNK_SIZE):
        chunk = event_ids[i:i + _IN_CHUNK_SIZE]
        result = (
            db.table("attendances")
            .select("user_id")
            .in_("event_id", chunk)
            .eq("status", "going")
            .execute()
        )
        users.update(row["user_id"] for row in (result.data or []))
    return users


def get_going_event_ids_for_user(db: Client, user_id: str) -> list[str]:
    """Return event_ids where the user has status='going', ordered by marked_at desc."""
    result = (
        db.table("attendances")
        .select("event_id")
        .eq("user_id", user_id)
        .eq("status", "going")
        .order("marked_at", desc=True)
        .execute()
    )
    return [row["event_id"] for row in (result.data or [])]


def get_attended_ended_event_categories(db: Client, user_id: str) -> set[str]:
    """Return the set of category_ids for events the user attended (status='going')
    on events whose status='ended'. Used to bias the Discovery listing.

    Returns empty set if the user has no qualifying attendance history.
    """
    # Step 1: ended events the user was 'going' to
    att_rows = (
        db.table("attendances")
        .select("event_id, events!inner(status)")
        .eq("user_id", user_id)
        .eq("status", "going")
        .eq("events.status", "ended")
        .execute()
    )
    event_ids = [row["event_id"] for row in (att_rows.data or [])]
    if not event_ids:
        return set()

    # Step 2: collect category_ids for those events — chunk to avoid URL limits.
    categories: set[str] = set()
    for i in range(0, len(event_ids), _IN_CHUNK_SIZE):
        chunk = event_ids[i:i + _IN_CHUNK_SIZE]
        cat_rows = (
            db.table("event_categories")
            .select("category_id")
            .in_("event_id", chunk)
            .execute()
        )
        categories.update(row["category_id"] for row in (cat_rows.data or []))
    return categories
