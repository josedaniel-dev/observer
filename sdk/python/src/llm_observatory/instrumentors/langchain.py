"""LangChain auto-instrumentation for LLM Observatory."""

from __future__ import annotations

import uuid
from typing import Any

from llm_observatory.pricing import calculate_cost
from llm_observatory.tracer import SpanStatus, _current_span, _get_global_tracer


class LangChainInstrumentor:
    """Instruments LangChain callbacks to capture traces."""

    def __init__(self) -> None:
        self._patched = False
        self._original_on_llm_start: Any = None
        self._original_on_llm_end: Any = None
        self._original_on_llm_error: Any = None

    def instrument(self) -> None:
        """Enable LangChain instrumentation."""
        if self._patched:
            return

        try:
            from langchain_core.callbacks import BaseCallbackHandler

            # Monkey-patch BaseCallbackHandler
            original_on_llm_start = BaseCallbackHandler.on_llm_start
            original_on_llm_end = BaseCallbackHandler.on_llm_end
            original_on_llm_error = BaseCallbackHandler.on_llm_error

            # Store original methods
            self._patched = True
            self._original_on_llm_start = original_on_llm_start
            self._original_on_llm_end = original_on_llm_end
            self._original_on_llm_error = original_on_llm_error

            def patched_on_llm_start(
                self_handler: Any,
                serialized: dict[str, Any],
                prompts: list[str],
                *,
                run_id: uuid.UUID | None = None,
                **kwargs: Any,
            ) -> Any:
                """Patched on_llm_start that creates a span."""
                tracer = _get_global_tracer()
                model_id = serialized.get("id", ["unknown"])
                model = (
                    serialized.get("name", model_id[-1])
                    if isinstance(model_id, list)
                    else "unknown"
                )

                span = tracer.start_span(
                    f"langchain.{model}",
                    span_type="llm",
                    model=model,
                    provider="langchain",
                )
                span.set_input({"prompts": prompts, "serialized": serialized})
                return original_on_llm_start(
                    self_handler, serialized, prompts,
                    run_id=run_id, **kwargs,
                )

            def patched_on_llm_end(
                self_handler: Any,
                response: Any,
                *,
                run_id: uuid.UUID | None = None,
                **kwargs: Any,
            ) -> Any:
                """Patched on_llm_end that ends the span."""
                current = _current_span.get()
                if current:
                    # Extract token usage from LLMResult
                    if hasattr(response, "llm_output") and response.llm_output:
                        token_usage = response.llm_output.get("token_usage", {})
                        if token_usage:
                            input_tokens = token_usage.get(
                                "prompt_tokens",
                                token_usage.get("input_tokens", 0),
                            )
                            output_tokens = token_usage.get(
                                "completion_tokens",
                                token_usage.get("output_tokens", 0),
                            )
                            current.set_token_usage(input_tokens, output_tokens)

                            # Calculate cost
                            model = current.attributes.get("model", "unknown")
                            cost = calculate_cost(model, input_tokens, output_tokens)
                            if cost is not None:
                                current.set_cost(cost)

                    # Capture output
                    if hasattr(response, "generations") and response.generations:
                        generations = []
                        for gen_list in response.generations:
                            for gen in gen_list:
                                generations.append(gen.text if hasattr(gen, "text") else str(gen))
                        current.set_output({"generations": generations})

                    current.set_status(SpanStatus.OK)
                    current.end()

                return original_on_llm_end(self_handler, response, run_id=run_id, **kwargs)

            def patched_on_llm_error(
                self_handler: Any,
                error: BaseException,
                *,
                run_id: uuid.UUID | None = None,
                **kwargs: Any,
            ) -> Any:
                """Patched on_llm_error that records error."""
                current = _current_span.get()
                if current:
                    current.set_status(SpanStatus.ERROR)
                    current.set_attribute("error.message", str(error))
                    current.end()

                return original_on_llm_error(self_handler, error, run_id=run_id, **kwargs)

            BaseCallbackHandler.on_llm_start = patched_on_llm_start
            BaseCallbackHandler.on_llm_end = patched_on_llm_end
            BaseCallbackHandler.on_llm_error = patched_on_llm_error

        except ImportError:
            # LangChain not available
            pass

    def uninstrument(self) -> None:
        """Disable LangChain instrumentation."""
        if not self._patched:
            return

        try:
            from langchain_core.callbacks import BaseCallbackHandler

            if self._original_on_llm_start is not None:
                BaseCallbackHandler.on_llm_start = self._original_on_llm_start
            if self._original_on_llm_end is not None:
                BaseCallbackHandler.on_llm_end = self._original_on_llm_end
            if self._original_on_llm_error is not None:
                BaseCallbackHandler.on_llm_error = self._original_on_llm_error

            self._patched = False
            self._original_on_llm_start = None
            self._original_on_llm_end = None
            self._original_on_llm_error = None
        except ImportError:
            pass
