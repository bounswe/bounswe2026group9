"""Attendance repository — database operations for event attendance."""

from supabase import Client


def get_attendance(db: Client, user_id: str, event_id: str) -> dict | None:
    result = (
        db.table("attendances")
        .select("*")
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


def delete_attendance(db: Client, user_id: str, event_id: str) -> None:
    db.table("attendances").delete().eq("user_id", user_id).eq("event_id", event_id).execute()


def get_interested_count_for_event(db: Client, event_id: str) -> int:
    result = (
        db.table("attendances")
        .select("*", count="exact")
        .eq("event_id", event_id)
        .eq("status", "interested")
        .execute()
    )
    return result.count or 0


def get_interested_counts_for_events(db: Client, event_ids: list[str]) -> dict[str, int]:
    if not event_ids:
        return {}

    result = (
        db.table("attendances")
        .select("event_id")
        .in_("event_id", event_ids)
        .eq("status", "interested")
        .execute()
    )

    counts = {eid: 0 for eid in event_ids}
    for row in (result.data or []):
        counts[row["event_id"]] += 1
    return counts


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
