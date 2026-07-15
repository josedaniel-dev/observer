"""Evaluation engine for LLM Observatory."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EvaluatorType(str, Enum):
    """Types of evaluators."""

    LLM_JUDGE = "llm_judge"
    RULE_BASED = "rule_based"
    HUMAN = "human"


class EvaluationCriteria(BaseModel):
    """Criteria for evaluation."""

    name: str
    description: str
    weight: float = 1.0
    threshold: Optional[float] = None


class EvaluationResult(BaseModel):
    """Result of an evaluation."""

    score: float
    criteria: dict[str, Any]
    details: Optional[dict[str, Any]] = None
    passed: bool = True


class BaseEvaluator(ABC):
    """Base class for evaluators."""

    @abstractmethod
    async def evaluate(
        self,
        trace_id: str,
        trace_data: dict[str, Any],
        criteria: list[EvaluationCriteria],
    ) -> EvaluationResult:
        """Evaluate a trace against criteria.

        Args:
            trace_id: ID of the trace to evaluate.
            trace_data: Trace data including spans, tokens, etc.
            criteria: List of evaluation criteria.

        Returns:
            Evaluation result with score and details.
        """
        ...


class LLMJudgeEvaluator(BaseEvaluator):
    """Evaluates traces using an LLM as a judge."""

    def __init__(self, model: str = "gpt-4", api_key: Optional[str] = None) -> None:
        """Initialize the LLM judge evaluator.

        Args:
            model: LLM model to use for evaluation.
            api_key: API key for the LLM provider.
        """
        self.model = model
        self.api_key = api_key

    async def evaluate(
        self,
        trace_id: str,
        trace_data: dict[str, Any],
        criteria: list[EvaluationCriteria],
    ) -> EvaluationResult:
        """Evaluate a trace using LLM as judge.

        This implementation calls OpenAI's API to evaluate the trace.
        Falls back to rule-based scoring if API is unavailable.
        """
        try:
            import httpx

            # Build the evaluation prompt
            prompt = self._build_evaluation_prompt(trace_data, criteria)

            # Call OpenAI API
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "You are an expert evaluator for LLM traces. Evaluate the trace data against the given criteria and return a JSON object with scores for each criterion (0.0 to 1.0)."},
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.0,
                        "response_format": {"type": "json_object"},
                    },
                )
                response.raise_for_status()
                result = response.json()

                # Parse the LLM response
                content = result["choices"][0]["message"]["content"]
                scores = json.loads(content)

                # Normalize scores
                criteria_scores = {}
                for criterion in criteria:
                    if criterion.name in scores:
                        score = float(scores[criterion.name])
                        score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                        criteria_scores[criterion.name] = score
                    else:
                        criteria_scores[criterion.name] = 0.5  # Default if missing

                avg_score = sum(criteria_scores.values()) / len(criteria_scores) if criteria_scores else 0.0

                return EvaluationResult(
                    score=avg_score,
                    criteria=criteria_scores,
                    details={
                        "model": self.model,
                        "trace_id": trace_id,
                        "raw_response": content,
                    },
                    passed=avg_score >= 0.7,
                )

        except ImportError:
            logger.warning("httpx not available, falling back to rule-based evaluation")
            return await self._fallback_evaluate(trace_id, trace_data, criteria)
        except Exception as e:
            logger.warning(f"LLM judge failed ({e}), falling back to rule-based evaluation")
            return await self._fallback_evaluate(trace_id, trace_data, criteria)

    def _build_evaluation_prompt(
        self, trace_data: dict[str, Any], criteria: list[EvaluationCriteria]
    ) -> str:
        """Build the evaluation prompt for the LLM."""
        criteria_list = "\n".join([
            f"- {c.name}: {c.description}" + (f" (threshold: {c.threshold})" if c.threshold else "")
            for c in criteria
        ])

        return f"""Evaluate this LLM trace against the given criteria.

Trace Data:
{json.dumps(trace_data, indent=2, default=str)}

Criteria:
{criteria_list}

Return a JSON object with a score for each criterion (0.0 to 1.0).
Example: {{"criterion_name": 0.85, "another_criterion": 0.92}}"""

    async def _fallback_evaluate(
        self,
        trace_id: str,
        trace_data: dict[str, Any],
        criteria: list[EvaluationCriteria],
    ) -> EvaluationResult:
        """Fallback to rule-based evaluation when LLM is unavailable."""
        evaluator = RuleBasedEvaluator()
        return await evaluator.evaluate(trace_id, trace_data, criteria)


class RuleBasedEvaluator(BaseEvaluator):
    """Evaluates traces based on predefined rules."""

    def __init__(self, rules: Optional[list[dict[str, Any]]] = None) -> None:
        """Initialize the rule-based evaluator.

        Args:
            rules: List of rules to apply.
        """
        self.rules = rules or []

    async def evaluate(
        self,
        trace_id: str,
        trace_data: dict[str, Any],
        criteria: list[EvaluationCriteria],
    ) -> EvaluationResult:
        """Evaluate a trace based on rules."""
        scores = {}
        details = {}

        for criterion in criteria:
            # Apply rules based on criterion name
            if criterion.name == "max_latency":
                max_latency_ms = trace_data.get("max_latency_ms", 0)
                threshold = criterion.threshold or 5000
                scores[criterion.name] = 1.0 if max_latency_ms <= threshold else 0.0
                details[f"{criterion.name}_value"] = max_latency_ms
                details[f"{criterion.name}_threshold"] = threshold

            elif criterion.name == "max_cost":
                total_cost = trace_data.get("total_cost_usd", 0)
                threshold = criterion.threshold or 0.1
                scores[criterion.name] = 1.0 if total_cost <= threshold else 0.0
                details[f"{criterion.name}_value"] = total_cost
                details[f"{criterion.name}_threshold"] = threshold

            elif criterion.name == "error_rate":
                error_count = trace_data.get("error_count", 0)
                total_count = trace_data.get("total_spans", 1)
                error_rate = error_count / total_count if total_count > 0 else 0
                threshold = criterion.threshold or 0.1
                scores[criterion.name] = 1.0 if error_rate <= threshold else 0.0
                details[f"{criterion.name}_value"] = error_rate
                details[f"{criterion.name}_threshold"] = threshold

            else:
                # Default: pass
                scores[criterion.name] = 1.0

        avg_score = sum(scores.values()) / len(scores) if scores else 0.0

        return EvaluationResult(
            score=avg_score,
            criteria=scores,
            details=details,
            passed=avg_score >= 0.7,
        )


class HumanEvaluator(BaseEvaluator):
    """Placeholder for human evaluation (stores feedback)."""

    async def evaluate(
        self,
        trace_id: str,
        trace_data: dict[str, Any],
        criteria: list[EvaluationCriteria],
    ) -> EvaluationResult:
        """Human evaluation is not automated - returns pending status."""
        return EvaluationResult(
            score=0.0,
            criteria={c.name: 0.0 for c in criteria},
            details={"status": "pending_human_review", "trace_id": trace_id},
            passed=False,
        )


def create_evaluator(
    evaluator_type: EvaluatorType,
    **kwargs: Any,
) -> BaseEvaluator:
    """Create an evaluator instance.

    Args:
        evaluator_type: Type of evaluator to create.
        **kwargs: Additional arguments for the evaluator.

    Returns:
        Evaluator instance.
    """
    if evaluator_type == EvaluatorType.LLM_JUDGE:
        return LLMJudgeEvaluator(**kwargs)
    elif evaluator_type == EvaluatorType.RULE_BASED:
        return RuleBasedEvaluator(**kwargs)
    elif evaluator_type == EvaluatorType.HUMAN:
        return HumanEvaluator(**kwargs)
    else:
        raise ValueError(f"Unsupported evaluator type: {evaluator_type}")
