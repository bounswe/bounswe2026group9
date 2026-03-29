import os
import re
import uuid

BASE_TEST_PREFIXES = (
    "testuser",
    "eventtest",
    "imgtest",
    "cattest",
    "disctest",
    "cmttest",
    "invtest",
    "notiftest",
    "emittest",
)


def _normalized_run_id() -> str:
    raw = os.getenv("TEST_RUN_ID", "")
    normalized = re.sub(r"[^0-9A-Za-z]", "", raw)
    return normalized or uuid.uuid4().hex[:8]


TEST_RUN_ID = _normalized_run_id()
USERNAME_RUN_ID = TEST_RUN_ID[:6]


def build_test_identity(prefix: str, *, suffix: str = "") -> tuple[str, str]:
    unique = uuid.uuid4().hex[:8]
    username = f"{prefix}_{USERNAME_RUN_ID}_{unique}{suffix}"
    email = f"{prefix}_{TEST_RUN_ID}_{unique}{suffix}@example.com"
    return username, email


def build_test_email(prefix: str) -> str:
    unique = uuid.uuid4().hex[:8]
    return f"{prefix}_{TEST_RUN_ID}_{unique}@example.com"


def cleanup_username_patterns() -> list[str]:
    return [f"{prefix}_{USERNAME_RUN_ID}_%" for prefix in BASE_TEST_PREFIXES]
