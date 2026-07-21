"""Idempotency receipts for external telemetry ingestion."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, String, UniqueConstraint

from app.models import Base


class IngestionReceipt(Base):
    """Records one accepted request so exporters can retry safely."""

    __tablename__ = "ingestion_receipts"
    __table_args__ = (
        UniqueConstraint("project_id", "idempotency_key", name="uq_ingestion_project_key"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(128), nullable=False, index=True)
    idempotency_key = Column(String(255), nullable=False)
    payload_sha256 = Column(String(64), nullable=False)
    trace_id = Column(String(36), nullable=False, index=True)
    response = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
