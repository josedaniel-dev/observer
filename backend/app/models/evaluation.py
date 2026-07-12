"""Evaluation model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Evaluation(Base):
    """Represents an evaluation result for a trace or span."""

    __tablename__ = "evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("traces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    span_id = Column(
        UUID(as_uuid=True),
        ForeignKey("spans.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    evaluator_type = Column(
        Enum("llm_judge", "rule_based", "human", name="evaluator_type"),
        nullable=False,
    )
    score = Column(Numeric(5, 4), nullable=True)
    criteria = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
