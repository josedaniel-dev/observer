"""Model pricing table for cost calculation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelPricing:
    """Pricing for a model (per 1M tokens)."""

    input_per_1m: float
    output_per_1m: float
    currency: str = "USD"


# Pricing as of July 2026 (approximate)
MODEL_PRICING: dict[str, ModelPricing] = {
    # OpenAI models
    "gpt-4o": ModelPricing(input_per_1m=2.50, output_per_1m=10.00),
    "gpt-4o-mini": ModelPricing(input_per_1m=0.15, output_per_1m=0.60),
    "gpt-4-turbo": ModelPricing(input_per_1m=10.00, output_per_1m=30.00),
    "gpt-4": ModelPricing(input_per_1m=30.00, output_per_1m=60.00),
    "gpt-3.5-turbo": ModelPricing(input_per_1m=0.50, output_per_1m=1.50),
    "o1": ModelPricing(input_per_1m=15.00, output_per_1m=60.00),
    "o1-mini": ModelPricing(input_per_1m=3.00, output_per_1m=12.00),
    "o3": ModelPricing(input_per_1m=10.00, output_per_1m=40.00),
    "o3-mini": ModelPricing(input_per_1m=1.10, output_per_1m=4.40),
    # Anthropic models
    "claude-4-opus": ModelPricing(input_per_1m=15.00, output_per_1m=75.00),
    "claude-4-sonnet": ModelPricing(input_per_1m=3.00, output_per_1m=15.00),
    "claude-3-5-sonnet": ModelPricing(input_per_1m=3.00, output_per_1m=15.00),
    "claude-3-5-haiku": ModelPricing(input_per_1m=0.80, output_per_1m=4.00),
    "claude-3-opus": ModelPricing(input_per_1m=15.00, output_per_1m=75.00),
    "claude-3-sonnet": ModelPricing(input_per_1m=3.00, output_per_1m=15.00),
    "claude-3-haiku": ModelPricing(input_per_1m=0.25, output_per_1m=1.25),
    # Google models
    "gemini-2.0-flash": ModelPricing(input_per_1m=0.10, output_per_1m=0.40),
    "gemini-2.0-pro": ModelPricing(input_per_1m=1.25, output_per_1m=10.00),
    "gemini-1.5-pro": ModelPricing(input_per_1m=1.25, output_per_1m=5.00),
    "gemini-1.5-flash": ModelPricing(input_per_1m=0.075, output_per_1m=0.30),
}


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float | None:
    """Calculate cost for a model invocation.

    Args:
        model: Model name (e.g., "gpt-4o").
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.

    Returns:
        Cost in USD, or None if model pricing is unknown.
    """
    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        return None

    input_cost = (input_tokens / 1_000_000) * pricing.input_per_1m
    output_cost = (output_tokens / 1_000_000) * pricing.output_per_1m
    return input_cost + output_cost


def get_model_pricing(model: str) -> ModelPricing | None:
    """Get pricing for a model.

    Args:
        model: Model name.

    Returns:
        ModelPricing or None if unknown.
    """
    return MODEL_PRICING.get(model)
