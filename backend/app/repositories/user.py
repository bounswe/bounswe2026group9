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


def get_user_date_of_birth(db: Client, user_id: str) -> str | None:
    result = db.table("users").select("date_of_birth").eq("id", user_id).execute()
    if not result.data:
        return None
    return result.data[0].get("date_of_birth")
