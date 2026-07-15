"""Trace API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models.trace import Trace, Span
from app.websocket import manager

router = APIRouter()


def _safe_uuid(value: str | None) -> str | None:
    """Validate and return a UUID string, or None if invalid."""
    if not value:
        return None
    try:
        uuid.UUID(value)
        return value
    except ValueError:
        return None


class SpanCreate(BaseModel):
    """Schema for creating a span."""

    id: Optional[str] = None
    trace_id: Optional[str] = None
    parent_id: Optional[str] = None
    name: str
    span_type: str = "generic"
    start_time: float
    end_time: Optional[float] = None
    status: str = "unset"
    input: Optional[dict] = None
    output: Optional[dict] = None
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    cost_usd: Optional[float] = None
    metadata: Optional[dict] = None
    attributes: Optional[dict] = None


class TraceCreate(BaseModel):
    """Schema for creating a trace."""

    name: str
    session_id: Optional[str] = None
    start_time: float
    end_time: Optional[float] = None
    status: str = "unset"
    metadata: Optional[dict] = None
    spans: list[SpanCreate] = []

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError:
                return None
        return v


class BatchSpansCreate(BaseModel):
    """Schema for batch-creating spans (auto-creates traces)."""

    spans: list[SpanCreate] = []


class TraceResponse(BaseModel):
    """Schema for trace response."""

    model_config = {"from_attributes": True}

    id: str
    name: str
    session_id: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    metadata: Optional[dict]
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def _map_orm_keys(cls, values: dict | object) -> dict:
        if hasattr(values, "meta"):
            return {
                "id": values.id,
                "name": values.name,
                "session_id": values.session_id,
                "start_time": values.start_time,
                "end_time": values.end_time,
                "status": values.status,
                "metadata": values.meta,
                "created_at": values.created_at,
            }
        return values


class TraceListResponse(BaseModel):
    """Paginated trace list response."""

    traces: list[TraceResponse]
    total: int
    limit: int
    offset: int


class SpanResponse(BaseModel):
    """Schema for span response."""

    model_config = {"from_attributes": True}

    id: str
    trace_id: str
    parent_id: Optional[str]
    name: str
    span_type: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    input: Optional[dict]
    output: Optional[dict]
    tokens_input: Optional[int]
    tokens_output: Optional[int]
    cost_usd: Optional[float]
    metadata: Optional[dict]
    attributes: Optional[dict]

    @model_validator(mode="before")
    @classmethod
    def _map_orm_keys(cls, values: dict | object) -> dict:
        if hasattr(values, "inp"):
            return {
                "id": values.id,
                "trace_id": values.trace_id,
                "parent_id": values.parent_span_id,
                "name": values.name,
                "span_type": values.span_type,
                "start_time": values.start_time,
                "end_time": values.end_time,
                "status": values.status,
                "input": values.inp,
                "output": values.out,
                "tokens_input": values.tokens_input,
                "tokens_output": values.tokens_output,
                "cost_usd": float(values.cost_usd) if values.cost_usd else None,
                "metadata": values.meta,
                "attributes": values.attributes,
            }
        return values


@router.post("/", response_model=TraceResponse)
async def create_trace(
    trace_data: TraceCreate,
    session: AsyncSession = Depends(get_session),
) -> Trace:
    """Create a new trace with optional spans."""
    trace_id = str(uuid.uuid4())
    trace = Trace(
        id=trace_id,
        name=trace_data.name,
        session_id=trace_data.session_id,
        start_time=datetime.fromtimestamp(trace_data.start_time, tz=timezone.utc),
        end_time=datetime.fromtimestamp(trace_data.end_time, tz=timezone.utc) if trace_data.end_time else None,
        status=trace_data.status,
        meta=trace_data.metadata,
    )
    session.add(trace)

    # Add spans
    for span_data in trace_data.spans:
        span = Span(
            id=span_data.id or str(uuid.uuid4()),
            trace_id=trace_id,
            parent_span_id=_safe_uuid(span_data.parent_id),
            name=span_data.name,
            span_type=span_data.span_type,
            start_time=datetime.fromtimestamp(span_data.start_time, tz=timezone.utc),
            end_time=datetime.fromtimestamp(span_data.end_time, tz=timezone.utc) if span_data.end_time else None,
            status=span_data.status,
            inp=span_data.input,
            out=span_data.output,
            tokens_input=span_data.tokens_input,
            tokens_output=span_data.tokens_output,
            cost_usd=span_data.cost_usd,
            meta=span_data.metadata,
            attributes=span_data.attributes,
        )
        session.add(span)

    await session.flush()

    # Broadcast new trace via WebSocket
    await manager.broadcast({
        "type": "new_trace",
        "data": {
            "id": trace_id,
            "name": trace.name,
            "status": trace.status,
            "created_at": trace.created_at.isoformat() if trace.created_at else None,
        },
    })

    return trace


@router.post("/batch", response_model=list[TraceResponse])
async def create_traces_batch(
    batch_data: BatchSpansCreate,
    session: AsyncSession = Depends(get_session),
) -> list[Trace]:
    """Create traces from a batch of spans.

    Spans are grouped by trace_id. If a trace_id doesn't exist, a new trace is created.
    This endpoint is designed for SDK exporters that send spans directly.
    """
    # Group spans by trace_id
    spans_by_trace: dict[str, list[SpanCreate]] = {}
    for span_data in batch_data.spans:
        trace_id = span_data.trace_id or str(uuid.uuid4())
        if trace_id not in spans_by_trace:
            spans_by_trace[trace_id] = []
        spans_by_trace[trace_id].append(span_data)

    created_traces: list[Trace] = []

    for trace_id, spans in spans_by_trace.items():
        # Check if trace already exists
        query = select(Trace).where(Trace.id == trace_id)
        result = await session.execute(query)
        trace = result.scalar_one_or_none()

        if not trace:
            # Create trace from first span's timing
            first_span = spans[0]
            trace = Trace(
                id=trace_id,
                name=first_span.name,
                start_time=datetime.fromtimestamp(first_span.start_time, tz=timezone.utc),
                end_time=datetime.fromtimestamp(spans[-1].end_time, tz=timezone.utc) if spans[-1].end_time else None,
                status="ok" if all(s.status == "ok" for s in spans) else "error",
            )
            session.add(trace)

        # Add spans
        for span_data in spans:
            span = Span(
                id=span_data.id or str(uuid.uuid4()),
                trace_id=trace_id,
                parent_span_id=_safe_uuid(span_data.parent_id),
                name=span_data.name,
                span_type=span_data.span_type,
                start_time=datetime.fromtimestamp(span_data.start_time, tz=timezone.utc),
                end_time=datetime.fromtimestamp(span_data.end_time, tz=timezone.utc) if span_data.end_time else None,
                status=span_data.status,
                inp=span_data.input,
                out=span_data.output,
                tokens_input=span_data.tokens_input,
                tokens_output=span_data.tokens_output,
                cost_usd=span_data.cost_usd,
                meta=span_data.metadata,
                attributes=span_data.attributes,
            )
            session.add(span)

        created_traces.append(trace)

    await session.flush()

    # Broadcast new traces via WebSocket
    for trace in created_traces:
        await manager.broadcast({
            "type": "new_trace",
            "data": {
                "id": str(trace.id),
                "name": trace.name,
                "status": trace.status,
                "created_at": trace.created_at.isoformat() if trace.created_at else None,
            },
        })

    return created_traces


@router.get("/", response_model=TraceListResponse)
async def list_traces(
    session_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List traces with optional filtering and server-side search."""
    base_query = select(Trace)

    if session_id:
        valid_sid = _safe_uuid(session_id)
        if valid_sid:
            base_query = base_query.where(Trace.session_id == valid_sid)

    if status:
        base_query = base_query.where(Trace.status == status)

    if search:
        base_query = base_query.where(Trace.name.ilike(f"%{search}%"))

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await session.execute(count_query)).scalar() or 0

    # Get paginated results
    data_query = base_query.order_by(Trace.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(data_query)
    traces = list(result.scalars().all())

    return {
        "traces": traces,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    session: AsyncSession = Depends(get_session),
) -> Trace:
    """Get a trace by ID."""
    valid_id = _safe_uuid(trace_id)
    if not valid_id:
        raise HTTPException(status_code=400, detail="Invalid trace ID format")

    query = select(Trace).where(Trace.id == valid_id)
    result = await session.execute(query)
    trace = result.scalar_one_or_none()

    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    return trace


@router.get("/{trace_id}/spans", response_model=list[SpanResponse])
async def get_trace_spans(
    trace_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[Span]:
    """Get all spans for a trace."""
    valid_id = _safe_uuid(trace_id)
    if not valid_id:
        raise HTTPException(status_code=400, detail="Invalid trace ID format")

    query = (
        select(Span)
        .where(Span.trace_id == valid_id)
        .order_by(Span.start_time)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


@router.delete("/{trace_id}")
async def delete_trace(
    trace_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """Delete a trace and its spans."""
    valid_id = _safe_uuid(trace_id)
    if not valid_id:
        raise HTTPException(status_code=400, detail="Invalid trace ID format")

    query = select(Trace).where(Trace.id == valid_id)
    result = await session.execute(query)
    trace = result.scalar_one_or_none()

    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    await session.delete(trace)
    await session.flush()
    return {"detail": "Trace deleted"}
