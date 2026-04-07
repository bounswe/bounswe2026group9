"""Attendance repository — database operations for event attendance."""

from supabase import Client


def get_attendance(db: Client, user_id: str, event_id: str) -> dict | None:
    result = (
        db.table("attendances")
        .select("id,user_id,event_id,status,marked_at")
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
