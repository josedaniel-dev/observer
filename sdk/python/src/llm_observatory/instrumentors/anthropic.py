"""Anthropic auto-instrumentation."""

from __future__ import annotations

import time
from typing import Any, Optional

from llm_observatory.tracer import SpanStatus, get_tracer


class AnthropicInstrumentor:
    """Instruments Anthropic API calls to capture traces."""

    def __init__(self) -> None:
        self._original_create: Optional[Any] = None

    def instrument(self) -> None:
        """Patch Anthropic to capture traces."""
        try:
            import anthropic

            self._original_create = anthropic.resources.messages.Messages.create
            anthropic.resources.messages.Messages.create = self._patched_create
        except ImportError:
            pass

    def _patched_create(self, *args: Any, **kwargs: Any) -> Any:
        """Patched create method that captures traces."""
        tracer = get_tracer()
        model = kwargs.get("model", "unknown")
        messages = kwargs.get("messages", [])

        span = tracer.start_span(
            name="anthropic.messages.create",
            span_type="llm",
            input={"model": model, "messages": messages},
        )

        try:
            result = self._original_create(*args, **kwargs)

            # Extract token usage
            if hasattr(result, "usage"):
                span.set_token_usage(
                    input_tokens=result.usage.input_tokens or 0,
                    output_tokens=result.usage.output_tokens or 0,
                )

            span.set_attribute("model", model)
            span.set_attribute("response_id", getattr(result, "id", None))
            span.set_status(SpanStatus.OK)

            return result

        except Exception as e:
            span.set_status(SpanStatus.ERROR)
            span.set_attribute("error.message", str(e))
            raise

        finally:
            span.end()

    def uninstrument(self) -> None:
        """Remove instrumentation."""
        if self._original_create is not None:
            try:
                import anthropic

                anthropic.resources.messages.Messages.create = self._original_create
            except ImportError:
                pass
