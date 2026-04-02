"""Shared rate limiter instance for per-endpoint rate limiting."""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

# Disable rate limiting during tests (pytest sets TESTING=1 via conftest)
_enabled = os.getenv("TESTING", "") != "1"

limiter = Limiter(key_func=get_remote_address, enabled=_enabled)
