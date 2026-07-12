"""Database configuration - supports both PostgreSQL and SQLite."""

from __future__ import annotations

import os

from sqlalchemy.ext.asyncio import create_async_engine

# Support both PostgreSQL and SQLite
# PostgreSQL: postgresql+asyncpg://user:pass@host:port/db
# SQLite: sqlite+aiosqlite:///./path/to/db.db
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./observatory.db",
)

# Create engine with appropriate settings
if DATABASE_URL.startswith("sqlite"):
    # SQLite-specific settings
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL settings
    engine = create_async_engine(DATABASE_URL, echo=False)
