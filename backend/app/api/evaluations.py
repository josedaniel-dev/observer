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
from app.models.trace import Trace, Span
from app.evaluators import create_evaluator, EvaluatorType, EvaluationCriteria

router = APIRouter()


class EvaluationCreate(BaseModel):
    """Schema for creating an evaluation."""

    trace_id: str
    span_id: Optional[str] = None
    evaluator_type: str
    score: Optional[float] = None
    criteria: Optional[dict] = None
    result: Optional[dict] = None


class EvaluationRunRequest(BaseModel):
    """Schema for running an evaluation."""

    trace_id: str
    evaluator_type: str
    criteria: list[dict]


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
        id=str(uuid.uuid4()),
        trace_id=eval_data.trace_id,
        span_id=eval_data.span_id,
        evaluator_type=eval_data.evaluator_type,
        score=eval_data.score,
        criteria=eval_data.criteria,
        result=eval_data.result,
    )
    session.add(evaluation)
    await session.flush()
    return evaluation


@router.post("/run", response_model=EvaluationResponse)
async def run_evaluation(
    run_request: EvaluationRunRequest,
    session: AsyncSession = Depends(get_session),
) -> Evaluation:
    """Run an evaluation on a trace using the specified evaluator."""
    # Get the trace
    query = select(Trace).where(Trace.id == run_request.trace_id)
    result = await session.execute(query)
    trace = result.scalar_one_or_none()

    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    # Get spans for the trace
    spans_query = select(Span).where(Span.trace_id == run_request.trace_id)
    spans_result = await session.execute(spans_query)
    spans = list(spans_result.scalars().all())

    # Build trace data for evaluator
    trace_data = {
        "id": str(trace.id),
        "name": trace.name,
        "status": trace.status,
        "spans": [
            {
                "id": str(s.id),
                "name": s.name,
                "span_type": s.span_type,
                "tokens_input": s.tokens_input,
                "tokens_output": s.tokens_output,
                "cost_usd": float(s.cost_usd) if s.cost_usd else None,
            }
            for s in spans
        ],
        "total_spans": len(spans),
        "total_cost_usd": sum(float(s.cost_usd) for s in spans if s.cost_usd),
        "max_latency_ms": max(
            (
                (s.end_time - s.start_time).total_seconds() * 1000
                for s in spans
                if s.end_time and s.start_time
            ),
            default=0,
        ),
        "error_count": sum(1 for s in spans if s.status == "error"),
    }

    # Create evaluator and run
    try:
        evaluator_type = EvaluatorType(run_request.evaluator_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid evaluator type: {run_request.evaluator_type}")

    evaluator = create_evaluator(evaluator_type)

    criteria = [
        EvaluationCriteria(
            name=c.get("name", ""),
            description=c.get("description", ""),
            weight=c.get("weight", 1.0),
            threshold=c.get("threshold"),
        )
        for c in run_request.criteria
    ]

    eval_result = await evaluator.evaluate(
        trace_id=run_request.trace_id,
        trace_data=trace_data,
        criteria=criteria,
    )

    # Store the evaluation
    evaluation = Evaluation(
        id=str(uuid.uuid4()),
        trace_id=run_request.trace_id,
        evaluator_type=run_request.evaluator_type,
        score=eval_result.score,
        criteria={"criteria": [c.name for c in criteria]},
        result={
            "scores": eval_result.criteria,
            "details": eval_result.details,
            "passed": eval_result.passed,
        },
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
        query = query.where(Evaluation.trace_id == trace_id)

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
    query = select(Evaluation).where(Evaluation.id == evaluation_id)
    result = await session.execute(query)
    evaluation = result.scalar_one_or_none()

    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    return evaluation
