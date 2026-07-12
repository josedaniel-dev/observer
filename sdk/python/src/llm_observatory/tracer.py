"""Core tracing engine for LLM Observatory."""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

# Context variable for current span
_current_span: ContextVar[Optional[Span]] = ContextVar("current_span", default=None)


class SpanStatus(str, Enum):
    """Status of a span."""

    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


@dataclass
class TokenUsage:
    """Token usage statistics."""

    input: int = 0
    output: int = 0
    total: int = 0


@dataclass
class Span:
    """A single trace span representing an operation."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = ""
    parent_id: Optional[str] = None
    name: str = ""
    span_type: str = "generic"
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    input: Optional[dict[str, Any]] = None
    output: Optional[dict[str, Any]] = None
    tokens: Optional[TokenUsage] = None
    cost_usd: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)

    def end(self, status: SpanStatus = SpanStatus.OK) -> None:
        """End the span."""
        self.end_time = time.time()
        self.status = status

    def set_status(self, status: SpanStatus) -> None:
        """Set the span status."""
        self.status = status

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value

    def set_token_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Set token usage for this span."""
        self.tokens = TokenUsage(
            input=input_tokens,
            output=output_tokens,
            total=input_tokens + output_tokens,
        )

    def set_cost(self, cost_usd: float) -> None:
        """Set the cost in USD for this span."""
        self.cost_usd = cost_usd

    @property
    def duration_ms(self) -> Optional[float]:
        """Get duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000


class Tracer:
    """Main tracer class for creating and managing traces."""

    def __init__(
        self,
        service_name: str = "llm-observatory",
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        """Initialize the tracer.

        Args:
            service_name: Name of the service being traced.
            endpoint: Endpoint URL for the observatory backend.
            api_key: API key for authentication.
        """
        self.service_name = service_name
        self.endpoint = endpoint
        self.api_key = api_key
        self._spans: list[Span] = []
        self._exporters: list[Any] = []

    def start_trace(self, name: str, **attributes: Any) -> Span:
        """Start a new trace.

        Args:
            name: Name of the trace.
            **attributes: Additional attributes for the trace.

        Returns:
            The root span of the trace.
        """
        span = Span(
            trace_id=str(uuid.uuid4()),
            name=name,
            span_type="trace",
            attributes=attributes,
        )
        self._spans.append(span)
        return span

    def start_span(
        self,
        name: str,
        span_type: str = "generic",
        parent: Optional[Span] = None,
        **attributes: Any,
    ) -> Span:
        """Start a new span.

        Args:
            name: Name of the span.
            span_type: Type of span (e.g., "llm", "tool", "agent").
            parent: Parent span (defaults to current span).
            **attributes: Additional attributes for the span.

        Returns:
            The new span.
        """
        parent_span = parent or _current_span.get()
        span = Span(
            trace_id=parent_span.trace_id if parent_span else str(uuid.uuid4()),
            parent_id=parent_span.id if parent_span else None,
            name=name,
            span_type=span_type,
            attributes=attributes,
        )
        self._spans.append(span)
        return span

    def export(self) -> list[dict[str, Any]]:
        """Export all spans as dictionaries.

        Returns:
            List of span dictionaries.
        """
        return [
            {
                "id": span.id,
                "trace_id": span.trace_id,
                "parent_id": span.parent_id,
                "name": span.name,
                "span_type": span.span_type,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "status": span.status.value,
                "input": span.input,
                "output": span.output,
                "tokens": {
                    "input": span.tokens.input,
                    "output": span.tokens.output,
                    "total": span.tokens.total,
                }
                if span.tokens
                else None,
                "cost_usd": span.cost_usd,
                "metadata": span.metadata,
                "attributes": span.attributes,
            }
            for span in self._spans
        ]

    def clear(self) -> None:
        """Clear all collected spans."""
        self._spans.clear()


def trace(
    name: Optional[str] = None,
    span_type: str = "function",
) -> Callable:
    """Decorator to trace a function.

    Args:
        name: Name for the trace (defaults to function name).
        span_type: Type of span.

    Returns:
        Decorated function.
    """

    def decorator(func: Callable) -> Callable:
        import functools

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            span_name = name or func.__name__
            tracer = _get_global_tracer()

            span = tracer.start_span(span_name, span_type=span_type)
            token = _current_span.set(span)

            try:
                result = func(*args, **kwargs)
                span.set_status(SpanStatus.OK)
                return result
            except Exception as e:
                span.set_status(SpanStatus.ERROR)
                span.set_attribute("error.message", str(e))
                raise
            finally:
                span.end()
                _current_span.reset(token)

        return wrapper

    return decorator


# Global tracer instance
_global_tracer: Optional[Tracer] = None


def _get_global_tracer() -> Tracer:
    """Get or create the global tracer instance."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = Tracer()
    return _global_tracer


def get_tracer() -> Tracer:
    """Get the global tracer instance."""
    return _get_global_tracer()


def set_tracer(tracer: Tracer) -> None:
    """Set the global tracer instance."""
    global _global_tracer
    _global_tracer = tracer
