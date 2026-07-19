"""Rubric loader and evaluator engine.

Loads YAML rubric definitions and JSON scoring levels, extracts deterministic
metrics from trace data, generates LLM prompts for qualitative criteria,
and computes composite scores.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from dataclasses import field as dc_field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_RUBRICS_DIR = Path(__file__).parent / "rubrics"


@dataclass
class LevelDefinition:
    """A single scoring level from the JSON scale."""

    name: str
    label: str
    numeric_min: float
    numeric_max: float
    score: float
    color: str
    icon: str
    description: str
    auto_fail: bool = False


@dataclass
class ScoringScale:
    """A complete scoring scale (e.g. default_scale, safety_scale)."""

    name: str
    description: str
    min_val: float
    max_val: float
    pass_threshold: float
    levels: list[LevelDefinition]

    def resolve_level(self, raw_score: float) -> LevelDefinition:
        """Map a raw 0-1 score to the matching level definition."""
        clamped = max(self.min_val, min(self.max_val, raw_score))
        for level in self.levels:
            if level.numeric_min <= clamped <= level.numeric_max:
                return level
        return self.levels[-1]  # fallback to lowest


@dataclass
class CriterionExtraction:
    """Defines how to extract a value from trace data."""

    extract_field: str | None = None
    compute: str | None = None
    fields: list[str] = dc_field(default_factory=list)
    unit: str = ""
    spans: bool = False
    include_fields: list[str] = dc_field(default_factory=list)
    filter_type: str = ""


@dataclass
class ThresholdLevel:
    """A threshold boundary for deterministic scoring."""

    level: str
    max: float


@dataclass
class CriterionDefinition:
    """A single evaluation criterion from the YAML rubric."""

    name: str
    display_name: str
    description: str
    category: str
    weight: float
    required: bool
    extract: CriterionExtraction
    scoring_type: str  # "threshold" or "llm_judge"
    scoring_invert: bool = False
    threshold_levels: list[ThresholdLevel] = dc_field(default_factory=list)
    default_level: str = "failing"
    llm_prompt_template: str | None = None
    llm_levels: list[str] = dc_field(default_factory=list)
    scale_name: str = "default_scale"


@dataclass
class Rubric:
    """A complete evaluation rubric."""

    name: str
    version: str
    description: str
    scoring_scale: str
    min_pass_score: float
    defaults: dict[str, Any]
    criteria: list[CriterionDefinition]


@dataclass
class CriterionResult:
    """Result of evaluating a single criterion."""

    criterion_name: str
    display_name: str
    category: str
    level: str
    level_score: float
    weight: float
    raw_value: Any = None
    auto_fail: bool = False
    details: dict[str, Any] = dc_field(default_factory=dict)


class RubricLoader:
    """Loads and validates rubric YAML + scoring levels JSON."""

    def __init__(
        self,
        rubric_path: Path | None = None,
        levels_path: Path | None = None,
    ) -> None:
        self._rubric_path = rubric_path or _RUBRICS_DIR / "default.yaml"
        self._levels_path = levels_path or _RUBRICS_DIR / "scoring_levels.json"
        self._scales: dict[str, ScoringScale] = {}
        self._rubric: Rubric | None = None

    def load(self) -> Rubric:
        """Load rubric and scoring levels from disk."""
        self._load_scales()
        self._rubric = self._load_rubric()
        return self._rubric

    @property
    def rubric(self) -> Rubric:
        if self._rubric is None:
            raise RuntimeError("Rubric not loaded. Call load() first.")
        return self._rubric

    def get_scale(self, name: str) -> ScoringScale:
        if name not in self._scales:
            raise KeyError(f"Scoring scale '{name}' not found")
        return self._scales[name]

    def _load_scales(self) -> None:
        with open(self._levels_path) as f:
            data = json.load(f)

        for scale_name, scale_data in data["scales"].items():
            levels = [
                LevelDefinition(
                    name=lvl["name"],
                    label=lvl["label"],
                    numeric_min=lvl["numeric_min"],
                    numeric_max=lvl["numeric_max"],
                    score=lvl["score"],
                    color=lvl["color"],
                    icon=lvl["icon"],
                    description=lvl["description"],
                    auto_fail=lvl.get("auto_fail", False),
                )
                for lvl in scale_data["levels"]
            ]
            self._scales[scale_name] = ScoringScale(
                name=scale_data["name"],
                description=scale_data["description"],
                min_val=scale_data["min"],
                max_val=scale_data["max"],
                pass_threshold=scale_data["pass_threshold"],
                levels=levels,
            )

        logger.info("Loaded %d scoring scales", len(self._scales))

    def _load_rubric(self) -> Rubric:
        with open(self._rubric_path) as f:
            data = yaml.safe_load(f)

        meta = data["meta"]
        criteria = []
        for name, crit_data in data.get("criteria", {}).items():
            extract_data = crit_data.get("extract", {})
            scoring = crit_data.get("scoring", {})

            extraction = CriterionExtraction(
                extract_field=extract_data.get("field"),
                compute=extract_data.get("compute"),
                fields=extract_data.get("fields", []),
                unit=extract_data.get("unit", ""),
                spans=extract_data.get("spans", False),
                include_fields=extract_data.get("include_fields", []),
                filter_type=extract_data.get("filter_type", ""),
            )

            scoring_type = scoring.get("type", "threshold")
            threshold_levels = []
            if scoring_type == "threshold":
                for lvl in scoring.get("levels", []):
                    threshold_levels.append(
                        ThresholdLevel(level=lvl["level"], max=lvl["max"])
                    )

            criteria.append(
                CriterionDefinition(
                    name=name,
                    display_name=crit_data.get("display_name", name),
                    description=crit_data.get("description", ""),
                    category=crit_data.get("category", "general"),
                    weight=crit_data.get("weight", 1.0),
                    required=crit_data.get("required", False),
                    extract=extraction,
                    scoring_type=scoring_type,
                    scoring_invert=scoring.get("invert", False),
                    threshold_levels=threshold_levels,
                    default_level=scoring.get("default_level", "failing"),
                    llm_prompt_template=scoring.get("prompt_template"),
                    llm_levels=scoring.get("levels", []),
                    scale_name=meta.get("scoring_scale", "default_scale"),
                )
            )

        rubric = Rubric(
            name=meta["name"],
            version=meta["version"],
            description=meta["description"],
            scoring_scale=meta.get("scoring_scale", "default_scale"),
            min_pass_score=meta.get("min_pass_score", 0.6),
            defaults=data.get("defaults", {}),
            criteria=criteria,
        )

        logger.info(
            "Loaded rubric '%s' v%s with %d criteria",
            rubric.name,
            rubric.version,
            len(criteria),
        )
        return rubric


class TraceDataExtractor:
    """Extracts deterministic metrics from trace data for rubric evaluation."""

    def extract_value(self, trace_data: dict[str, Any], extraction: CriterionExtraction) -> Any:
        """Extract a raw value from trace data based on extraction rules."""
        if extraction.compute:
            return self._compute_value(trace_data, extraction)
        if extraction.extract_field:
            return self._get_nested(trace_data, extraction.extract_field)
        return None

    def _get_nested(self, data: dict[str, Any], path: str) -> Any:
        """Get a nested value using dot notation (e.g. 'spans.0.name')."""
        parts = path.split(".")
        current: Any = data
        for part in parts:
            if current is None:
                return None
            if isinstance(current, list):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError):
                    return None
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _compute_value(self, trace_data: dict[str, Any], extraction: CriterionExtraction) -> float:
        """Compute a derived value from trace data fields."""
        compute_expr = extraction.compute or ""

        if compute_expr == "error_count / total_spans":
            errors = trace_data.get("error_count", 0)
            total = trace_data.get("total_spans", 1)
            return errors / total if total > 0 else 0.0

        if compute_expr == "sum(tokens_input) + sum(tokens_output)":
            spans = trace_data.get("spans", [])
            total_input = sum(s.get("tokens_input", 0) or 0 for s in spans)
            total_output = sum(s.get("tokens_output", 0) or 0 for s in spans)
            return float(total_input + total_output)

        return 0.0

    def extract_llm_context(
        self, trace_data: dict[str, Any], extraction: CriterionExtraction
    ) -> list[dict[str, str]]:
        """Extract input/output pairs from spans for LLM judge evaluation."""
        spans = trace_data.get("spans", [])
        contexts = []

        for span in spans:
            if extraction.filter_type and span.get("span_type") != extraction.filter_type:
                continue
            context: dict[str, str] = {}
            for field_name in extraction.include_fields:
                value = span.get(field_name)
                if isinstance(value, dict):
                    context[field_name] = json.dumps(value, indent=2, default=str)
                elif value is not None:
                    context[field_name] = str(value)
                else:
                    context[field_name] = ""
            if context:
                contexts.append(context)

        return contexts


class RubricEvaluator:
    """Evaluates trace data against a loaded rubric, combining deterministic
    and LLM-judged criteria into a composite score."""

    def __init__(self, rubric: Rubric, scales: dict[str, ScoringScale]) -> None:
        self._rubric = rubric
        self._scales = scales
        self._extractor = TraceDataExtractor()

    @classmethod
    def from_loader(cls, loader: RubricLoader) -> RubricEvaluator:
        rubric = loader.rubric
        scales = {name: loader.get_scale(name) for name in set(
            c.scale_name for c in rubric.criteria
        ) | {rubric.scoring_scale}}
        return cls(rubric, scales)

    def extract_deterministic(self, trace_data: dict[str, Any]) -> list[CriterionResult]:
        """Evaluate all threshold-based criteria (no LLM needed)."""
        results = []
        for criterion in self._rubric.criteria:
            if criterion.scoring_type != "threshold":
                continue
            result = self._evaluate_threshold(criterion, trace_data)
            results.append(result)
        return results

    def build_llm_prompts(self, trace_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Build LLM prompt payloads for all llm_judge criteria."""
        prompts = []
        for criterion in self._rubric.criteria:
            if criterion.scoring_type != "llm_judge":
                continue
            contexts = self._extractor.extract_llm_context(trace_data, criterion.extract)
            for ctx in contexts:
                prompt_text = criterion.llm_prompt_template or ""
                for key, value in ctx.items():
                    prompt_text = prompt_text.replace(f"{{{key}}}", value)
                prompts.append({
                    "criterion_name": criterion.name,
                    "display_name": criterion.display_name,
                    "category": criterion.category,
                    "weight": criterion.weight,
                    "prompt": prompt_text,
                    "levels": criterion.llm_levels,
                    "scale_name": criterion.scale_name,
                })
        return prompts

    def score_llm_result(
        self,
        criterion_name: str,
        level_name: str,
    ) -> CriterionResult:
        """Convert an LLM judge response (level name) into a CriterionResult."""
        criterion = self._find_criterion(criterion_name)
        scale = self._scales[criterion.scale_name]
        level_def = self._find_level(scale, level_name)

        return CriterionResult(
            criterion_name=criterion.name,
            display_name=criterion.display_name,
            category=criterion.category,
            level=level_def.name,
            level_score=level_def.score,
            weight=criterion.weight,
            auto_fail=level_def.auto_fail,
            details={"level_label": level_def.label, "level_description": level_def.description},
        )

    def compute_composite(self, results: list[CriterionResult]) -> dict[str, Any]:
        """Compute the weighted composite score from individual criterion results."""
        if not results:
            return {"score": 0.0, "grade": "F", "passed": False, "criteria": []}

        total_weighted = 0.0
        total_weight = 0.0
        has_auto_fail = False
        criteria_details = []

        for r in results:
            total_weighted += r.level_score * r.weight
            total_weight += r.weight
            if r.auto_fail:
                has_auto_fail = True
            criteria_details.append({
                "criterion": r.criterion_name,
                "display_name": r.display_name,
                "category": r.category,
                "level": r.level,
                "score": r.level_score,
                "weight": r.weight,
                "auto_fail": r.auto_fail,
                "details": r.details,
            })

        composite = total_weighted / total_weight if total_weight > 0 else 0.0

        grade = "F"
        for g in _GRADE_BOUNDARIES:
            if composite >= g["min"]:
                grade = g["grade"]
                break

        passed = (
            composite >= self._rubric.min_pass_score and not has_auto_fail
        )

        # Check required criteria
        required_names = {c.name for c in self._rubric.criteria if c.required}
        scored_names = {r.criterion_name for r in results}
        missing_required = required_names - scored_names

        return {
            "score": round(composite, 4),
            "grade": grade,
            "passed": passed,
            "has_auto_fail": has_auto_fail,
            "missing_required": list(missing_required),
            "criteria": criteria_details,
        }

    def _evaluate_threshold(
        self,
        criterion: CriterionDefinition,
        trace_data: dict[str, Any],
    ) -> CriterionResult:
        raw_value = self._extractor.extract_value(trace_data, criterion.extract)
        scale = self._scales[criterion.scale_name]

        if raw_value is None:
            return CriterionResult(
                criterion_name=criterion.name,
                display_name=criterion.display_name,
                category=criterion.category,
                level=criterion.default_level,
                level_score=0.0,
                weight=criterion.weight,
                raw_value=None,
                details={"reason": "value_not_extracted"},
            )

        numeric_val = float(raw_value)
        level_name = criterion.default_level

        for tl in criterion.threshold_levels:
            if numeric_val <= tl.max:
                level_name = tl.level
                break

        level_def = self._find_level(scale, level_name)

        return CriterionResult(
            criterion_name=criterion.name,
            display_name=criterion.display_name,
            category=criterion.category,
            level=level_def.name,
            level_score=level_def.score,
            weight=criterion.weight,
            raw_value=numeric_val,
            auto_fail=level_def.auto_fail,
            details={
                "value": numeric_val,
                "unit": criterion.extract.unit,
                "thresholds": [
                    {"level": tl.level, "max": tl.max}
                    for tl in criterion.threshold_levels
                ],
            },
        )

    def _find_criterion(self, name: str) -> CriterionDefinition:
        for c in self._rubric.criteria:
            if c.name == name:
                return c
        raise KeyError(f"Criterion '{name}' not found in rubric")

    @staticmethod
    def _find_level(scale: ScoringScale, level_name: str) -> LevelDefinition:
        for lvl in scale.levels:
            if lvl.name == level_name:
                return lvl
        return scale.levels[-1]


# Grade boundaries for composite scoring
_GRADE_BOUNDARIES = [
    {"grade": "A", "min": 0.90},
    {"grade": "B", "min": 0.70},
    {"grade": "C", "min": 0.50},
    {"grade": "D", "min": 0.20},
    {"grade": "F", "min": 0.00},
]
