from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Response, Request, Depends
from starlette.responses import RedirectResponse

from app.config import settings
from app.database import get_supabase
from app.models.user import (
    UserRegisterRequest,
    UserLoginRequest,
    RefreshTokenRequest,
    UserResponse,
    AuthResponse,
    MessageResponse,
)
from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    generate_refresh_token,
    store_refresh_token,
    validate_refresh_token,
    revoke_refresh_token,
    check_account_locked,
    increment_failed_attempts,
    reset_failed_attempts,
)
from app.services.oauth import (
    generate_oauth_state,
    build_google_auth_url,
    exchange_code_for_tokens,
    get_google_user_info,
)
from app.services.email import (
    generate_verification_token,
    store_verification_token,
    validate_verification_token,
    delete_verification_token,
    mark_email_verified,
    send_verification_email,
)
from app.middleware.auth import get_current_user_id

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_TOKEN_COOKIE = "sem_refresh_token"
REFRESH_COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=token,
        httponly=True,
        secure=False,  # True in production (HTTPS)
        samesite="lax",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path="/",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_TOKEN_COOKIE, path="/")


def _user_response(user: dict) -> UserResponse:
    return UserResponse(**user)


# --- Register ---

@router.post("/register", response_model=AuthResponse, status_code=201)
def register(body: UserRegisterRequest, response: Response):
    db = get_supabase()

    # Check duplicate email
    existing = db.table("users").select("id").eq("email", body.email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Check duplicate username
    existing = db.table("users").select("id").eq("username", body.username).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Username already taken")

    # Create user
    hashed = hash_password(body.password)
    insert_result = db.table("users").insert({
        "username": body.username,
        "email": body.email,
        "hashed_password": hashed,
        "date_of_birth": body.date_of_birth.isoformat(),
        "role": "registered",
        "auth_provider": "local",
        "email_verified": False,
    }).execute()

    user = insert_result.data[0]

    # Generate tokens
    access_token = create_access_token(user["id"], user["email"])
    refresh_token = generate_refresh_token()
    store_refresh_token(user["id"], refresh_token)
    _set_refresh_cookie(response, refresh_token)

    # Send verification email
    v_token = generate_verification_token()
    store_verification_token(user["id"], v_token)
    send_verification_email(user["email"], v_token)

    return AuthResponse(user=_user_response(user), access_token=access_token)


# --- Login ---

@router.post("/login", response_model=AuthResponse)
def login(body: UserLoginRequest, response: Response):
    db = get_supabase()

    # Find user by email
    result = db.table("users").select("*").eq("email", body.email).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = result.data[0]

    # Check if account is active
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Check if account is locked
    is_locked, lock_msg = check_account_locked(user)
    if is_locked:
        raise HTTPException(status_code=429, detail=lock_msg)

    # Check auth provider
    if user["auth_provider"] != "local" and not user["hashed_password"]:
        raise HTTPException(
            status_code=400,
            detail="This account uses Google sign-in. Please login with Google.",
        )

    # Verify password
    if not verify_password(body.password, user["hashed_password"]):
        increment_failed_attempts(user["id"], user["failed_login_attempts"])
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Success — reset failed attempts
    reset_failed_attempts(user["id"])

    # Generate tokens
    access_token = create_access_token(user["id"], user["email"])
    refresh_token = generate_refresh_token()
    store_refresh_token(user["id"], refresh_token)
    _set_refresh_cookie(response, refresh_token)

    return AuthResponse(user=_user_response(user), access_token=access_token)


# --- Refresh ---

@router.post("/refresh", response_model=AuthResponse)
def refresh(request: Request, response: Response, body: RefreshTokenRequest = None):
    # Get token from body or cookie
    token = None
    if body and body.refresh_token:
        token = body.refresh_token
    else:
        token = request.cookies.get(REFRESH_TOKEN_COOKIE)

    if not token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    # Validate old token
    user_id = validate_refresh_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Fetch user
    db = get_supabase()
    result = db.table("users").select("*").eq("id", user_id).execute()
    if not result.data or not result.data[0]["is_active"]:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    user = result.data[0]

    # Rotate: store new BEFORE revoking old (safety-first, mia-website pattern)
    new_access = create_access_token(user["id"], user["email"])
    new_refresh = generate_refresh_token()
    store_refresh_token(user["id"], new_refresh)
    revoke_refresh_token(token)
    _set_refresh_cookie(response, new_refresh)

    return AuthResponse(user=_user_response(user), access_token=new_access)


# --- Logout ---

@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, response: Response, body: RefreshTokenRequest = None):
    token = None
    if body and body.refresh_token:
        token = body.refresh_token
    else:
        token = request.cookies.get(REFRESH_TOKEN_COOKIE)

    if token:
        revoke_refresh_token(token)

    _clear_refresh_cookie(response)
    return MessageResponse(message="Logged out successfully")


# --- Me ---

@router.get("/me", response_model=UserResponse)
def me(user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    result = db.table("users").select("*").eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_response(result.data[0])


# --- Email Verification ---

@router.get("/verify-email", response_model=MessageResponse)
def verify_email(token: str):
    user_id = validate_verification_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    mark_email_verified(user_id)
    delete_verification_token(token)
    return MessageResponse(message="Email verified successfully")


@router.post("/resend-verification", response_model=MessageResponse)
def resend_verification(user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    result = db.table("users").select("email, email_verified").eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = result.data[0]
    if user["email_verified"]:
        raise HTTPException(status_code=400, detail="Email already verified")

    v_token = generate_verification_token()
    store_verification_token(user_id, v_token)
    send_verification_email(user["email"], v_token)
    return MessageResponse(message="Verification email sent")


# --- Google OAuth ---

OAUTH_STATE_COOKIE = "oauth_state"


@router.get("/google")
def google_auth(mode: str = "login"):
    """Redirect to Google OAuth. mode: 'signup' or 'login'."""
    state = generate_oauth_state()
    auth_url = build_google_auth_url(state, mode)
    redirect = RedirectResponse(url=auth_url)
    redirect.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=600,  # 10 minutes
        path="/",
    )
    return redirect


@router.get("/google/callback")
def google_callback(
    code: str,
    state: str,
    request: Request,
):
    """Handle Google OAuth callback."""
    # Validate state (CSRF protection)
    stored_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    # Exchange code for tokens
    try:
        google_tokens = exchange_code_for_tokens(code)
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

    # Get user info from Google
    try:
        google_user = get_google_user_info(google_tokens["access_token"])
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to fetch Google user info")

    google_email = google_user["email"]
    google_id = google_user["id"]

    db = get_supabase()

    # Check if user exists by email
    result = db.table("users").select("*").eq("email", google_email).execute()

    if result.data:
        # Existing user — link Google account if not already linked
        user = result.data[0]
        if not user["google_id"]:
            db.table("users").update({
                "google_id": google_id,
                "auth_provider": "google" if not user["hashed_password"] else user["auth_provider"],
            }).eq("id", user["id"]).execute()
        if not user["email_verified"]:
            db.table("users").update({"email_verified": True}).eq("id", user["id"]).execute()
        # Re-fetch updated user
        user = db.table("users").select("*").eq("id", user["id"]).execute().data[0]
    else:
        # New user — create account
        username = google_email.split("@")[0]
        # Ensure unique username
        existing = db.table("users").select("id").eq("username", username).execute()
        if existing.data:
            username = f"{username}_{google_id[:6]}"

        insert_result = db.table("users").insert({
            "username": username,
            "email": google_email,
            "hashed_password": None,
            "role": "registered",
            "auth_provider": "google",
            "google_id": google_id,
            "email_verified": True,
        }).execute()
        user = insert_result.data[0]

    # Generate tokens
    access_token = create_access_token(user["id"], user["email"])
    refresh_token = generate_refresh_token()
    store_refresh_token(user["id"], refresh_token)

    # Redirect to frontend with access token
    params = urlencode({"access_token": access_token, "token_type": "bearer"})
    redirect = RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?{params}")
    redirect.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path="/",
    )
    redirect.delete_cookie(key=OAUTH_STATE_COOKIE, path="/")
    return redirect
