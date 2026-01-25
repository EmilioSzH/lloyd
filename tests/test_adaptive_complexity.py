"""Tests for AdaptiveComplexityManager."""

import pytest

from lloyd.orchestrator.complexity import (
    AdaptiveComplexityManager,
    ExecutionSignals,
    TaskComplexity,
)


@pytest.fixture
def manager():
    """Create an AdaptiveComplexityManager for testing."""
    return AdaptiveComplexityManager()


class TestStartTracking:
    """Tests for start_tracking method."""

    def test_creates_signals_for_story(self, manager):
        """Start tracking creates signals entry."""
        manager.start_tracking("s1", TaskComplexity.SIMPLE)

        signals = manager.get_signals("s1")
        assert signals is not None
        assert signals.retry_count == 0
        assert signals.execution_time == 0.0

    def test_sets_expected_values_based_on_complexity(self, manager):
        """Expected values are set based on complexity level."""
        manager.start_tracking("s1", TaskComplexity.TRIVIAL)
        signals = manager.get_signals("s1")

        assert signals.expected_time == 30.0
        assert signals.expected_tool_calls == 3


class TestRecordSignals:
    """Tests for signal recording methods."""

    def test_record_retry(self, manager):
        """Can record retries."""
        manager.start_tracking("s1", TaskComplexity.SIMPLE)
        manager.record_retry("s1")
        manager.record_retry("s1")

        signals = manager.get_signals("s1")
        assert signals.retry_count == 2

    def test_record_tool_call(self, manager):
        """Can record tool calls."""
        manager.start_tracking("s1", TaskComplexity.SIMPLE)
        manager.record_tool_call("s1")
        manager.record_tool_call("s1")
        manager.record_tool_call("s1")

        signals = manager.get_signals("s1")
        assert signals.tool_calls == 3

    def test_record_error(self, manager):
        """Can record errors."""
        manager.start_tracking("s1", TaskComplexity.SIMPLE)
        manager.record_error("s1")

        signals = manager.get_signals("s1")
        assert signals.error_count == 1

    def test_record_execution_time(self, manager):
        """Can record execution time."""
        manager.start_tracking("s1", TaskComplexity.SIMPLE)
        manager.record_execution_time("s1", 45.5)
        manager.record_execution_time("s1", 30.0)

        signals = manager.get_signals("s1")
        assert signals.execution_time == 75.5


class TestShouldEscalateComplexity:
    """Tests for should_escalate_complexity method."""

    def test_no_escalation_without_triggers(self, manager):
        """No escalation when no triggers are met."""
        signals = ExecutionSignals(
            retry_count=1,
            execution_time=60.0,
            tool_calls=8,
            expected_time=120.0,
            expected_tool_calls=10,
        )

        result = manager.should_escalate_complexity(TaskComplexity.SIMPLE, signals)

        assert result.should_escalate is False
        assert result.new_level is None

    def test_escalate_on_retry_count(self, manager):
        """Escalates when retry_count >= 2."""
        signals = ExecutionSignals(
            retry_count=2,
            execution_time=60.0,
            tool_calls=5,
            expected_time=120.0,
            expected_tool_calls=10,
        )

        result = manager.should_escalate_complexity(TaskComplexity.SIMPLE, signals)

        assert result.should_escalate is True
        assert result.new_level == TaskComplexity.MODERATE
        assert "retry_count" in result.reason

    def test_escalate_on_execution_time(self, manager):
        """Escalates when execution_time > 3x expected."""
        signals = ExecutionSignals(
            retry_count=0,
            execution_time=400.0,  # > 3 * 120 = 360
            tool_calls=5,
            expected_time=120.0,
            expected_tool_calls=10,
        )

        result = manager.should_escalate_complexity(TaskComplexity.SIMPLE, signals)

        assert result.should_escalate is True
        assert "execution_time" in result.reason

    def test_escalate_on_tool_calls(self, manager):
        """Escalates when tool_calls > 2x expected."""
        signals = ExecutionSignals(
            retry_count=0,
            execution_time=60.0,
            tool_calls=25,  # > 2 * 10 = 20
            expected_time=120.0,
            expected_tool_calls=10,
        )

        result = manager.should_escalate_complexity(TaskComplexity.SIMPLE, signals)

        assert result.should_escalate is True
        assert "tool_calls" in result.reason

    def test_escalation_path_trivial_to_simple(self, manager):
        """TRIVIAL escalates to SIMPLE."""
        signals = ExecutionSignals(retry_count=2, expected_time=30.0, expected_tool_calls=3)

        result = manager.should_escalate_complexity(TaskComplexity.TRIVIAL, signals)

        assert result.new_level == TaskComplexity.SIMPLE

    def test_escalation_path_simple_to_moderate(self, manager):
        """SIMPLE escalates to MODERATE."""
        signals = ExecutionSignals(retry_count=2, expected_time=120.0, expected_tool_calls=10)

        result = manager.should_escalate_complexity(TaskComplexity.SIMPLE, signals)

        assert result.new_level == TaskComplexity.MODERATE

    def test_escalation_path_moderate_to_complex(self, manager):
        """MODERATE escalates to COMPLEX."""
        signals = ExecutionSignals(retry_count=2, expected_time=300.0, expected_tool_calls=25)

        result = manager.should_escalate_complexity(TaskComplexity.MODERATE, signals)

        assert result.new_level == TaskComplexity.COMPLEX

    def test_no_escalation_at_max_level(self, manager):
        """Cannot escalate beyond COMPLEX."""
        signals = ExecutionSignals(retry_count=3, expected_time=600.0, expected_tool_calls=50)

        result = manager.should_escalate_complexity(TaskComplexity.COMPLEX, signals)

        assert result.should_escalate is False
        assert result.new_level is None
        assert "already at max" in result.reason.lower()

    def test_inject_planning_for_moderate_and_complex(self, manager):
        """inject_planning is True when escalating to MODERATE or COMPLEX."""
        signals = ExecutionSignals(retry_count=2, expected_time=120.0, expected_tool_calls=10)

        result = manager.should_escalate_complexity(TaskComplexity.SIMPLE, signals)

        assert result.inject_planning is True  # Escalating to MODERATE


class TestCheckAndEscalate:
    """Tests for check_and_escalate convenience method."""

    def test_returns_result_when_tracking(self, manager):
        """Returns result when story is being tracked."""
        manager.start_tracking("s1", TaskComplexity.SIMPLE)
        manager.record_retry("s1")
        manager.record_retry("s1")

        result = manager.check_and_escalate("s1", TaskComplexity.SIMPLE)

        assert result.should_escalate is True

    def test_returns_no_escalate_when_not_tracking(self, manager):
        """Returns no escalation when story is not tracked."""
        result = manager.check_and_escalate("unknown", TaskComplexity.SIMPLE)

        assert result.should_escalate is False
        assert "No signals tracked" in result.reason


class TestResetAndSummary:
    """Tests for reset_story and get_summary methods."""

    def test_reset_story_removes_tracking(self, manager):
        """Reset removes tracking for a story."""
        manager.start_tracking("s1", TaskComplexity.SIMPLE)
        manager.record_retry("s1")

        manager.reset_story("s1")

        assert manager.get_signals("s1") is None

    def test_get_summary_returns_ratios(self, manager):
        """Summary includes calculated ratios."""
        manager.start_tracking("s1", TaskComplexity.SIMPLE)
        manager.record_execution_time("s1", 240.0)  # 2x expected (120)
        manager.record_tool_call("s1")
        manager.record_tool_call("s1")

        summary = manager.get_summary("s1")

        assert summary is not None
        assert summary["time_ratio"] == 2.0
        assert summary["tool_calls_ratio"] == 0.2  # 2/10

    def test_get_summary_returns_none_for_unknown(self, manager):
        """Summary returns None for unknown story."""
        assert manager.get_summary("unknown") is None
