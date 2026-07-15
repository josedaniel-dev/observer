"""Rate limiter shared across the application."""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address


def _rate_limit_key(request: "Request") -> str:  # noqa: F821
    """Rate limit key: use API key header if present, otherwise IP."""
    auth = request.headers.get("Authorization", "")
    if auth:
        token = auth[7:] if auth.lower().startswith("bearer ") else auth
        if token:
            return f"apikey:{token}"
    return get_remote_address(request)


# Configurable via env vars
_default_limit = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
_batch_limit = os.getenv("RATE_LIMIT_BATCH", "10/minute")

limiter = Limiter(key_func=_rate_limit_key, default_limits=[_default_limit])
