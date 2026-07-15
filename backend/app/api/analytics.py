"""Analytics API endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.trace import Trace, Span
from app.models.evaluation import Evaluation

router = APIRouter()


class AnalyticsSummary(BaseModel):
    """Summary analytics response."""

    total_traces: int
    total_spans: int
    total_cost_usd: float
    avg_latency_ms: float
    error_count: int
    error_rate: float
    total_evaluations: int
    avg_evaluation_score: Optional[float]


class CostByModel(BaseModel):
    """Cost breakdown by model."""

    model: str
    cost_usd: float
    span_count: int


class TraceTimeline(BaseModel):
    """Trace count over time."""

    timestamp: str
    count: int
    cost_usd: float


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    session_id: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Get analytics summary for the specified time period."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Total traces
    trace_query = select(func.count(Trace.id)).where(Trace.created_at >= cutoff)
    if session_id:
        from uuid import UUID
        trace_query = trace_query.where(Trace.session_id == UUID(session_id))
    result = await session.execute(trace_query)
    total_traces = result.scalar() or 0

    # Total spans and cost
    span_query = select(
        func.count(Span.id),
        func.coalesce(func.sum(Span.cost_usd), 0),
        func.coalesce(func.avg(Span.end_time - Span.start_time), 0),
    ).join(Trace, Span.trace_id == Trace.id).where(Trace.created_at >= cutoff)
    result = await session.execute(span_query)
    span_data = result.one()
    total_spans = span_data[0] or 0
    total_cost_usd = float(span_data[1] or 0)
    avg_latency_ms = float(span_data[2] or 0) * 1000

    # Error count
    error_query = select(func.count(Trace.id)).where(
        Trace.created_at >= cutoff, Trace.status == "error"
    )
    result = await session.execute(error_query)
    error_count = result.scalar() or 0

    # Evaluations
    eval_query = select(
        func.count(Evaluation.id),
        func.coalesce(func.avg(Evaluation.score), 0),
    ).join(Trace, Evaluation.trace_id == Trace.id).where(Trace.created_at >= cutoff)
    result = await session.execute(eval_query)
    eval_data = result.one()
    total_evaluations = eval_data[0] or 0
    avg_score = float(eval_data[1] or 0) if total_evaluations > 0 else None

    return {
        "total_traces": total_traces,
        "total_spans": total_spans,
        "total_cost_usd": total_cost_usd,
        "avg_latency_ms": avg_latency_ms,
        "error_count": error_count,
        "error_rate": error_count / total_traces if total_traces > 0 else 0,
        "total_evaluations": total_evaluations,
        "avg_evaluation_score": avg_score,
    }


@router.get("/cost-by-model", response_model=list[CostByModel])
async def get_cost_by_model(
    hours: int = Query(24, ge=1, le=720),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Get cost breakdown by model (from span attributes)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Use json_extract for cross-dialect compatibility (SQLite + PostgreSQL)
    model_col = func.json_extract(Span.attributes, "$.model").label("model")

    query = (
        select(
            model_col,
            func.sum(Span.cost_usd).label("cost_usd"),
            func.count(Span.id).label("span_count"),
        )
        .join(Trace, Span.trace_id == Trace.id)
        .where(Trace.created_at >= cutoff)
        .where(Span.attributes["model"].isnot(None))
        .group_by(model_col)
        .order_by(func.sum(Span.cost_usd).desc())
    )
    result = await session.execute(query)
    rows = result.all()

    return [
        {"model": row.model or "unknown", "cost_usd": float(row.cost_usd or 0), "span_count": row.span_count}
        for row in rows
    ]


@router.get("/timeline", response_model=list[TraceTimeline])
async def get_trace_timeline(
    hours: int = Query(24, ge=1, le=720),
    interval_minutes: int = Query(60, ge=5, le=1440),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Get trace count and cost over time."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Get all traces in the time range
    query = (
        select(Trace)
        .where(Trace.created_at >= cutoff)
        .order_by(Trace.created_at)
    )
    result = await session.execute(query)
    traces = list(result.scalars().all())

    # Get all span costs for traces in the time range (single query, no N+1)
    cost_query = select(
        Span.trace_id,
        func.coalesce(func.sum(Span.cost_usd), 0).label("cost_usd"),
    ).join(Trace, Span.trace_id == Trace.id).where(
        Trace.created_at >= cutoff
    ).group_by(Span.trace_id)
    cost_result = await session.execute(cost_query)
    cost_by_trace = {row.trace_id: float(row.cost_usd) for row in cost_result.all()}

    # Bucket traces by interval
    buckets: dict[str, dict] = {}
    for trace in traces:
        # Truncate to interval
        ts = trace.created_at.replace(
            minute=(trace.created_at.minute // interval_minutes) * interval_minutes,
            second=0,
            microsecond=0,
        )
        key = ts.isoformat()
        if key not in buckets:
            buckets[key] = {"timestamp": key, "count": 0, "cost_usd": 0}
        buckets[key]["count"] += 1
        buckets[key]["cost_usd"] += cost_by_trace.get(trace.id, 0)

    return list(buckets.values())
