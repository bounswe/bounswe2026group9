"""Bookmark repository — database operations for bookmarks."""

from supabase import Client


def get_bookmark(db: Client, user_id: str, event_id: str) -> dict | None:
    result = (
        db.table("bookmarks")
        .select("id,user_id,event_id,created_at")
        .eq("user_id", user_id)
        .eq("event_id", event_id)
        .execute()
    )
    return result.data[0] if result.data else None


def insert_bookmark(db: Client, data: dict) -> dict:
    result = db.table("bookmarks").insert(data).execute()
    return result.data[0]


def delete_bookmark(db: Client, user_id: str, event_id: str) -> None:
    db.table("bookmarks").delete().eq("user_id", user_id).eq("event_id", event_id).execute()


def get_bookmarks_by_user(
    db: Client, user_id: str, *, page: int = 1, page_size: int = 20
) -> tuple[list[dict], int]:
    query = (
        db.table("bookmarks")
        .select("id,user_id,event_id,created_at", count="exact")
        .eq("user_id", user_id)
    )
    offset = (page - 1) * page_size
    result = (
        query
        .order("created_at", desc=True)
        .range(offset, offset + page_size - 1)
        .execute()
    )
    return result.data or [], result.count or 0


def get_bookmark_count_for_event(db: Client, event_id: str) -> int:
    result = (
        db.table("bookmarks")
        .select("id", count="exact")
        .eq("event_id", event_id)
        .execute()
    )
    return result.count or 0


def get_bookmark_counts_for_events(db: Client, event_ids: list[str]) -> dict[str, int]:
    if not event_ids:
        return {}
    result = (
        db.table("bookmarks")
        .select("event_id")
        .in_("event_id", event_ids)
        .execute()
    )
    counts = {eid: 0 for eid in event_ids}
    for row in (result.data or []):
        counts[row["event_id"]] += 1
    return counts


def get_bookmark_status_for_events(
    db: Client, user_id: str, event_ids: list[str]
) -> set[str]:
    """Return set of event_ids that the user has bookmarked."""
    if not event_ids:
        return set()
    result = (
        db.table("bookmarks")
        .select("event_id")
        .eq("user_id", user_id)
        .in_("event_id", event_ids)
        .execute()
    )
    return {row["event_id"] for row in (result.data or [])}
