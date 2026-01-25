"""Tests for PolicyEngine."""

import tempfile
from pathlib import Path

import pytest

from lloyd.orchestrator.policy_engine import Policy, PolicyEffect, PolicyEngine, PolicyType


@pytest.fixture
def temp_lloyd_dir():
    """Create a temporary lloyd directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def policy_engine(temp_lloyd_dir):
    """Create a PolicyEngine with temporary storage."""
    return PolicyEngine(lloyd_dir=temp_lloyd_dir)


class TestPolicyEngine:
    """Tests for PolicyEngine class."""

    def test_default_policies_registered(self, policy_engine):
        """Default policies are registered on init."""
        policies = policy_engine.list_policies()
        assert len(policies) > 0

        # Check for expected default policies
        names = [p["name"] for p in policies]
        assert "jwt_env_validation" in names
        assert "auth_requires_config" in names
        assert "prefer_pytest" in names

    def test_evaluate_returns_policy_effect(self, policy_engine):
        """Evaluate returns a PolicyEffect object."""
        context = {"description": "Simple task", "complexity": "simple"}
        result = policy_engine.evaluate(context)

        assert isinstance(result, PolicyEffect)

    def test_jwt_policy_triggers_on_retry(self, policy_engine):
        """JWT policy triggers when retry_count >= 2."""
        context = {
            "description": "Implement JWT authentication",
            "retry_count": 2,
        }

        result = policy_engine.evaluate(context)

        assert "jwt_env_validation" in result.applied_policies
        assert any("env" in step.lower() for step in result.inject_steps)

    def test_jwt_policy_not_triggered_without_retry(self, policy_engine):
        """JWT policy doesn't trigger with low retry count."""
        context = {
            "description": "Implement JWT authentication",
            "retry_count": 1,
        }

        result = policy_engine.evaluate(context)

        assert "jwt_env_validation" not in result.applied_policies

    def test_pytest_tool_bias(self, policy_engine):
        """Pytest preference adds tool bias."""
        context = {
            "description": "Add unit tests",
            "user_preferences": {"test_framework": "pytest"},
        }

        result = policy_engine.evaluate(context)

        assert "prefer_pytest" in result.applied_policies
        assert result.tool_bias.get("pytest", 0) > 0

    def test_skip_reviewer_for_simple_tasks(self, policy_engine):
        """Reviewer is skipped for high-confidence simple tasks."""
        context = {
            "description": "Fix typo in README",
            "complexity": "simple",
            "coder_success_rate": 0.90,
        }

        result = policy_engine.evaluate(context)

        assert "skip_reviewer_simple" in result.applied_policies
        assert "reviewer" in result.skip_agents

    def test_no_skip_for_complex_tasks(self, policy_engine):
        """Reviewer is not skipped for complex tasks."""
        context = {
            "description": "Refactor authentication system",
            "complexity": "complex",
            "coder_success_rate": 0.90,
        }

        result = policy_engine.evaluate(context)

        assert "skip_reviewer_simple" not in result.applied_policies

    def test_add_custom_policy(self, policy_engine):
        """Can add custom policies."""
        custom_policy = Policy(
            name="custom_test",
            policy_type=PolicyType.ROUTING,
            condition=lambda ctx: "custom" in ctx.get("description", "").lower(),
            action=lambda ctx: {"warnings": ["Custom policy triggered"]},
            confidence=0.9,
        )

        policy_engine.add_policy(custom_policy)

        context = {"description": "A custom task"}
        result = policy_engine.evaluate(context)

        assert "custom_test" in result.applied_policies
        assert any("Custom" in w for w in result.warnings)

    def test_remove_policy(self, policy_engine):
        """Can remove policies by name."""
        # First verify it exists
        policies_before = policy_engine.list_policies()
        assert any(p["name"] == "jwt_env_validation" for p in policies_before)

        # Remove it
        removed = policy_engine.remove_policy("jwt_env_validation")
        assert removed is True

        # Verify it's gone
        policies_after = policy_engine.list_policies()
        assert not any(p["name"] == "jwt_env_validation" for p in policies_after)

    def test_remove_nonexistent_policy(self, policy_engine):
        """Removing nonexistent policy returns False."""
        removed = policy_engine.remove_policy("nonexistent")
        assert removed is False

    def test_multiple_policies_apply(self, policy_engine):
        """Multiple policies can apply to same context."""
        context = {
            "description": "Implement JWT authentication",
            "retry_count": 2,
            "categories": ["auth"],
            "user_preferences": {"test_framework": "pytest"},
        }

        result = policy_engine.evaluate(context)

        # Both JWT and pytest policies should apply
        assert "jwt_env_validation" in result.applied_policies
        assert "prefer_pytest" in result.applied_policies


class TestPolicyEffect:
    """Tests for PolicyEffect dataclass."""

    def test_default_values(self):
        """PolicyEffect has correct default values."""
        effect = PolicyEffect()

        assert effect.skip_agents == []
        assert effect.inject_steps == []
        assert effect.tool_bias == {}
        assert effect.warnings == []
        assert effect.context_additions == {}
        assert effect.applied_policies == []


class TestPolicy:
    """Tests for Policy dataclass."""

    def test_policy_creation(self):
        """Policy can be created with all fields."""
        policy = Policy(
            name="test_policy",
            policy_type=PolicyType.RETRY,
            condition=lambda ctx: True,
            action=lambda ctx: {"warnings": ["test"]},
            confidence=0.8,
            source="test",
        )

        assert policy.name == "test_policy"
        assert policy.policy_type == PolicyType.RETRY
        assert policy.confidence == 0.8
        assert policy.source == "test"
