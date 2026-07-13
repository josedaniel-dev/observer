"""SQLAlchemy models for LLM Observatory."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


from app.models.trace import Trace, Span
from app.models.evaluation import Evaluation

__all__ = ["Base", "Trace", "Span", "Evaluation"]
