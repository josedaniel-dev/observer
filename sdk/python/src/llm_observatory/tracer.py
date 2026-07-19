"""Core tracing engine for LLM Observatory."""

from __future__ import annotations

import asyncio
import functools
import logging
import threading
import time
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# Context variable for current span
_current_span: ContextVar[Span | None] = ContextVar("current_span", default=None)


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
    parent_id: str | None = None
    name: str = ""
    span_type: str = "generic"
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    status: SpanStatus = SpanStatus.UNSET
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    tokens: TokenUsage | None = None
    cost_usd: float | None = None
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

    def set_input(self, data: dict[str, Any]) -> None:
        """Set the span input."""
        self.input = data

    def set_output(self, data: dict[str, Any]) -> None:
        """Set the span output."""
        self.output = data

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
    def duration_ms(self) -> float | None:
        """Get duration in milliseconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time) * 1000


class Tracer:
    """Main tracer class for creating and managing traces."""

    def __init__(
        self,
        service_name: str = "llm-observatory",
        endpoint: str | None = None,
        api_key: str | None = None,
        batch_size: int = 10,
        flush_interval: float = 5.0,
    ) -> None:
        """Initialize the tracer.

        Args:
            service_name: Name of the service being traced.
            endpoint: Endpoint URL for the observatory backend.
            api_key: API key for authentication.
            batch_size: Number of spans to buffer before flushing.
            flush_interval: Seconds between automatic flushes.
        """
        self.service_name = service_name
        self.endpoint = endpoint
        self.api_key = api_key
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._spans: list[Span] = []
        self._exporters: list[Any] = []
        self._buffer: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._flush_thread: threading.Thread | None = None
        self._shutdown = False

        # Auto-start flush thread if we have an endpoint
        if endpoint:
            self._start_flush_thread()

    def _start_flush_thread(self) -> None:
        """Start background flush thread."""
        if self._flush_thread is not None:
            return

        def flush_loop() -> None:
            while not self._shutdown:
                time.sleep(self.flush_interval)
                try:
                    self.flush()
                except Exception as e:
                    logger.warning(f"Flush failed: {e}")

        self._flush_thread = threading.Thread(target=flush_loop, daemon=True)
        self._flush_thread.start()

    def add_exporter(self, exporter: Any) -> None:
        """Add an exporter to the tracer.

        Args:
            exporter: Exporter instance with an export(spans) method.
        """
        self._exporters.append(exporter)

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

        # Auto-export if we have exporters
        if self._exporters:
            span_dict = self._span_to_dict(span)
            with self._lock:
                self._buffer.append(span_dict)
                if len(self._buffer) >= self.batch_size:
                    self._flush_buffer()

        return span

    def start_span(
        self,
        name: str,
        span_type: str = "generic",
        parent: Span | None = None,
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

        # Auto-export if we have exporters
        if self._exporters:
            span_dict = self._span_to_dict(span)
            with self._lock:
                self._buffer.append(span_dict)
                if len(self._buffer) >= self.batch_size:
                    self._flush_buffer()

        return span

    def _span_to_dict(self, span: Span) -> dict[str, Any]:
        """Convert a span to a dictionary for export."""
        return {
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
            "tokens_input": span.tokens.input if span.tokens else None,
            "tokens_output": span.tokens.output if span.tokens else None,
            "cost_usd": span.cost_usd,
            "metadata": span.metadata,
            "attributes": span.attributes,
        }

    def export(self) -> list[dict[str, Any]]:
        """Export all spans as dictionaries.

        Returns:
            List of span dictionaries.
        """
        return [self._span_to_dict(span) for span in self._spans]

    def flush(self) -> None:
        """Flush buffered spans to exporters."""
        with self._lock:
            if not self._buffer:
                return
            spans_to_export = self._buffer.copy()
            self._buffer.clear()

        for exporter in self._exporters:
            try:
                exporter.export(spans_to_export)
            except Exception as e:
                logger.warning(f"Exporter failed: {e}")

    def _flush_buffer(self) -> None:
        """Flush buffer (must hold lock)."""
        if not self._buffer:
            return
        spans_to_export = self._buffer.copy()
        self._buffer.clear()

        for exporter in self._exporters:
            try:
                exporter.export(spans_to_export)
            except Exception as e:
                logger.warning(f"Exporter failed: {e}")

    def clear(self) -> None:
        """Clear all collected spans."""
        self._spans.clear()

    def shutdown(self) -> None:
        """Shutdown the tracer, flushing any remaining spans."""
        self._shutdown = True
        self.flush()
        for exporter in self._exporters:
            try:
                exporter.flush()
            except Exception:
                pass


def trace(
    name: str | None = None,
    span_type: str = "function",
) -> Callable:
    """Decorator to trace a function (sync or async).

    Args:
        name: Name for the trace (defaults to function name).
        span_type: Type of span.

    Returns:
        Decorated function.
    """

    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        if asyncio.iscoroutinefunction(func):
            # Async version
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = _get_global_tracer()
                span = tracer.start_span(span_name, span_type=span_type)
                token = _current_span.set(span)

                try:
                    result = await func(*args, **kwargs)
                    span.set_status(SpanStatus.OK)
                    return result
                except Exception as e:
                    span.set_status(SpanStatus.ERROR)
                    span.set_attribute("error.message", str(e))
                    raise
                finally:
                    span.end()
                    _current_span.reset(token)

            return async_wrapper
        else:
            # Sync version
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
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

            return sync_wrapper

    return decorator


# Global tracer instance
_global_tracer: Tracer | None = None


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
