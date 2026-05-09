import os
import re
import uuid


def _normalized_run_id() -> str:
    raw = os.getenv("TEST_RUN_ID", "")
    # Under pytest-xdist each worker is a separate process that shares the
    # parent's TEST_RUN_ID. The autouse `cleanup_test_users` fixture deletes
    # rows by an email pattern keyed off this id — without per-worker
    # namespacing, worker A's teardown wipes worker B/C/D's users mid-test
    # and they hit "User not found" on the next request. Fold the worker id
    # into the run id so each worker has its own delete pattern.
    worker = os.getenv("PYTEST_XDIST_WORKER", "")
    if worker:
        raw = f"{raw}_{worker}"
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


def cleanup_email_pattern() -> str:
    return f"%_{TEST_RUN_ID}_%@example.com"
