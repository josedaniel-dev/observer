"""Auto-instrumentation for LLM libraries."""

from __future__ import annotations

from typing import Any


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

        OpenAIInstrumentor().instrument()

    if anthropic:
        from llm_observatory.instrumentors.anthropic import AnthropicInstrumentor

        AnthropicInstrumentor().instrument()

    if langchain:
        try:
            from llm_observatory.instrumentors.langchain import LangChainInstrumentor

            LangChainInstrumentor().instrument()
        except ImportError:
            pass
