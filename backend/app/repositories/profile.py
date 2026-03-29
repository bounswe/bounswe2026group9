"""Profile repository — database operations for user profiles."""

from fastapi import HTTPException
from supabase import Client


def get_full_user_profile(db: Client, user_id: str) -> dict | None:
    result = (
        db.table("users")
        .select("*")
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


def get_hosted_events(db: Client, user_id: str) -> list[dict]:
    # all events except drafts
    result = (
        db.table("events")
        .select("*")
        .eq("host_id", user_id)
        .neq("status", "draft")
        .order("start_datetime", desc=False)
        .execute()
    )
    return result.data or []
