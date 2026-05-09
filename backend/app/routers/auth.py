from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from starlette.responses import RedirectResponse

from app.config import settings
from app.database import get_supabase
from app.middleware.auth import get_current_user_id
from app.models.errors import (
    AUTH_RESPONSES,
    CONFLICT_RESPONSE,
    NOT_FOUND_RESPONSE,
    RATE_LIMIT_RESPONSE,
)
from app.models.user import (
    AuthResponse,
    MessageResponse,
    RefreshTokenRequest,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.rate_limit import limiter
from app.repositories.user import USER_AUTH_COLS, USER_SAFE_COLS
from app.services.auth import (
    check_account_locked,
    create_access_token,
    generate_refresh_token,
    hash_password,
    increment_failed_attempts,
    reset_failed_attempts,
    revoke_refresh_token,
    store_refresh_token,
    validate_refresh_token,
    verify_password,
)
from app.services.email import (
    delete_verification_token,
    generate_verification_token,
    is_smtp_configured,
    mark_email_verified,
    send_verification_email,
    store_verification_token,
    validate_verification_token,
)
from app.services.oauth import (
    build_google_auth_url,
    exchange_code_for_tokens,
    generate_oauth_state,
    get_google_user_info,
)
from app.services.rate_limit import is_rate_limit_exempt_email

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_TOKEN_COOKIE = "sem_refresh_token"  # nosec B105 — cookie name, not a credential
REFRESH_COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 days


def _set_refresh_cookie(response: Response, token: str) -> None:
    kwargs: dict = dict(
        key=REFRESH_TOKEN_COOKIE,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path="/",
    )
    if settings.COOKIE_DOMAIN:
        kwargs["domain"] = settings.COOKIE_DOMAIN
    response.set_cookie(**kwargs)


def _clear_refresh_cookie(response: Response) -> None:
    kwargs: dict = dict(key=REFRESH_TOKEN_COOKIE, path="/")
    if settings.COOKIE_DOMAIN:
        kwargs["domain"] = settings.COOKIE_DOMAIN
    response.delete_cookie(**kwargs)


def _user_response(user: dict) -> UserResponse:
    return UserResponse(**user)


# --- Register ---

@router.post(
    "/register",
    status_code=201,
    response_model=AuthResponse,
    summary="Register a new user",
    description=(
        "Creates a local-auth user, sets the refresh-token cookie, and "
        "returns an access token. A verification email is sent in the "
        "background; `email_sent=false` means SMTP is unconfigured."
    ),
    responses={**CONFLICT_RESPONSE, **RATE_LIMIT_RESPONSE},
)
@limiter.limit("5/minute")
def register(request: Request, body: UserRegisterRequest, response: Response, background_tasks: BackgroundTasks):
    db = get_supabase()

    # Create user (unique constraints handle race conditions)
    hashed = hash_password(body.password)
    try:
        insert_result = db.table("users").insert({
            "username": body.username,
            "email": body.email,
            "hashed_password": hashed,
            "date_of_birth": body.date_of_birth.isoformat(),
            "role": "registered",
            "auth_provider": "local",
            "email_verified": False,
        }).execute()
    except Exception as e:
        error_msg = str(e).lower()
        if "users_email_key" in error_msg:
            raise HTTPException(status_code=409, detail="Email already registered") from None
        if "users_username_key" in error_msg:
            raise HTTPException(status_code=409, detail="Username already taken") from None
        raise

    user = insert_result.data[0]

    # Generate tokens
    access_token = create_access_token(user["id"], user["email"])
    refresh_token = generate_refresh_token()
    store_refresh_token(user["id"], refresh_token)
    _set_refresh_cookie(response, refresh_token)

    # Send verification email in background (non-blocking)
    v_token = generate_verification_token()
    store_verification_token(user["id"], v_token)
    background_tasks.add_task(send_verification_email, user["email"], v_token)

    return AuthResponse(user=_user_response(user), access_token=access_token, email_sent=is_smtp_configured())


# --- Login ---

@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in with email + password",
    description=(
        "Returns an access token and sets the `sem_refresh_token` HttpOnly "
        "cookie. Repeated failures lock the account; Google-only accounts "
        "must use `/auth/google`."
    ),
    responses={**AUTH_RESPONSES, **RATE_LIMIT_RESPONSE},
)
@limiter.limit("10/minute")
def login(request: Request, body: UserLoginRequest, response: Response):
    db = get_supabase()

    # Find user by email
    result = db.table("users").select(USER_AUTH_COLS).eq("email", body.email).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = result.data[0]
    is_rate_limit_exempt = is_rate_limit_exempt_email(user.get("email"))

    # Check if account is active
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Check if account is locked
    if not is_rate_limit_exempt:
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
        if not is_rate_limit_exempt:
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

@router.post(
    "/refresh",
    response_model=AuthResponse,
    summary="Rotate access + refresh tokens",
    description=(
        "Reads the refresh token from the body or the `sem_refresh_token` "
        "cookie, rotates it, and returns a fresh access token."
    ),
    responses={**AUTH_RESPONSES},
)
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
    result = db.table("users").select(USER_SAFE_COLS).eq("id", user_id).execute()
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

@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out",
    description="Revokes the refresh token and clears the cookie. Idempotent.",
)
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

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Authenticated user's profile",
    responses={**AUTH_RESPONSES, **NOT_FOUND_RESPONSE},
)
def me(user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    result = db.table("users").select(USER_SAFE_COLS).eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_response(result.data[0])


# --- Email Verification ---

@router.get(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email via token",
    description="Token is delivered in the verification email link.",
)
def verify_email(token: str):
    user_id = validate_verification_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    mark_email_verified(user_id)
    delete_verification_token(token)
    return MessageResponse(message="Email verified successfully")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend verification email",
    responses={**AUTH_RESPONSES, **RATE_LIMIT_RESPONSE},
)
@limiter.limit("3/minute")
def resend_verification(request: Request, background_tasks: BackgroundTasks, user_id: str = Depends(get_current_user_id)):
    db = get_supabase()
    result = db.table("users").select("email, email_verified").eq("id", user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    user = result.data[0]
    if user["email_verified"]:
        raise HTTPException(status_code=400, detail="Email already verified")

    v_token = generate_verification_token()
    store_verification_token(user_id, v_token)
    background_tasks.add_task(send_verification_email, user["email"], v_token)
    return MessageResponse(message="Verification email sent")


# --- Google OAuth ---

OAUTH_STATE_COOKIE = "oauth_state"


@router.get(
    "/google",
    summary="Start Google OAuth flow",
    description=(
        "Redirects the browser to Google's consent screen. `mode` is "
        "either `login` or `signup` and is round-tripped through state."
    ),
)
def google_auth(mode: str = "login"):
    """Redirect to Google OAuth. mode: 'signup' or 'login'."""
    state = generate_oauth_state()
    auth_url = build_google_auth_url(state, mode)
    redirect = RedirectResponse(url=auth_url)
    redirect.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=state,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=600,  # 10 minutes
        path="/",
    )
    return redirect


@router.get(
    "/google/callback",
    summary="Google OAuth callback",
    description=(
        "Validates the state cookie, exchanges the code for Google tokens, "
        "links or creates the local user, sets the refresh-token cookie, "
        "and redirects to the frontend `/auth/callback` page."
    ),
)
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
    except Exception as err:
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code") from err

    # Get user info from Google
    try:
        google_user = get_google_user_info(google_tokens["access_token"])
    except Exception as err:
        raise HTTPException(status_code=400, detail="Failed to fetch Google user info") from err

    google_email = google_user["email"]
    google_id = google_user["id"]
    google_email_verified = google_user.get("verified_email", False)

    db = get_supabase()

    # Check if user exists by email
    result = db.table("users").select(USER_AUTH_COLS).eq("email", google_email).execute()

    if result.data:
        # Existing user — link Google account if not already linked
        user = result.data[0]

        # Check if account is deactivated
        if not user["is_active"]:
            raise HTTPException(status_code=403, detail="Account is deactivated")

        if not user["google_id"]:
            db.table("users").update({
                "google_id": google_id,
                "auth_provider": "google" if not user["hashed_password"] else user["auth_provider"],
            }).eq("id", user["id"]).execute()
        if not user["email_verified"] and google_email_verified:
            db.table("users").update({"email_verified": True}).eq("id", user["id"]).execute()
        # Re-fetch updated user
        user = db.table("users").select(USER_SAFE_COLS).eq("id", user["id"]).execute().data[0]
    else:
        # New user — create account
        import secrets
        username = google_email.split("@")[0]
        for _ in range(3):
            try:
                insert_result = db.table("users").insert({
                    "username": username,
                    "email": google_email,
                    "hashed_password": None,
                    "role": "registered",
                    "auth_provider": "google",
                    "google_id": google_id,
                    "email_verified": google_email_verified,
                }).execute()
                user = insert_result.data[0]
                break
            except Exception as e:
                if "users_username_key" in str(e).lower():
                    username = f"{google_email.split('@')[0]}_{secrets.token_hex(3)}"
                else:
                    raise
        else:
            raise HTTPException(status_code=500, detail="Failed to create user")

    # Generate refresh token only — frontend will call /auth/refresh to get access token
    refresh_token = generate_refresh_token()
    store_refresh_token(user["id"], refresh_token)

    # Redirect to frontend (no token in URL)
    redirect = RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback")
    _set_refresh_cookie(redirect, refresh_token)
    redirect.delete_cookie(key=OAUTH_STATE_COOKIE, path="/")
    return redirect
