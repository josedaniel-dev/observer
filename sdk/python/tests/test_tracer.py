"""Tests for the tracer module."""

import asyncio

import pytest

from llm_observatory.pricing import MODEL_PRICING, calculate_cost, get_model_pricing
from llm_observatory.tracer import Span, SpanStatus, Tracer, trace


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

    def test_span_set_input(self):
        """Test setting span input."""
        span = Span(name="test_span")
        span.set_input({"prompt": "hello"})
        assert span.input == {"prompt": "hello"}

    def test_span_set_output(self):
        """Test setting span output."""
        span = Span(name="test_span")
        span.set_output({"response": "world"})
        assert span.output == {"response": "world"}

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
        """Test trace decorator with sync function."""
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

    def test_trace_decorator_async(self):
        """Test trace decorator with async function."""
        @trace(name="async_function")
        async def async_function():
            await asyncio.sleep(0.01)
            return 42

        result = asyncio.run(async_function())
        assert result == 42

    def test_trace_decorator_async_with_error(self):
        """Test trace decorator with async error."""
        @trace(name="async_failing")
        async def async_failing():
            await asyncio.sleep(0.01)
            raise ValueError("async error")

        with pytest.raises(ValueError):
            asyncio.run(async_failing())


class TestPricing:
    """Tests for pricing module."""

    def test_known_model_pricing(self):
        """Test pricing for known model."""
        pricing = get_model_pricing("gpt-4o")
        assert pricing is not None
        assert pricing.input_per_1m == 2.50
        assert pricing.output_per_1m == 10.00

    def test_unknown_model_pricing(self):
        """Test pricing for unknown model."""
        pricing = get_model_pricing("unknown-model")
        assert pricing is None

    def test_calculate_cost(self):
        """Test cost calculation."""
        cost = calculate_cost("gpt-4o", input_tokens=1000, output_tokens=500)
        # 1000/1M * 2.50 + 500/1M * 10.00 = 0.0025 + 0.005 = 0.0075
        assert cost == pytest.approx(0.0075, rel=1e-6)

    def test_calculate_cost_unknown_model(self):
        """Test cost calculation for unknown model."""
        cost = calculate_cost("unknown", input_tokens=1000, output_tokens=500)
        assert cost is None

    def test_all_models_have_pricing(self):
        """Test that all models in pricing table have valid data."""
        for model, pricing in MODEL_PRICING.items():
            assert pricing.input_per_1m >= 0, f"{model} has negative input price"
            assert pricing.output_per_1m >= 0, f"{model} has negative output price"
