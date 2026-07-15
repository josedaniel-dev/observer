"""LLM Observatory Python SDK - Open-source LLM observability."""

from llm_observatory.tracer import Tracer, Span, SpanStatus, TokenUsage, trace, get_tracer, set_tracer
from llm_observatory.instrumentors import instrument, uninstrument
from llm_observatory.pricing import calculate_cost, get_model_pricing, MODEL_PRICING
from llm_observatory.exporters.otlp import OTLPExporter

__version__ = "0.1.0"

__all__ = [
    "Tracer",
    "Span",
    "SpanStatus",
    "TokenUsage",
    "trace",
    "get_tracer",
    "set_tracer",
    "instrument",
    "uninstrument",
    "calculate_cost",
    "get_model_pricing",
    "MODEL_PRICING",
    "OTLPExporter",
]
