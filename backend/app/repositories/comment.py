"""Comment repository — all database operations for comments."""

from supabase import Client


def insert_comment(db: Client, comment_data: dict) -> dict:
    result = db.table("comments").insert(comment_data).execute()
    return result.data[0] if result.data else None


def get_comments_by_event(
    db: Client, event_id: str, *, page: int = 1, page_size: int = 20
) -> tuple[list[dict], int]:
    query = (
        db.table("comments")
        .select("id,user_id,event_id,text,created_at,parent_id", count="exact")
        .eq("event_id", event_id)
    )
    offset = (page - 1) * page_size
    result = (
        query
        .order("created_at", desc=True)
        .range(offset, offset + page_size - 1)
        .execute()
    )
    return result.data or [], result.count or 0


def get_comment_by_id(db: Client, comment_id: str) -> dict | None:
    result = db.table("comments").select("id,user_id,event_id,text,created_at,parent_id").eq("id", comment_id).execute()
    return result.data[0] if result.data else None


def delete_comment(db: Client, comment_id: str) -> None:
    db.table("comments").delete().eq("id", comment_id).execute()


def get_user_by_id(db: Client, user_id: str) -> dict | None:
    result = db.table("users").select("id, username").eq("id", user_id).execute()
    return result.data[0] if result.data else None


def get_users_by_ids(db: Client, user_ids: list[str]) -> dict[str, dict]:
    if not user_ids:
        return {}
    result = (
        db.table("users")
        .select("id, username")
        .in_("id", user_ids)
        .execute()
    )
    return {row["id"]: row for row in (result.data or [])}
