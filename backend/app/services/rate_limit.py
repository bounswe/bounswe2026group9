"""Shared helpers for rate-limit and lockout exemptions."""

RATE_LIMIT_EXEMPT_EMAILS = {
    "muhittin0koybasi@gmail.com",
}


def is_rate_limit_exempt_email(email: str | None) -> bool:
    if not email:
        return False
    return email.strip().lower() in RATE_LIMIT_EXEMPT_EMAILS
