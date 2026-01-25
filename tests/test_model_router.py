"""Tests for Cost-Aware Model Router."""

import json
import tempfile
from pathlib import Path

import pytest

from lloyd.utils.model_router import (
    CostAwareRouter,
    DEFAULT_MODELS,
    ModelConfig,
    ModelTier,
    TASK_MODEL_MAP,
    UsageRecord,
)


@pytest.fixture
def temp_lloyd_dir():
    """Create a temporary lloyd directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def router(temp_lloyd_dir):
    """Create a CostAwareRouter with temporary storage."""
    return CostAwareRouter(lloyd_dir=temp_lloyd_dir, budget=100.0)


class TestModelTier:
    """Tests for ModelTier enum."""

    def test_values(self):
        """Enum has expected values."""
        assert ModelTier.FAST.value == "fast"
        assert ModelTier.BALANCED.value == "balanced"
        assert ModelTier.POWERFUL.value == "powerful"


class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_creation(self):
        """Creates config correctly."""
        config = ModelConfig(
            name="test-model",
            tier=ModelTier.BALANCED,
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.002,
            max_context=100000,
        )

        assert config.name == "test-model"
        assert config.tier == ModelTier.BALANCED
        assert config.cost_per_1k_input == 0.001


class TestUsageRecord:
    """Tests for UsageRecord dataclass."""

    def test_creation(self):
        """Creates record correctly."""
        record = UsageRecord(
            model="test",
            tier=ModelTier.FAST,
            input_tokens=1000,
            output_tokens=500,
            cost=0.01,
            task_type="coding",
        )

        assert record.model == "test"
        assert record.input_tokens == 1000

    def test_to_dict(self):
        """Converts to dictionary correctly."""
        record = UsageRecord(
            model="test",
            tier=ModelTier.FAST,
            input_tokens=1000,
            output_tokens=500,
            cost=0.01,
            task_type="coding",
            timestamp=1000.0,
        )

        data = record.to_dict()

        assert data["model"] == "test"
        assert data["tier"] == "fast"
        assert data["input_tokens"] == 1000


class TestDefaultMappings:
    """Tests for default model mappings."""

    def test_default_models_exist(self):
        """Default models are defined for all tiers."""
        assert ModelTier.FAST in DEFAULT_MODELS
        assert ModelTier.BALANCED in DEFAULT_MODELS
        assert ModelTier.POWERFUL in DEFAULT_MODELS

    def test_task_map_has_expected_entries(self):
        """Task map has expected entries."""
        assert "classification" in TASK_MODEL_MAP
        assert "coding" in TASK_MODEL_MAP
        assert "architecture" in TASK_MODEL_MAP


class TestGetModel:
    """Tests for get_model method."""

    def test_returns_config_for_task_type(self, router):
        """Returns appropriate config for task type."""
        config = router.get_model("classification")
        assert config.tier == ModelTier.FAST

        config = router.get_model("coding")
        assert config.tier == ModelTier.BALANCED

        config = router.get_model("architecture")
        assert config.tier == ModelTier.POWERFUL

    def test_unknown_task_type_defaults_balanced(self, router):
        """Unknown task type defaults to BALANCED."""
        config = router.get_model("unknown_task")
        assert config.tier == ModelTier.BALANCED

    def test_force_tier_overrides(self, router):
        """force_tier overrides task type mapping."""
        config = router.get_model("classification", force_tier=ModelTier.POWERFUL)
        assert config.tier == ModelTier.POWERFUL

    def test_downgrades_near_budget(self, temp_lloyd_dir):
        """Downgrades to FAST when near budget."""
        router = CostAwareRouter(lloyd_dir=temp_lloyd_dir, budget=0.01)

        # Use up most of budget (90%+)
        router.record_usage(
            model="test",
            tier=ModelTier.BALANCED,
            input_tokens=3000,  # ~$0.009 input
            output_tokens=100,
            task_type="coding",
        )

        # Should now downgrade to FAST
        config = router.get_model("architecture")
        assert config.tier == ModelTier.FAST


class TestGetModelForComplexity:
    """Tests for get_model_for_complexity method."""

    def test_trivial_uses_fast(self, router):
        """TRIVIAL complexity uses FAST tier."""
        config = router.get_model_for_complexity("TRIVIAL")
        assert config.tier == ModelTier.FAST

    def test_simple_uses_fast(self, router):
        """SIMPLE complexity uses FAST tier."""
        config = router.get_model_for_complexity("SIMPLE")
        assert config.tier == ModelTier.FAST

    def test_moderate_uses_balanced(self, router):
        """MODERATE complexity uses BALANCED tier."""
        config = router.get_model_for_complexity("MODERATE")
        assert config.tier == ModelTier.BALANCED

    def test_complex_uses_powerful(self, router):
        """COMPLEX complexity uses POWERFUL tier."""
        config = router.get_model_for_complexity("COMPLEX")
        assert config.tier == ModelTier.POWERFUL

    def test_case_insensitive(self, router):
        """Complexity is case insensitive."""
        config = router.get_model_for_complexity("complex")
        assert config.tier == ModelTier.POWERFUL


class TestRecordUsage:
    """Tests for record_usage method."""

    def test_records_and_returns_cost(self, router):
        """Records usage and returns computed cost."""
        cost = router.record_usage(
            model="test",
            tier=ModelTier.FAST,
            input_tokens=1000,
            output_tokens=500,
            task_type="classification",
        )

        assert cost > 0
        assert router._total_cost == cost

    def test_accumulates_cost(self, router):
        """Accumulates cost across calls."""
        cost1 = router.record_usage(
            model="test",
            tier=ModelTier.FAST,
            input_tokens=1000,
            output_tokens=500,
            task_type="classification",
        )
        cost2 = router.record_usage(
            model="test",
            tier=ModelTier.BALANCED,
            input_tokens=1000,
            output_tokens=500,
            task_type="coding",
        )

        assert router._total_cost == cost1 + cost2

    def test_persists_usage(self, temp_lloyd_dir):
        """Usage persists to disk."""
        router1 = CostAwareRouter(lloyd_dir=temp_lloyd_dir, budget=100.0)
        router1.record_usage(
            model="test",
            tier=ModelTier.FAST,
            input_tokens=1000,
            output_tokens=500,
            task_type="classification",
        )

        router2 = CostAwareRouter(lloyd_dir=temp_lloyd_dir, budget=100.0)

        assert router2._total_cost == router1._total_cost


class TestBudgetReport:
    """Tests for get_budget_report method."""

    def test_includes_total_cost(self, router):
        """Report includes total cost."""
        router.record_usage(
            model="test",
            tier=ModelTier.FAST,
            input_tokens=1000,
            output_tokens=500,
            task_type="classification",
        )

        report = router.get_budget_report()

        assert "total_cost" in report
        assert report["total_cost"] > 0

    def test_includes_budget_info(self, router):
        """Report includes budget information."""
        report = router.get_budget_report()

        assert report["budget"] == 100.0
        assert "budget_remaining" in report
        assert "budget_used_percent" in report

    def test_includes_usage_by_tier(self, router):
        """Report includes usage by tier."""
        router.record_usage(
            model="test",
            tier=ModelTier.FAST,
            input_tokens=1000,
            output_tokens=500,
            task_type="classification",
        )

        report = router.get_budget_report()

        assert "usage_by_tier" in report
        assert "fast" in report["usage_by_tier"]

    def test_includes_usage_by_task(self, router):
        """Report includes usage by task type."""
        router.record_usage(
            model="test",
            tier=ModelTier.FAST,
            input_tokens=1000,
            output_tokens=500,
            task_type="classification",
        )

        report = router.get_budget_report()

        assert "usage_by_task" in report
        assert "classification" in report["usage_by_task"]

    def test_recommendations_near_budget(self, temp_lloyd_dir):
        """Generates recommendations when near budget."""
        router = CostAwareRouter(lloyd_dir=temp_lloyd_dir, budget=0.001)

        # Use most of tiny budget
        router.record_usage(
            model="test",
            tier=ModelTier.FAST,
            input_tokens=1000,
            output_tokens=500,
            task_type="classification",
        )

        report = router.get_budget_report()

        assert len(report["recommendations"]) > 0


class TestBudgetChecks:
    """Tests for budget checking methods."""

    def test_is_over_budget_false_initially(self, router):
        """is_over_budget returns False initially."""
        assert router.is_over_budget() is False

    def test_is_over_budget_when_exceeded(self, temp_lloyd_dir):
        """is_over_budget returns True when budget exceeded."""
        router = CostAwareRouter(lloyd_dir=temp_lloyd_dir, budget=0.0001)

        router.record_usage(
            model="test",
            tier=ModelTier.BALANCED,
            input_tokens=10000,
            output_tokens=5000,
            task_type="coding",
        )

        assert router.is_over_budget() is True

    def test_is_near_budget_limit(self, temp_lloyd_dir):
        """is_near_budget_limit detects 90%+ usage."""
        router = CostAwareRouter(lloyd_dir=temp_lloyd_dir, budget=0.001)

        # Use up 95% of budget
        router._total_cost = 0.00095

        assert router.is_near_budget_limit() is True

    def test_no_budget_never_over(self, temp_lloyd_dir):
        """Without budget, never over/near limit."""
        router = CostAwareRouter(lloyd_dir=temp_lloyd_dir, budget=None)

        router.record_usage(
            model="test",
            tier=ModelTier.POWERFUL,
            input_tokens=1000000,
            output_tokens=500000,
            task_type="architecture",
        )

        assert router.is_over_budget() is False
        assert router.is_near_budget_limit() is False


class TestResetUsage:
    """Tests for reset_usage method."""

    def test_clears_records(self, router):
        """Clears all usage records."""
        router.record_usage(
            model="test",
            tier=ModelTier.FAST,
            input_tokens=1000,
            output_tokens=500,
            task_type="classification",
        )

        router.reset_usage()

        assert len(router._usage_records) == 0
        assert router._total_cost == 0.0


class TestRecommendedTier:
    """Tests for get_recommended_tier method."""

    def test_uses_task_map(self, router):
        """Uses task map by default."""
        tier = router.get_recommended_tier("classification")
        assert tier == ModelTier.FAST

        tier = router.get_recommended_tier("coding")
        assert tier == ModelTier.BALANCED

    def test_escalates_on_retry(self, router):
        """Escalates tier after retries."""
        tier = router.get_recommended_tier("classification", retry_count=2)
        assert tier == ModelTier.BALANCED

        tier = router.get_recommended_tier("coding", retry_count=2)
        assert tier == ModelTier.POWERFUL

    def test_considers_complexity(self, router):
        """Considers complexity in recommendation."""
        tier = router.get_recommended_tier("coding", complexity="COMPLEX")
        assert tier == ModelTier.POWERFUL

        tier = router.get_recommended_tier("coding", complexity="TRIVIAL")
        assert tier == ModelTier.FAST

    def test_budget_overrides(self, temp_lloyd_dir):
        """Budget constraints override other factors."""
        router = CostAwareRouter(lloyd_dir=temp_lloyd_dir, budget=0.001)
        router._total_cost = 0.00095  # Near limit

        tier = router.get_recommended_tier("architecture", complexity="COMPLEX")
        assert tier == ModelTier.FAST


class TestPersistence:
    """Tests for usage file persistence."""

    def test_usage_file_path(self, temp_lloyd_dir):
        """Uses correct file path."""
        router = CostAwareRouter(lloyd_dir=temp_lloyd_dir)
        expected = temp_lloyd_dir / "model_usage.json"

        assert router._get_usage_path() == expected

    def test_creates_directory(self, temp_lloyd_dir):
        """Creates lloyd directory if needed."""
        new_dir = temp_lloyd_dir / "new_lloyd"
        router = CostAwareRouter(lloyd_dir=new_dir)

        router.record_usage(
            model="test",
            tier=ModelTier.FAST,
            input_tokens=1000,
            output_tokens=500,
            task_type="classification",
        )

        assert new_dir.exists()

    def test_handles_corrupt_file(self, temp_lloyd_dir):
        """Handles corrupt JSON gracefully."""
        usage_file = temp_lloyd_dir / "model_usage.json"
        usage_file.write_text("not valid json{{{")

        router = CostAwareRouter(lloyd_dir=temp_lloyd_dir)

        assert len(router._usage_records) == 0
        assert router._total_cost == 0.0

    def test_usage_file_format(self, router):
        """Usage file has correct format."""
        router.record_usage(
            model="test",
            tier=ModelTier.FAST,
            input_tokens=1000,
            output_tokens=500,
            task_type="classification",
        )

        path = router._get_usage_path()
        with open(path) as f:
            data = json.load(f)

        assert "version" in data
        assert "updated_at" in data
        assert "total_cost" in data
        assert "records" in data
