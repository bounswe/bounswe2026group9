import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.config import settings
from app.database import get_supabase

# --- Password ---


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# --- JWT ---


def create_access_token(user_id: str, email: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """Decode and validate access token. Raises JWTError on failure."""
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload


# --- Refresh Token ---


def generate_refresh_token() -> str:
    """Generate a secure random refresh token (32 bytes, base64url)."""
    return secrets.token_urlsafe(32)


def store_refresh_token(user_id: str, token: str) -> None:
    db = get_supabase()
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    db.table("refresh_tokens").insert({
        "user_id": user_id,
        "token": token,
        "expires_at": expires_at.isoformat(),
    }).execute()


def validate_refresh_token(token: str) -> str | None:
    """Validate refresh token. Returns user_id if valid, None otherwise."""
    db = get_supabase()
    result = (
        db.table("refresh_tokens")
        .select("user_id, expires_at, revoked")
        .eq("token", token)
        .execute()
    )
    if not result.data:
        return None
    row = result.data[0]
    if row["revoked"]:
        return None
    if datetime.fromisoformat(row["expires_at"]) < datetime.now(UTC):
        return None
    return row["user_id"]


def revoke_refresh_token(token: str) -> None:
    db = get_supabase()
    db.table("refresh_tokens").update({"revoked": True}).eq("token", token).execute()


def revoke_all_user_tokens(user_id: str) -> None:
    db = get_supabase()
    db.table("refresh_tokens").update({"revoked": True}).eq("user_id", user_id).execute()


# --- Account Lockout ---

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def check_account_locked(user: dict) -> tuple[bool, str | None]:
    """Returns (is_locked, lock_message)."""
    locked_until = user.get("locked_until")
    if not locked_until:
        return False, None
    lock_time = datetime.fromisoformat(locked_until)
    if lock_time > datetime.now(UTC):
        remaining = int((lock_time - datetime.now(UTC)).total_seconds() / 60) + 1
        return True, f"Account locked. Try again in {remaining} minutes."
    return False, None


def increment_failed_attempts(user_id: str, current_attempts: int) -> None:
    db = get_supabase()
    new_count = current_attempts + 1
    update_data: dict = {"failed_login_attempts": new_count}
    if new_count >= MAX_FAILED_ATTEMPTS:
        lock_until = datetime.now(UTC) + timedelta(minutes=LOCKOUT_MINUTES)
        update_data["locked_until"] = lock_until.isoformat()
    db.table("users").update(update_data).eq("id", user_id).execute()


def reset_failed_attempts(user_id: str) -> None:
    db = get_supabase()
    db.table("users").update({
        "failed_login_attempts": 0,
        "locked_until": None,
    }).eq("id", user_id).execute()
