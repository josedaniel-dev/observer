"""Trace and Span models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Trace(Base):
    """Represents a complete trace (collection of spans)."""

    __tablename__ = "traces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    session_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        Enum("ok", "error", "unset", name="trace_status"),
        nullable=False,
        default="unset",
    )
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    spans = relationship("Span", back_populates="trace", cascade="all, delete-orphan")


class Span(Base):
    """Represents a single span within a trace."""

    __tablename__ = "spans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(
        UUID(as_uuid=True), ForeignKey("traces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_span_id = Column(UUID(as_uuid=True), ForeignKey("spans.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    span_type = Column(String(50), nullable=False, default="generic")
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        Enum("ok", "error", "unset", name="span_status"),
        nullable=False,
        default="unset",
    )
    input_ = Column("input", JSONB, nullable=True)
    output_ = Column("output", JSONB, nullable=True)
    tokens_input = Column(Integer, nullable=True)
    tokens_output = Column(Integer, nullable=True)
    cost_usd = Column(Numeric(10, 6), nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
    attributes = Column(JSONB, nullable=True)

    # Relationships
    trace = relationship("Trace", back_populates="spans")
    parent = relationship("Span", remote_side=[id], backref="children")
