"""Trace API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.models.trace import Trace, Span
from app.websocket import manager

router = APIRouter()


class SpanCreate(BaseModel):
    """Schema for creating a span."""

    id: Optional[str] = None
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


class TraceResponse(BaseModel):
    """Schema for trace response."""

    id: str
    name: str
    session_id: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    metadata: Optional[dict]
    created_at: datetime


class SpanResponse(BaseModel):
    """Schema for span response."""

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


@router.post("/", response_model=TraceResponse)
async def create_trace(
    trace_data: TraceCreate,
    session: AsyncSession = Depends(get_session),
) -> Trace:
    """Create a new trace with optional spans."""
    trace = Trace(
        id=uuid.uuid4(),
        name=trace_data.name,
        session_id=uuid.UUID(trace_data.session_id) if trace_data.session_id else None,
        start_time=datetime.fromtimestamp(trace_data.start_time),
        end_time=datetime.fromtimestamp(trace_data.end_time) if trace_data.end_time else None,
        status=trace_data.status,
        metadata_=trace_data.metadata,
    )
    session.add(trace)

    # Add spans
    for span_data in trace_data.spans:
        span = Span(
            id=uuid.UUID(span_data.id) if span_data.id else uuid.uuid4(),
            trace_id=trace.id,
            parent_span_id=uuid.UUID(span_data.parent_id) if span_data.parent_id else None,
            name=span_data.name,
            span_type=span_data.span_type,
            start_time=datetime.fromtimestamp(span_data.start_time),
            end_time=datetime.fromtimestamp(span_data.end_time) if span_data.end_time else None,
            status=span_data.status,
            input_=span_data.input,
            output_=span_data.output,
            tokens_input=span_data.tokens_input,
            tokens_output=span_data.tokens_output,
            cost_usd=span_data.cost_usd,
            metadata_=span_data.metadata,
            attributes=span_data.attributes,
        )
        session.add(span)

    await session.flush()

    # Broadcast new trace via WebSocket
    await manager.broadcast({
        "type": "new_trace",
        "data": {
            "id": str(trace.id),
            "name": trace.name,
            "status": trace.status,
            "created_at": trace.created_at.isoformat() if trace.created_at else None,
        },
    })

    return trace


@router.get("/", response_model=list[TraceResponse])
async def list_traces(
    session_id: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[Trace]:
    """List traces with optional filtering."""
    query = select(Trace).order_by(Trace.created_at.desc())

    if session_id:
        query = query.where(Trace.session_id == uuid.UUID(session_id))

    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{trace_id}", response_model=TraceResponse)
async def get_trace(
    trace_id: str,
    session: AsyncSession = Depends(get_session),
) -> Trace:
    """Get a trace by ID."""
    query = select(Trace).where(Trace.id == uuid.UUID(trace_id))
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
    query = (
        select(Span)
        .where(Span.trace_id == uuid.UUID(trace_id))
        .order_by(Span.start_time)
    )
    result = await session.execute(query)
    return list(result.scalars().all())
