"""Tests for FailureEscalationLadder."""

import pytest

from lloyd.orchestrator.recovery import (
    FailureEscalationLadder,
    HumanQuestion,
    RecoveryAction,
)


@pytest.fixture
def ladder():
    """Create a FailureEscalationLadder for testing."""
    return FailureEscalationLadder()


class TestGetRecoveryAction:
    """Tests for get_recovery_action method."""

    def test_attempt_1_simple_retry(self, ladder):
        """Attempt 1 returns simple retry."""
        action, desc = ladder.get_recovery_action(1)
        assert action == RecoveryAction.SIMPLE_RETRY

    def test_attempt_2_alternate_approach(self, ladder):
        """Attempt 2 returns alternate approach."""
        action, desc = ladder.get_recovery_action(2)
        assert action == RecoveryAction.ALTERNATE_APPROACH

    def test_attempt_3_inject_architect(self, ladder):
        """Attempt 3 returns inject architect."""
        action, desc = ladder.get_recovery_action(3)
        assert action == RecoveryAction.INJECT_ARCHITECT

    def test_attempt_4_ask_human(self, ladder):
        """Attempt 4 returns ask human."""
        action, desc = ladder.get_recovery_action(4)
        assert action == RecoveryAction.ASK_HUMAN

    def test_attempt_5_reduce_scope(self, ladder):
        """Attempt 5 returns reduce scope."""
        action, desc = ladder.get_recovery_action(5)
        assert action == RecoveryAction.REDUCE_SCOPE

    def test_attempt_6_mark_blocked(self, ladder):
        """Attempt 6 returns mark blocked."""
        action, desc = ladder.get_recovery_action(6)
        assert action == RecoveryAction.MARK_BLOCKED

    def test_attempt_beyond_6_clamps(self, ladder):
        """Attempts beyond 6 clamp to mark blocked."""
        action, desc = ladder.get_recovery_action(10)
        assert action == RecoveryAction.MARK_BLOCKED


class TestExecuteRecovery:
    """Tests for execute_recovery method."""

    def test_simple_retry_continues(self, ladder):
        """Simple retry continues execution."""
        story = {"id": "s1", "title": "Test story"}
        result = ladder.execute_recovery(
            RecoveryAction.SIMPLE_RETRY, story, {}
        )

        assert result["continue_execution"] is True
        assert result["action_taken"] == "simple_retry"

    def test_alternate_approach_provides_prompt(self, ladder):
        """Alternate approach provides alternate prompt."""
        story = {"id": "s1", "title": "Test story", "description": "A test"}
        context = {"error_history": ["Error 1", "Error 2"]}

        result = ladder.execute_recovery(
            RecoveryAction.ALTERNATE_APPROACH, story, context
        )

        assert result["continue_execution"] is True
        assert "alternate_approach_prompt" in result["modifications"]
        assert result["modifications"]["use_alternate_strategy"] is True

    def test_inject_architect_provides_prompt(self, ladder):
        """Inject architect provides analysis prompt."""
        story = {"id": "s1", "title": "Test story"}
        result = ladder.execute_recovery(
            RecoveryAction.INJECT_ARCHITECT, story, {}
        )

        assert result["continue_execution"] is True
        assert result["modifications"]["inject_architect"] is True
        assert "architect_prompt" in result["modifications"]

    def test_ask_human_without_handler_stops(self, ladder):
        """Ask human without handler stops execution."""
        story = {"id": "s1", "title": "Test story"}
        result = ladder.execute_recovery(
            RecoveryAction.ASK_HUMAN, story, {}
        )

        assert result["continue_execution"] is False
        assert result["requires_human_input"] is True
        assert "human_question" in result

    def test_ask_human_with_handler_continues(self, ladder):
        """Ask human with handler continues execution."""
        story = {"id": "s1", "title": "Test story"}

        def mock_handler(question):
            return "Use approach X"

        result = ladder.execute_recovery(
            RecoveryAction.ASK_HUMAN, story, {}, human_input_handler=mock_handler
        )

        assert result["continue_execution"] is True
        assert result["modifications"]["human_guidance"] == "Use approach X"

    def test_reduce_scope_modifies_criteria(self, ladder):
        """Reduce scope reduces acceptance criteria."""
        story = {
            "id": "s1",
            "title": "Test story",
            "acceptanceCriteria": ["A", "B", "C", "D", "E"],
        }

        result = ladder.execute_recovery(
            RecoveryAction.REDUCE_SCOPE, story, {}
        )

        assert result["continue_execution"] is True
        assert result["modifications"]["reduced_scope"] is True
        assert result["modifications"]["original_criteria_count"] == 5
        assert result["modifications"]["reduced_criteria_count"] == 4

    def test_mark_blocked_stops_execution(self, ladder):
        """Mark blocked stops execution."""
        story = {"id": "s1", "title": "Test story"}
        result = ladder.execute_recovery(
            RecoveryAction.MARK_BLOCKED, story, {}
        )

        assert result["continue_execution"] is False
        assert result["modifications"]["status"] == "blocked"


class TestErrorHistory:
    """Tests for error history tracking."""

    def test_record_failure(self, ladder):
        """Can record failures."""
        ladder.record_failure("s1", "Error 1")
        ladder.record_failure("s1", "Error 2")

        history = ladder.get_error_history("s1")
        assert len(history) == 2
        assert "Error 1" in history
        assert "Error 2" in history

    def test_separate_histories_per_story(self, ladder):
        """Each story has separate history."""
        ladder.record_failure("s1", "Error 1")
        ladder.record_failure("s2", "Error A")

        assert len(ladder.get_error_history("s1")) == 1
        assert len(ladder.get_error_history("s2")) == 1

    def test_reset_story_clears_history(self, ladder):
        """Reset clears error history."""
        ladder.record_failure("s1", "Error 1")
        ladder.reset_story("s1")

        assert ladder.get_error_history("s1") == []

    def test_get_escalation_summary(self, ladder):
        """Get escalation summary returns correct info."""
        ladder.record_failure("s1", "Error 1")
        ladder.record_failure("s1", "Error 2")

        summary = ladder.get_escalation_summary("s1")

        assert summary["story_id"] == "s1"
        assert summary["error_count"] == 2
        assert summary["current_level"] == 3  # After 2 errors, level 3


class TestHumanQuestion:
    """Tests for human question generation."""

    def test_question_includes_error_history(self, ladder):
        """Human question includes error history."""
        story = {"id": "s1", "title": "Auth task"}
        ladder.record_failure("s1", "Permission denied")
        ladder.record_failure("s1", "Token invalid")

        result = ladder.execute_recovery(RecoveryAction.ASK_HUMAN, story, {})
        question = result["human_question"]

        assert isinstance(question, HumanQuestion)
        assert len(question.error_history) > 0

    def test_question_has_options(self, ladder):
        """Human question provides options."""
        story = {"id": "s1", "title": "Test task"}

        result = ladder.execute_recovery(RecoveryAction.ASK_HUMAN, story, {})
        question = result["human_question"]

        assert len(question.options) > 0
        assert len(question.options) <= 4

    def test_permission_error_adds_permission_option(self, ladder):
        """Permission errors add permission-related option."""
        story = {"id": "s1", "title": "File task"}
        ladder.record_failure("s1", "Permission denied to access file")

        result = ladder.execute_recovery(RecoveryAction.ASK_HUMAN, story, {})
        question = result["human_question"]

        assert any("permission" in opt.lower() for opt in question.options)
