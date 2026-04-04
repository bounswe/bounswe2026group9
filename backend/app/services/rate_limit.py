"""Shared helpers for rate-limit and lockout exemptions."""

import os

RATE_LIMIT_EXEMPT_EMAILS = frozenset(
    e.strip().lower()
    for e in os.getenv(
        "RATE_LIMIT_EXEMPT_EMAILS",
        "muhittin0koybasi@gmail.com,emir27_bora@hotmail.com",
    ).split(",")
    if e.strip()
)


def is_rate_limit_exempt_email(email: str | None) -> bool:
    if not email:
        return False
    return email.strip().lower() in RATE_LIMIT_EXEMPT_EMAILS
