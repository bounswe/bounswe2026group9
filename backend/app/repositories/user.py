"""User repository — database operations for users."""

from supabase import Client

# Safe column list for user-facing queries — excludes hashed_password, google_id, locked_until, failed_login_attempts
USER_SAFE_COLS = (
    "id,username,email,phone_number,date_of_birth,"
    "email_visibility,phone_visibility,"
    "role,auth_provider,email_verified,is_active,"
    "created_at,updated_at"
)

# Columns needed for login (includes sensitive fields for auth checks)
USER_AUTH_COLS = f"{USER_SAFE_COLS},hashed_password,google_id,failed_login_attempts,locked_until"


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


def get_users_by_ids(db: Client, user_ids: list[str]) -> list[dict]:
    if not user_ids:
        return []

    result = db.table("users").select("id,username").in_("id", user_ids).execute()
    return result.data or []


def get_user_default_area(
    db: Client, user_id: str,
) -> tuple[float | None, float | None]:
    """Return (lat, lng) of the user's saved default area, or (None, None) if unset."""
    result = (
        db.table("users")
        .select("default_location_lat,default_location_lng")
        .eq("id", user_id)
        .execute()
    )
    row = result.data[0] if result.data else {}
    return (row.get("default_location_lat"), row.get("default_location_lng"))
