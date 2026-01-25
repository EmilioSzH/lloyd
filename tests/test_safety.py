"""Tests for LLM-based safety detection."""

import pytest

from lloyd.orchestrator.safety import (
    SafetyGuard,
    SelfModDetectionResult,
    SelfModRisk,
    detect_self_modification_intent,
    is_self_modification,
)


class TestDetectSelfModificationIntent:
    """Tests for detect_self_modification_intent function."""

    def test_safe_idea_returns_low_risk(self):
        """Normal ideas return low risk."""
        result = detect_self_modification_intent("Add a login page to the app")

        assert result.risk_level == SelfModRisk.SAFE
        assert result.risk_score <= 2
        assert not result.is_self_modification

    def test_lloyd_keyword_triggers_detection(self):
        """Mentioning 'lloyd' triggers detection."""
        result = detect_self_modification_intent("Improve Lloyd's error handling")

        assert result.risk_score >= 4
        assert result.is_self_modification

    def test_yourself_keyword_triggers_detection(self):
        """Mentioning 'yourself' triggers detection."""
        result = detect_self_modification_intent("Update yourself to handle edge cases")

        assert result.is_self_modification

    def test_protected_files_increase_risk(self):
        """Protected files increase risk score."""
        result = detect_self_modification_intent(
            "Fix the bug",
            files=["src/lloyd/orchestrator/flow.py"],
        )

        assert len(result.affected_files) > 0
        assert result.risk_score >= 3

    def test_agent_definitions_detected(self):
        """Agent definition files are detected."""
        result = detect_self_modification_intent(
            "Change the agent behavior",
            files=["crews/planning/agents.yaml"],
        )

        assert "agent" in result.category or len(result.affected_files) > 0

    def test_safety_code_protected(self):
        """Safety code modifications are detected."""
        result = detect_self_modification_intent(
            "Modify the safety checks",
            files=["selfmod/classifier.py"],
        )

        assert len(result.affected_files) > 0
        assert result.risk_score >= 3

    def test_with_llm_function(self):
        """Can use LLM function for classification."""

        def mock_llm(prompt: str) -> str:
            return '{"risk": 7, "category": "orchestration", "reason": "Test"}'

        result = detect_self_modification_intent(
            "Some task", llm_func=mock_llm
        )

        assert result.risk_score == 7
        assert result.category == "orchestration"

    def test_llm_json_parsing(self):
        """Can parse LLM JSON response with markdown."""

        def mock_llm(prompt: str) -> str:
            return '```json\n{"risk": 3, "category": "none", "reason": "Safe task"}\n```'

        result = detect_self_modification_intent(
            "Add a button", llm_func=mock_llm
        )

        assert result.risk_score == 3

    def test_llm_failure_fallback(self):
        """Falls back to rules if LLM fails."""

        def failing_llm(prompt: str) -> str:
            raise Exception("LLM failed")

        result = detect_self_modification_intent(
            "Add a login page", llm_func=failing_llm
        )

        # Should still return a result
        assert isinstance(result, SelfModDetectionResult)


class TestIsSelfModification:
    """Tests for is_self_modification function."""

    def test_returns_true_for_self_mod(self):
        """Returns True for self-modification."""
        assert is_self_modification("Upgrade Lloyd to handle more cases") is True

    def test_returns_false_for_normal(self):
        """Returns False for normal tasks."""
        assert is_self_modification("Add user authentication") is False


class TestSafetyGuard:
    """Tests for SafetyGuard class."""

    def test_check_idea_returns_result(self):
        """check_idea returns detection result."""
        guard = SafetyGuard()
        result = guard.check_idea("Add a new feature")

        assert isinstance(result, SelfModDetectionResult)

    def test_should_block_high_risk(self):
        """should_block returns True for high risk."""
        guard = SafetyGuard()

        # Mock a blocked scenario
        def mock_llm(prompt: str) -> str:
            return '{"risk": 10, "category": "safety_code", "reason": "Blocked"}'

        guard.llm_func = mock_llm
        assert guard.should_block("Modify safety checks") is True

    def test_should_not_block_safe(self):
        """should_block returns False for safe ideas."""
        guard = SafetyGuard()
        assert guard.should_block("Add a login page") is False

    def test_should_require_approval_risky(self):
        """should_require_approval returns True for risky."""
        guard = SafetyGuard()

        def mock_llm(prompt: str) -> str:
            return '{"risk": 7, "category": "orchestration", "reason": "Risky"}'

        guard.llm_func = mock_llm
        assert guard.should_require_approval("Modify orchestration") is True

    def test_validate_files_safe(self):
        """validate_files returns safe for normal files."""
        guard = SafetyGuard()
        is_safe, protected = guard.validate_files([
            "src/app/views.py",
            "src/app/models.py",
        ])

        assert is_safe is True
        assert len(protected) == 0

    def test_validate_files_protected(self):
        """validate_files detects protected files."""
        guard = SafetyGuard()
        is_safe, protected = guard.validate_files([
            "src/lloyd/orchestrator/flow.py",
            "src/lloyd/selfmod/handler.py",
        ])

        assert is_safe is False
        assert len(protected) >= 2


class TestSelfModRisk:
    """Tests for SelfModRisk enum."""

    def test_risk_levels_exist(self):
        """All expected risk levels exist."""
        assert SelfModRisk.SAFE.value == "safe"
        assert SelfModRisk.MODERATE.value == "moderate"
        assert SelfModRisk.RISKY.value == "risky"
        assert SelfModRisk.BLOCKED.value == "blocked"
