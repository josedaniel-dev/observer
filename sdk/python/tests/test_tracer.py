"""Tests for the tracer module."""

import pytest
from llm_observatory.tracer import Tracer, Span, SpanStatus, TokenUsage, trace


class TestSpan:
    """Tests for Span class."""

    def test_span_creation(self):
        """Test span creation with default values."""
        span = Span(name="test_span")
        assert span.name == "test_span"
        assert span.span_type == "generic"
        assert span.status == SpanStatus.UNSET
        assert span.id is not None
        assert span.trace_id is not None

    def test_span_end(self):
        """Test ending a span."""
        span = Span(name="test_span")
        span.end()
        assert span.end_time is not None
        assert span.status == SpanStatus.OK

    def test_span_end_with_error(self):
        """Test ending a span with error status."""
        span = Span(name="test_span")
        span.end(SpanStatus.ERROR)
        assert span.status == SpanStatus.ERROR

    def test_span_set_attribute(self):
        """Test setting span attributes."""
        span = Span(name="test_span")
        span.set_attribute("model", "gpt-4")
        assert span.attributes["model"] == "gpt-4"

    def test_span_set_token_usage(self):
        """Test setting token usage."""
        span = Span(name="test_span")
        span.set_token_usage(input_tokens=100, output_tokens=50)
        assert span.tokens.input == 100
        assert span.tokens.output == 50
        assert span.tokens.total == 150

    def test_span_set_cost(self):
        """Test setting cost."""
        span = Span(name="test_span")
        span.set_cost(0.005)
        assert span.cost_usd == 0.005

    def test_span_duration_ms(self):
        """Test duration calculation."""
        span = Span(name="test_span")
        span.start_time = 1000.0
        span.end_time = 1001.5
        assert span.duration_ms == 1500.0


class TestTracer:
    """Tests for Tracer class."""

    def test_tracer_creation(self):
        """Test tracer creation."""
        tracer = Tracer(service_name="test_service")
        assert tracer.service_name == "test_service"

    def test_start_trace(self):
        """Test starting a trace."""
        tracer = Tracer()
        span = tracer.start_trace("test_trace")
        assert span.name == "test_trace"
        assert span.span_type == "trace"
        assert span.trace_id is not None

    def test_start_span(self):
        """Test starting a span."""
        tracer = Tracer()
        parent = tracer.start_trace("parent")
        child = tracer.start_span("child", parent=parent)
        assert child.name == "child"
        assert child.parent_id == parent.id
        assert child.trace_id == parent.trace_id

    def test_export(self):
        """Test exporting spans."""
        tracer = Tracer()
        tracer.start_trace("test_trace")
        exported = tracer.export()
        assert len(exported) == 1
        assert exported[0]["name"] == "test_trace"

    def test_clear(self):
        """Test clearing spans."""
        tracer = Tracer()
        tracer.start_trace("test_trace")
        assert len(tracer.export()) == 1
        tracer.clear()
        assert len(tracer.export()) == 0


class TestTraceDecorator:
    """Tests for trace decorator."""

    def test_trace_decorator(self):
        """Test trace decorator."""
        @trace(name="test_function")
        def test_function():
            return 42

        result = test_function()
        assert result == 42

    def test_trace_decorator_with_error(self):
        """Test trace decorator with error."""
        @trace(name="failing_function")
        def failing_function():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            failing_function()
