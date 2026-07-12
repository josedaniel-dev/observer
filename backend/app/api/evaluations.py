"""Evaluation API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.evaluation import Evaluation

router = APIRouter()


class EvaluationCreate(BaseModel):
    """Schema for creating an evaluation."""

    trace_id: str
    span_id: Optional[str] = None
    evaluator_type: str
    score: Optional[float] = None
    criteria: Optional[dict] = None
    result: Optional[dict] = None


class EvaluationResponse(BaseModel):
    """Schema for evaluation response."""

    id: str
    trace_id: str
    span_id: Optional[str]
    evaluator_type: str
    score: Optional[float]
    criteria: Optional[dict]
    result: Optional[dict]
    created_at: datetime


@router.post("/", response_model=EvaluationResponse)
async def create_evaluation(
    eval_data: EvaluationCreate,
    session: AsyncSession = Depends(get_session),
) -> Evaluation:
    """Create a new evaluation."""
    evaluation = Evaluation(
        id=uuid.uuid4(),
        trace_id=uuid.UUID(eval_data.trace_id),
        span_id=uuid.UUID(eval_data.span_id) if eval_data.span_id else None,
        evaluator_type=eval_data.evaluator_type,
        score=eval_data.score,
        criteria=eval_data.criteria,
        result=eval_data.result,
    )
    session.add(evaluation)
    await session.flush()
    return evaluation


@router.get("/", response_model=list[EvaluationResponse])
async def list_evaluations(
    trace_id: Optional[str] = Query(None),
    evaluator_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[Evaluation]:
    """List evaluations with optional filtering."""
    query = select(Evaluation).order_by(Evaluation.created_at.desc())

    if trace_id:
        query = query.where(Evaluation.trace_id == uuid.UUID(trace_id))

    if evaluator_type:
        query = query.where(Evaluation.evaluator_type == evaluator_type)

    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    evaluation_id: str,
    session: AsyncSession = Depends(get_session),
) -> Evaluation:
    """Get an evaluation by ID."""
    query = select(Evaluation).where(Evaluation.id == uuid.UUID(evaluation_id))
    result = await session.execute(query)
    evaluation = result.scalar_one_or_none()

    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    return evaluation
