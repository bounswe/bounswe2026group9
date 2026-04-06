"""Profile repository — database operations for user profiles."""

from fastapi import HTTPException
from supabase import Client

from app.repositories.user import USER_SAFE_COLS


def get_full_user_profile(db: Client, user_id: str) -> dict | None:
    result = (
        db.table("users")
        .select(USER_SAFE_COLS)
        .eq("id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


def update_user_profile(db: Client, user_id: str, data: dict) -> dict:
    result = (
        db.table("users")
        .update(data)
        .eq("id", user_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update profile")
    return result.data[0]


_EVENT_COLS = (
    "id,host_id,title,description,start_datetime,end_datetime,"
    "visibility,is_age_restricted,attendee_limit,attendee_count,"
    "status,created_at,updated_at"
)


def get_hosted_events(db: Client, user_id: str, include_drafts: bool = False) -> list[dict]:
    query = (
        db.table("events")
        .select(_EVENT_COLS)
        .eq("host_id", user_id)
    )

    if not include_drafts:
        query = query.neq("status", "draft")

    result = query.order("start_datetime", desc=False).execute()
    return result.data or []
