"""Evaluation model - compatible with both PostgreSQL and SQLite."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String
from sqlalchemy import JSON

from app.models import Base


class Evaluation(Base):
    """Represents an evaluation result for a trace or span."""

    __tablename__ = "evaluations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id = Column(
        String(36),
        ForeignKey("traces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    span_id = Column(
        String(36),
        ForeignKey("spans.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    evaluator_type = Column(
        String(20),
        nullable=False,
    )
    score = Column(Numeric(5, 4), nullable=True)
    criteria = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
