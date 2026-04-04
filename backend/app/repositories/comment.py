"""Comment repository — all database operations for comments."""

from supabase import Client


def insert_comment(db: Client, comment_data: dict) -> dict:
    result = db.table("comments").insert(comment_data).execute()
    return result.data[0] if result.data else None


def get_comments_by_event(
    db: Client, event_id: str, *, page: int = 1, page_size: int = 20
) -> tuple[list[dict], int]:
    """Fetch root comments (paginated) and all their descendants for tree building."""
    # Count only root comments for pagination
    root_count_result = (
        db.table("comments")
        .select("id", count="exact")
        .eq("event_id", event_id)
        .is_("parent_id", "null")
        .execute()
    )
    total = root_count_result.count or 0

    # Fetch paginated root comments
    offset = (page - 1) * page_size
    root_result = (
        db.table("comments")
        .select("id,user_id,event_id,text,created_at,parent_id")
        .eq("event_id", event_id)
        .is_("parent_id", "null")
        .order("created_at", desc=True)
        .range(offset, offset + page_size - 1)
        .execute()
    )
    roots = root_result.data or []
    if not roots:
        return [], total

    # Fetch all descendants for these roots (all comments with parent_id != null for this event)
    children_result = (
        db.table("comments")
        .select("id,user_id,event_id,text,created_at,parent_id")
        .eq("event_id", event_id)
        .not_.is_("parent_id", "null")
        .order("created_at")
        .execute()
    )
    children = children_result.data or []

    return roots + children, total


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
