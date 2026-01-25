"""Cost-Aware Model Router for Lloyd.

Routes tasks to appropriate model tiers based on task type
and budget constraints.
"""

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
import json


class ModelTier(str, Enum):
    """Model tiers by capability and cost."""

    FAST = "fast"  # Cheap, fast, good for simple tasks
    BALANCED = "balanced"  # Mid-range, good for most coding
    POWERFUL = "powerful"  # Most capable, expensive, for complex tasks


@dataclass
class ModelConfig:
    """Configuration for a model.

    Attributes:
        name: Model identifier (e.g., "claude-3-haiku").
        tier: Model tier.
        cost_per_1k_input: Cost per 1000 input tokens.
        cost_per_1k_output: Cost per 1000 output tokens.
        max_context: Maximum context window.
    """

    name: str
    tier: ModelTier
    cost_per_1k_input: float
    cost_per_1k_output: float
    max_context: int = 100000


@dataclass
class UsageRecord:
    """Record of model usage.

    Attributes:
        model: Model name used.
        tier: Model tier.
        input_tokens: Number of input tokens.
        output_tokens: Number of output tokens.
        cost: Computed cost.
        task_type: Type of task performed.
        timestamp: When the usage occurred.
    """

    model: str
    tier: ModelTier
    input_tokens: int
    output_tokens: int
    cost: float
    task_type: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "model": self.model,
            "tier": self.tier.value,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost": self.cost,
            "task_type": self.task_type,
            "timestamp": self.timestamp,
        }


# Default model configurations (approximate pricing)
DEFAULT_MODELS: dict[ModelTier, ModelConfig] = {
    ModelTier.FAST: ModelConfig(
        name="claude-3-haiku-20240307",
        tier=ModelTier.FAST,
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125,
        max_context=200000,
    ),
    ModelTier.BALANCED: ModelConfig(
        name="claude-3-5-sonnet-20241022",
        tier=ModelTier.BALANCED,
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        max_context=200000,
    ),
    ModelTier.POWERFUL: ModelConfig(
        name="claude-3-opus-20240229",
        tier=ModelTier.POWERFUL,
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.075,
        max_context=200000,
    ),
}

# Task type to model tier mapping
TASK_MODEL_MAP: dict[str, ModelTier] = {
    # Fast tier tasks
    "classification": ModelTier.FAST,
    "summarization": ModelTier.FAST,
    "extraction": ModelTier.FAST,
    "formatting": ModelTier.FAST,
    "simple_qa": ModelTier.FAST,
    # Balanced tier tasks
    "coding": ModelTier.BALANCED,
    "code_review": ModelTier.BALANCED,
    "debugging": ModelTier.BALANCED,
    "testing": ModelTier.BALANCED,
    "refactoring": ModelTier.BALANCED,
    "documentation": ModelTier.BALANCED,
    # Powerful tier tasks
    "architecture": ModelTier.POWERFUL,
    "design": ModelTier.POWERFUL,
    "complex_reasoning": ModelTier.POWERFUL,
    "multi_step_planning": ModelTier.POWERFUL,
    "novel_solutions": ModelTier.POWERFUL,
}


class CostAwareRouter:
    """Routes tasks to models based on type and budget.

    Features:
    - Task type-based model selection
    - Budget tracking and enforcement
    - Automatic downgrade near budget limit
    - Usage reporting
    """

    BUDGET_WARNING_THRESHOLD = 0.9  # 90% of budget
    USAGE_FILE = "model_usage.json"

    def __init__(
        self,
        lloyd_dir: Path | None = None,
        budget: float | None = None,
        models: dict[ModelTier, ModelConfig] | None = None,
        task_map: dict[str, ModelTier] | None = None,
    ) -> None:
        """Initialize the cost-aware router.

        Args:
            lloyd_dir: Lloyd data directory. Defaults to .lloyd
            budget: Maximum budget in dollars. None for unlimited.
            models: Model configurations by tier.
            task_map: Task type to tier mapping.
        """
        self.lloyd_dir = lloyd_dir or Path(".lloyd")
        self.budget = budget
        self.models = models or DEFAULT_MODELS.copy()
        self.task_map = task_map or TASK_MODEL_MAP.copy()

        # Track usage
        self._usage_records: list[UsageRecord] = []
        self._total_cost: float = 0.0
        self._load_usage()

    def _get_usage_path(self) -> Path:
        """Get path to usage file.

        Returns:
            Path to model_usage.json.
        """
        return self.lloyd_dir / self.USAGE_FILE

    def _load_usage(self) -> None:
        """Load usage records from disk."""
        path = self._get_usage_path()
        if not path.exists():
            self._usage_records = []
            self._total_cost = 0.0
            return

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            self._usage_records = []
            for record in data.get("records", []):
                self._usage_records.append(UsageRecord(
                    model=record["model"],
                    tier=ModelTier(record["tier"]),
                    input_tokens=record["input_tokens"],
                    output_tokens=record["output_tokens"],
                    cost=record["cost"],
                    task_type=record["task_type"],
                    timestamp=record.get("timestamp", time.time()),
                ))
            self._total_cost = data.get("total_cost", 0.0)
        except (json.JSONDecodeError, KeyError):
            self._usage_records = []
            self._total_cost = 0.0

    def _save_usage(self) -> None:
        """Save usage records to disk."""
        self.lloyd_dir.mkdir(parents=True, exist_ok=True)
        path = self._get_usage_path()

        data = {
            "version": 1,
            "updated_at": datetime.now(UTC).isoformat(),
            "total_cost": self._total_cost,
            "records": [r.to_dict() for r in self._usage_records[-1000:]],  # Keep last 1000
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_model(
        self,
        task_type: str,
        force_tier: ModelTier | None = None,
    ) -> ModelConfig:
        """Get the appropriate model for a task type.

        Args:
            task_type: Type of task (e.g., "coding", "classification").
            force_tier: Override tier selection.

        Returns:
            ModelConfig for the selected model.
        """
        # Determine desired tier
        if force_tier:
            desired_tier = force_tier
        else:
            desired_tier = self.task_map.get(task_type, ModelTier.BALANCED)

        # Check budget constraints
        if self.budget is not None:
            budget_usage = self._total_cost / self.budget

            if budget_usage >= self.BUDGET_WARNING_THRESHOLD:
                # Near or over budget - downgrade to FAST
                return self.models[ModelTier.FAST]

        return self.models[desired_tier]

    def get_model_for_complexity(
        self,
        complexity: str,
        task_type: str | None = None,
    ) -> ModelConfig:
        """Get model based on task complexity.

        Args:
            complexity: Task complexity (TRIVIAL, SIMPLE, MODERATE, COMPLEX).
            task_type: Optional task type for additional context.

        Returns:
            ModelConfig for the selected model.
        """
        complexity_map = {
            "TRIVIAL": ModelTier.FAST,
            "SIMPLE": ModelTier.FAST,
            "MODERATE": ModelTier.BALANCED,
            "COMPLEX": ModelTier.POWERFUL,
        }

        tier = complexity_map.get(complexity.upper(), ModelTier.BALANCED)
        return self.get_model(task_type or "general", force_tier=tier)

    def record_usage(
        self,
        model: str,
        tier: ModelTier,
        input_tokens: int,
        output_tokens: int,
        task_type: str,
    ) -> float:
        """Record model usage and return cost.

        Args:
            model: Model name used.
            tier: Model tier.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.
            task_type: Type of task.

        Returns:
            Cost of this usage.
        """
        config = self.models.get(tier)
        if not config:
            # Fallback to balanced if tier not found
            config = self.models[ModelTier.BALANCED]

        cost = (
            (input_tokens / 1000) * config.cost_per_1k_input +
            (output_tokens / 1000) * config.cost_per_1k_output
        )

        record = UsageRecord(
            model=model,
            tier=tier,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            task_type=task_type,
        )

        self._usage_records.append(record)
        self._total_cost += cost
        self._save_usage()

        return cost

    def get_budget_report(self) -> dict[str, Any]:
        """Get a budget and usage report.

        Returns:
            Dict with budget info, usage stats, and recommendations.
        """
        report: dict[str, Any] = {
            "total_cost": self._total_cost,
            "budget": self.budget,
            "budget_remaining": None,
            "budget_used_percent": None,
            "usage_by_tier": {},
            "usage_by_task": {},
            "recommendations": [],
        }

        if self.budget:
            report["budget_remaining"] = max(0, self.budget - self._total_cost)
            report["budget_used_percent"] = (self._total_cost / self.budget) * 100

        # Aggregate by tier
        tier_usage: dict[str, dict[str, float | int]] = {}
        for record in self._usage_records:
            tier_name = record.tier.value
            if tier_name not in tier_usage:
                tier_usage[tier_name] = {"cost": 0.0, "calls": 0}
            tier_usage[tier_name]["cost"] += record.cost
            tier_usage[tier_name]["calls"] += 1
        report["usage_by_tier"] = tier_usage

        # Aggregate by task type
        task_usage: dict[str, dict[str, float | int]] = {}
        for record in self._usage_records:
            if record.task_type not in task_usage:
                task_usage[record.task_type] = {"cost": 0.0, "calls": 0}
            task_usage[record.task_type]["cost"] += record.cost
            task_usage[record.task_type]["calls"] += 1
        report["usage_by_task"] = task_usage

        # Generate recommendations
        if self.budget:
            used_percent = (self._total_cost / self.budget) * 100
            if used_percent >= 90:
                report["recommendations"].append(
                    "Budget nearly exhausted. Downgrading to FAST tier for all tasks."
                )
            elif used_percent >= 75:
                report["recommendations"].append(
                    "Budget at 75%+. Consider using FAST tier for simple tasks."
                )

        # Check if powerful tier is overused
        powerful_cost = tier_usage.get("powerful", {}).get("cost", 0)
        if self._total_cost > 0 and (powerful_cost / self._total_cost) > 0.5:
            report["recommendations"].append(
                "Over 50% of cost is from POWERFUL tier. "
                "Review if all tasks require maximum capability."
            )

        return report

    def is_over_budget(self) -> bool:
        """Check if budget is exceeded.

        Returns:
            True if over budget.
        """
        if self.budget is None:
            return False
        return self._total_cost >= self.budget

    def is_near_budget_limit(self) -> bool:
        """Check if near budget limit (90%+).

        Returns:
            True if near or over budget limit.
        """
        if self.budget is None:
            return False
        return (self._total_cost / self.budget) >= self.BUDGET_WARNING_THRESHOLD

    def reset_usage(self) -> None:
        """Reset all usage tracking."""
        self._usage_records.clear()
        self._total_cost = 0.0
        path = self._get_usage_path()
        if path.exists():
            path.unlink()

    def get_recommended_tier(
        self,
        task_type: str,
        complexity: str | None = None,
        retry_count: int = 0,
    ) -> ModelTier:
        """Get recommended tier considering multiple factors.

        Args:
            task_type: Type of task.
            complexity: Optional complexity level.
            retry_count: Number of retries so far.

        Returns:
            Recommended ModelTier.
        """
        # Base tier from task type
        base_tier = self.task_map.get(task_type, ModelTier.BALANCED)

        # Escalate if retrying
        if retry_count >= 2:
            if base_tier == ModelTier.FAST:
                base_tier = ModelTier.BALANCED
            elif base_tier == ModelTier.BALANCED:
                base_tier = ModelTier.POWERFUL

        # Consider complexity
        if complexity:
            complexity_upper = complexity.upper()
            if complexity_upper == "COMPLEX" and base_tier != ModelTier.POWERFUL:
                base_tier = ModelTier.POWERFUL
            elif complexity_upper in ("TRIVIAL", "SIMPLE") and retry_count == 0:
                if base_tier == ModelTier.BALANCED:
                    base_tier = ModelTier.FAST

        # Budget constraints override
        if self.is_near_budget_limit():
            return ModelTier.FAST

        return base_tier
