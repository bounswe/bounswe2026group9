"""User repository — database operations for users."""

from supabase import Client


def get_user_by_id(db: Client, user_id: str) -> dict | None:
    result = db.table("users").select("id,username,is_active").eq("id", user_id).execute()
    return result.data[0] if result.data else None


def get_user_email_by_id(db: Client, user_id: str) -> str | None:
    result = db.table("users").select("email").eq("id", user_id).execute()
    if not result.data:
        return None
    return result.data[0].get("email")


def get_user_date_of_birth(db: Client, user_id: str) -> str | None:
    result = db.table("users").select("date_of_birth").eq("id", user_id).execute()
    if not result.data:
        return None
    return result.data[0].get("date_of_birth")
