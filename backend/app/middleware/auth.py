from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.database import get_supabase
from app.services.auth import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """FastAPI dependency: extract and validate user_id from Bearer token, check active."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from err
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims",
        )
    # Check user exists and is active
    db = get_supabase()
    result = db.table("users").select("is_active").eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="User not found")
    if not result.data[0]["is_active"]:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    return user_id


def get_optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    db = get_supabase()
    result = db.table("users").select("is_active").eq("id", user_id).execute()
    if not result.data or not result.data[0]["is_active"]:
        return None
    return user_id


def require_role(*roles: str):
    """FastAPI dependency factory: require user to have one of the given roles."""

    def dependency(user_id: str = Depends(get_current_user_id)) -> str:
        db = get_supabase()
        result = db.table("users").select("role, is_active").eq("id", user_id).execute()
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        user = result.data[0]
        if not user["is_active"]:
            raise HTTPException(status_code=403, detail="Account is deactivated")
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user_id

    return dependency
