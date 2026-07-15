"""Auto-instrumentation for LLM libraries."""

from __future__ import annotations

from typing import Any

# Store instrumentor instances for uninstrument()
_active_instrumentors: list[Any] = []


def instrument(
    openai: bool = False,
    anthropic: bool = False,
    langchain: bool = False,
    **kwargs: Any,
) -> None:
    """Auto-instrument LLM libraries.

    Args:
        openai: Enable OpenAI instrumentation.
        anthropic: Enable Anthropic instrumentation.
        langchain: Enable LangChain instrumentation.
        **kwargs: Additional configuration options.
    """
    if openai:
        from llm_observatory.instrumentors.openai import OpenAIInstrumentor

        inst = OpenAIInstrumentor()
        inst.instrument()
        _active_instrumentors.append(inst)

    if anthropic:
        from llm_observatory.instrumentors.anthropic import AnthropicInstrumentor

        inst = AnthropicInstrumentor()
        inst.instrument()
        _active_instrumentors.append(inst)

    if langchain:
        try:
            from llm_observatory.instrumentors.langchain import LangChainInstrumentor

            inst = LangChainInstrumentor()
            inst.instrument()
            _active_instrumentors.append(inst)
        except ImportError:
            pass


def uninstrument() -> None:
    """Uninstrument all active instrumentors."""
    for inst in _active_instrumentors:
        try:
            inst.uninstrument()
        except Exception:
            pass
    _active_instrumentors.clear()
