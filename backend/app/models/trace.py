"""Trace and Span models - compatible with both PostgreSQL and SQLite."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship

# Use JSON type that works with both PostgreSQL and SQLite
from sqlalchemy import JSON


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class Trace(Base):
    """Represents a complete trace (collection of spans)."""

    __tablename__ = "traces"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    session_id = Column(String(36), nullable=True, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="unset")
    metadata_ = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    spans = relationship("Span", back_populates="trace", cascade="all, delete-orphan")


class Span(Base):
    """Represents a single span within a trace."""

    __tablename__ = "spans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    trace_id = Column(
        String(36), ForeignKey("traces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_span_id = Column(String(36), ForeignKey("spans.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    span_type = Column(String(50), nullable=False, default="generic")
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="unset")
    input_ = Column("input", JSON, nullable=True)
    output_ = Column("output", JSON, nullable=True)
    tokens_input = Column(Integer, nullable=True)
    tokens_output = Column(Integer, nullable=True)
    cost_usd = Column(Numeric(10, 6), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    attributes = Column(JSON, nullable=True)

    # Relationships
    trace = relationship("Trace", back_populates="spans")
    parent = relationship("Span", remote_side=[id], backref="children")
