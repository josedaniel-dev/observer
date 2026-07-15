"""Authentication middleware for API key validation."""

from __future__ import annotations

import os

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

# Read API key from environment. If not set, auth is disabled (dev mode).
API_KEY = os.getenv("OBSERVATORY_API_KEY", "")

_api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


async def require_api_key(
    authorization: str | None = Security(_api_key_header),
) -> None:
    """Dependency that validates the API key when authentication is enabled.

    If OBSERVATORY_API_KEY is not set, all requests are allowed (dev mode).
    If set, requests must include `Authorization: Bearer <key>`.
    """
    if not API_KEY:
        return

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing API key")

    # Support both "Bearer <key>" and raw key formats
    token = authorization
    if authorization.lower().startswith("bearer "):
        token = authorization[7:]

    if token != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
