"""Task complexity assessment for Lloyd."""

import re
from dataclasses import dataclass
from enum import Enum


class TaskComplexity(str, Enum):
    """Task complexity levels."""

    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


@dataclass
class ComplexityAssessment:
    """Result of complexity assessment."""

    complexity: TaskComplexity
    reasoning: str
    suggested_agents: list[str]


class ComplexityAssessor:
    """Assess task complexity to determine execution strategy."""

    # Patterns for trivial tasks (minimal planning needed)
    TRIVIAL_PATTERNS = [
        r"add\s+.{1,30}\s+comment",
        r"change\s+.{1,30}\s+to\s+",
        r"rename\s+.{1,30}\s+to\s+",
        r"delete\s+.{1,50}$",
        r"remove\s+.{1,50}$",
        r"fix\s+typo",
        r"update\s+version",
        r"add\s+import",
        r"remove\s+import",
        r"update\s+.{1,20}\s+to\s+",
        # Simple function/script creation tasks
        r"create\s+a\s+(simple\s+)?function\s+",
        r"write\s+a\s+(simple\s+)?function\s+",
        r"create\s+a\s+(simple\s+)?script\s+",
        r"write\s+a\s+(simple\s+)?script\s+",
        r"create\s+a\s+file\s+",
        r"write\s+a\s+file\s+",
        # Single-function utilities
        r"(function|script)\s+that\s+(adds|subtracts|multiplies|divides|squares|reverses|checks|counts|converts)",
        r"(function|script)\s+to\s+(add|subtract|multiply|divide|square|reverse|check|count|convert)",
        # Basic class creation
        r"create\s+a\s+(simple\s+)?class\s+",
        r"write\s+a\s+(simple\s+)?class\s+",
        # Test simple tasks explicitly
        r"hello\s*world",
        r"print\s+.{1,30}",
    ]

    # Patterns that indicate simple tasks (skip verbose planning)
    SIMPLE_TASK_PATTERNS = [
        r"^create\s+",
        r"^write\s+",
        r"^build\s+(a\s+)?(simple|basic)\s+",
        r"(single|one)\s+function",
        r"(single|one)\s+file",
        r"counter\s+(class|program|app)",
        r"calculator\s+(class|program|app)",
        r"(palindrome|fibonacci|factorial|prime)\s+(checker|function|calculator)",
    ]

    COMPLEX_SIGNALS = [
        "authentication",
        "authorization",
        "database",
        "api",
        "refactor",
        "migrate",
        "architecture",
        "system",
        "integrate",
        "multiple",
        "components",
        "security",
        "performance",
        "optimize",
    ]

    def assess(self, idea: str) -> ComplexityAssessment:
        """Assess the complexity of a task idea.

        Args:
            idea: The task description.

        Returns:
            ComplexityAssessment with routing information.
        """
        idea_lower = idea.lower().strip()

        # Check trivial patterns first (these skip planning entirely)
        for pattern in self.TRIVIAL_PATTERNS:
            if re.search(pattern, idea_lower):
                return ComplexityAssessment(
                    complexity=TaskComplexity.TRIVIAL,
                    reasoning=f"Trivial pattern matched: {pattern}",
                    suggested_agents=["executor"],
                )

        # Check for complex signals
        complex_count = sum(1 for s in self.COMPLEX_SIGNALS if s in idea_lower)
        if complex_count >= 2:
            return ComplexityAssessment(
                complexity=TaskComplexity.COMPLEX,
                reasoning=f"{complex_count} complexity signals detected",
                suggested_agents=["planner", "researcher", "architect", "executor", "qa"],
            )

        # Check simple task patterns (use lightweight planning)
        for pattern in self.SIMPLE_TASK_PATTERNS:
            if re.search(pattern, idea_lower):
                return ComplexityAssessment(
                    complexity=TaskComplexity.SIMPLE,
                    reasoning=f"Simple task pattern matched: {pattern}",
                    suggested_agents=["executor"],
                )

        # Simple: short and focused (< 20 words, no complex signals)
        word_count = len(idea.split())
        if word_count < 20:
            return ComplexityAssessment(
                complexity=TaskComplexity.SIMPLE,
                reasoning="Short request (under 20 words)",
                suggested_agents=["executor"],
            )

        # Default: moderate complexity
        return ComplexityAssessment(
            complexity=TaskComplexity.MODERATE,
            reasoning="Standard complexity",
            suggested_agents=["planner", "executor", "qa"],
        )

    def _has_specific_target(self, idea: str) -> bool:
        """Check if the idea mentions a specific file or target.

        Args:
            idea: The task description.

        Returns:
            True if a specific target is mentioned.
        """
        # File extension pattern
        if re.search(r"\.\w{2,4}\b", idea):
            return True
        # Path pattern
        if re.search(r"[\w/\\]+\.\w+", idea):
            return True
        # Named target pattern
        if re.search(r"(function|class|method|file|variable)\s+\w+", idea.lower()):
            return True
        return False


@dataclass
class ExecutionSignals:
    """Signals collected during execution for complexity reassessment.

    Attributes:
        retry_count: Number of execution retries.
        execution_time: Total execution time in seconds.
        tool_calls: Number of tool calls made.
        error_count: Number of errors encountered.
        expected_time: Expected execution time for this complexity level.
        expected_tool_calls: Expected tool calls for this complexity level.
    """

    retry_count: int = 0
    execution_time: float = 0.0
    tool_calls: int = 0
    error_count: int = 0
    expected_time: float = 60.0  # 1 minute default
    expected_tool_calls: int = 5  # Default expected


@dataclass
class EscalationResult:
    """Result of complexity escalation check.

    Attributes:
        should_escalate: Whether to escalate complexity.
        new_level: New complexity level if escalating.
        reason: Reason for escalation decision.
        inject_planning: Whether to inject planning for remaining stories.
    """

    should_escalate: bool
    new_level: TaskComplexity | None
    reason: str
    inject_planning: bool = False


class AdaptiveComplexityManager:
    """Manager for adaptive complexity reassessment during execution.

    Tracks execution signals and escalates complexity when tasks appear
    harder than initially assessed.

    Escalation triggers:
    - retry_count >= 2
    - execution_time > 3x expected
    - tool_calls > 2x expected

    Escalation path: TRIVIAL -> SIMPLE -> MODERATE -> COMPLEX
    """

    # Expected values per complexity level
    EXPECTED_VALUES = {
        TaskComplexity.TRIVIAL: {"time": 30.0, "tool_calls": 3},
        TaskComplexity.SIMPLE: {"time": 120.0, "tool_calls": 10},
        TaskComplexity.MODERATE: {"time": 300.0, "tool_calls": 25},
        TaskComplexity.COMPLEX: {"time": 600.0, "tool_calls": 50},
    }

    # Escalation path
    ESCALATION_PATH = [
        TaskComplexity.TRIVIAL,
        TaskComplexity.SIMPLE,
        TaskComplexity.MODERATE,
        TaskComplexity.COMPLEX,
    ]

    def __init__(self) -> None:
        """Initialize the adaptive complexity manager."""
        self.story_signals: dict[str, ExecutionSignals] = {}

    def get_expected_values(self, complexity: TaskComplexity) -> dict[str, float]:
        """Get expected execution values for a complexity level.

        Args:
            complexity: The complexity level.

        Returns:
            Dict with expected time and tool_calls.
        """
        return self.EXPECTED_VALUES.get(
            complexity, {"time": 120.0, "tool_calls": 10}
        )

    def start_tracking(self, story_id: str, complexity: TaskComplexity) -> None:
        """Start tracking execution signals for a story.

        Args:
            story_id: The story identifier.
            complexity: Initial complexity assessment.
        """
        expected = self.get_expected_values(complexity)
        self.story_signals[story_id] = ExecutionSignals(
            expected_time=expected["time"],
            expected_tool_calls=expected["tool_calls"],
        )

    def record_retry(self, story_id: str) -> None:
        """Record a retry for a story.

        Args:
            story_id: The story identifier.
        """
        if story_id in self.story_signals:
            self.story_signals[story_id].retry_count += 1

    def record_tool_call(self, story_id: str) -> None:
        """Record a tool call for a story.

        Args:
            story_id: The story identifier.
        """
        if story_id in self.story_signals:
            self.story_signals[story_id].tool_calls += 1

    def record_error(self, story_id: str) -> None:
        """Record an error for a story.

        Args:
            story_id: The story identifier.
        """
        if story_id in self.story_signals:
            self.story_signals[story_id].error_count += 1

    def record_execution_time(self, story_id: str, time_seconds: float) -> None:
        """Record execution time for a story.

        Args:
            story_id: The story identifier.
            time_seconds: Execution time in seconds.
        """
        if story_id in self.story_signals:
            self.story_signals[story_id].execution_time += time_seconds

    def get_signals(self, story_id: str) -> ExecutionSignals | None:
        """Get current signals for a story.

        Args:
            story_id: The story identifier.

        Returns:
            ExecutionSignals or None if not tracking.
        """
        return self.story_signals.get(story_id)

    def _get_next_level(self, current: TaskComplexity) -> TaskComplexity | None:
        """Get the next escalation level.

        Args:
            current: Current complexity level.

        Returns:
            Next level or None if already at max.
        """
        try:
            current_idx = self.ESCALATION_PATH.index(current)
            if current_idx < len(self.ESCALATION_PATH) - 1:
                return self.ESCALATION_PATH[current_idx + 1]
        except ValueError:
            pass
        return None

    def should_escalate_complexity(
        self, current: TaskComplexity, signals: ExecutionSignals
    ) -> EscalationResult:
        """Check if complexity should be escalated based on signals.

        Args:
            current: Current complexity level.
            signals: Execution signals collected so far.

        Returns:
            EscalationResult with decision and new level.
        """
        reasons = []

        # Check retry count trigger (>= 2)
        if signals.retry_count >= 2:
            reasons.append(f"retry_count={signals.retry_count} (threshold: 2)")

        # Check execution time trigger (> 3x expected)
        if signals.execution_time > signals.expected_time * 3:
            ratio = signals.execution_time / signals.expected_time
            reasons.append(f"execution_time {ratio:.1f}x expected (threshold: 3x)")

        # Check tool calls trigger (> 2x expected)
        if signals.tool_calls > signals.expected_tool_calls * 2:
            ratio = signals.tool_calls / signals.expected_tool_calls
            reasons.append(f"tool_calls {ratio:.1f}x expected (threshold: 2x)")

        # Decide on escalation
        if reasons:
            new_level = self._get_next_level(current)
            if new_level:
                return EscalationResult(
                    should_escalate=True,
                    new_level=new_level,
                    reason="; ".join(reasons),
                    inject_planning=new_level in [
                        TaskComplexity.MODERATE,
                        TaskComplexity.COMPLEX,
                    ],
                )
            else:
                # Already at max level
                return EscalationResult(
                    should_escalate=False,
                    new_level=None,
                    reason=f"Triggers met ({'; '.join(reasons)}) but already at max complexity",
                    inject_planning=True,
                )

        return EscalationResult(
            should_escalate=False,
            new_level=None,
            reason="No escalation triggers met",
            inject_planning=False,
        )

    def check_and_escalate(
        self, story_id: str, current: TaskComplexity
    ) -> EscalationResult:
        """Check signals and escalate if needed (convenience method).

        Args:
            story_id: The story identifier.
            current: Current complexity level.

        Returns:
            EscalationResult with decision.
        """
        signals = self.get_signals(story_id)
        if not signals:
            return EscalationResult(
                should_escalate=False,
                new_level=None,
                reason="No signals tracked for story",
                inject_planning=False,
            )

        return self.should_escalate_complexity(current, signals)

    def reset_story(self, story_id: str) -> None:
        """Reset tracking for a story.

        Args:
            story_id: The story identifier.
        """
        if story_id in self.story_signals:
            del self.story_signals[story_id]

    def get_summary(self, story_id: str) -> dict | None:
        """Get a summary of signals for a story.

        Args:
            story_id: The story identifier.

        Returns:
            Summary dict or None if not tracking.
        """
        signals = self.get_signals(story_id)
        if not signals:
            return None

        return {
            "story_id": story_id,
            "retry_count": signals.retry_count,
            "execution_time": signals.execution_time,
            "tool_calls": signals.tool_calls,
            "error_count": signals.error_count,
            "time_ratio": signals.execution_time / signals.expected_time
            if signals.expected_time
            else 0,
            "tool_calls_ratio": signals.tool_calls / signals.expected_tool_calls
            if signals.expected_tool_calls
            else 0,
        }
