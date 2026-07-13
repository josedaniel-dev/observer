"""Database helper for local SQLite access."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Optional

DEFAULT_DB_PATH = Path("observatory.db")


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Get a SQLite connection."""
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def list_traces(
    db_path: Optional[Path] = None,
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
    name_search: Optional[str] = None,
) -> list[dict[str, Any]]:
    """List traces from local SQLite database."""
    conn = get_connection(db_path)
    try:
        query = "SELECT * FROM traces WHERE 1=1"
        params: list[Any] = []

        if status:
            query += " AND status = ?"
            params.append(status)

        if name_search:
            query += " AND name LIKE ?"
            params.append(f"%{name_search}%")

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_trace(trace_id: str, db_path: Optional[Path] = None) -> Optional[dict[str, Any]]:
    """Get a single trace by ID."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute("SELECT * FROM traces WHERE id = ?", (trace_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_trace_spans(trace_id: str, db_path: Optional[Path] = None) -> list[dict[str, Any]]:
    """Get all spans for a trace."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT * FROM spans WHERE trace_id = ? ORDER BY start_time",
            (trace_id,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def list_evaluations(
    db_path: Optional[Path] = None,
    trace_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List evaluations from local SQLite database."""
    conn = get_connection(db_path)
    try:
        query = "SELECT * FROM evaluations WHERE 1=1"
        params: list[Any] = []

        if trace_id:
            query += " AND trace_id = ?"
            params.append(trace_id)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_stats(db_path: Optional[Path] = None) -> dict[str, Any]:
    """Get summary statistics from the database."""
    conn = get_connection(db_path)
    try:
        stats: dict[str, Any] = {}

        # Trace counts
        cursor = conn.execute("SELECT COUNT(*) FROM traces")
        stats["total_traces"] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM traces WHERE status = 'ok'")
        stats["ok_traces"] = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM traces WHERE status = 'error'")
        stats["error_traces"] = cursor.fetchone()[0]

        # Span counts
        cursor = conn.execute("SELECT COUNT(*) FROM spans")
        stats["total_spans"] = cursor.fetchone()[0]

        # Token totals
        cursor = conn.execute(
            "SELECT SUM(tokens_input), SUM(tokens_output) FROM spans WHERE tokens_input IS NOT NULL"
        )
        row = cursor.fetchone()
        stats["total_input_tokens"] = row[0] or 0
        stats["total_output_tokens"] = row[1] or 0

        # Cost total
        cursor = conn.execute(
            "SELECT SUM(cost_usd) FROM spans WHERE cost_usd IS NOT NULL"
        )
        stats["total_cost_usd"] = cursor.fetchone()[0] or 0.0

        # Evaluation counts
        cursor = conn.execute("SELECT COUNT(*) FROM evaluations")
        stats["total_evaluations"] = cursor.fetchone()[0]

        return stats
    finally:
        conn.close()
