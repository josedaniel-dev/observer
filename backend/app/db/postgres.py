"""PostgreSQL database configuration."""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/observatory",
)

engine = create_async_engine(DATABASE_URL, echo=False)
