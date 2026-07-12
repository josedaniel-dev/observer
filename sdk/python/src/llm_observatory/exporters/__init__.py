"""Exporters for sending traces to backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseExporter(ABC):
    """Base class for trace exporters."""

    @abstractmethod
    def export(self, spans: list[dict[str, Any]]) -> None:
        """Export spans to the backend.

        Args:
            spans: List of span dictionaries to export.
        """
        ...

    def flush(self) -> None:
        """Flush any buffered spans."""
        pass
