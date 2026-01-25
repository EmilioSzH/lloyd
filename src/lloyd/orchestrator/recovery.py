"""Failure Escalation Ladder for progressive recovery strategies.

Replaces simple "3 failures = blocked" with a progressive escalation approach
that tries different recovery strategies before blocking.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class RecoveryAction(str, Enum):
    """Types of recovery actions."""

    SIMPLE_RETRY = "simple_retry"
    ALTERNATE_APPROACH = "alternate_approach"
    INJECT_ARCHITECT = "inject_architect"
    ASK_HUMAN = "ask_human"
    REDUCE_SCOPE = "reduce_scope"
    MARK_BLOCKED = "mark_blocked"


@dataclass
class RecoveryStrategy:
    """A recovery strategy with its action and description.

    Attributes:
        action: The type of recovery action.
        description: Human-readable description of the strategy.
        requires_human: Whether this strategy requires human input.
    """

    action: RecoveryAction
    description: str
    requires_human: bool = False


@dataclass
class HumanQuestion:
    """A question to ask a human during recovery.

    Attributes:
        question: The main question text.
        context: Background context for the question.
        error_history: List of previous errors.
        options: Suggested options for the human.
    """

    question: str
    context: str
    error_history: list[str]
    options: list[str]


class FailureEscalationLadder:
    """Progressive failure escalation with recovery strategies.

    Escalation levels:
    - Attempt 1: Simple retry
    - Attempt 2: Alternate approach (generate different strategy)
    - Attempt 3: Inject architect agent for analysis
    - Attempt 4: Ask human with SPECIFIC question including error history
    - Attempt 5: Reduce scope to 80% functionality
    - Attempt 6: Mark blocked (last resort)
    """

    def __init__(self) -> None:
        """Initialize the escalation ladder."""
        self.escalation_levels: dict[int, RecoveryStrategy] = {
            1: RecoveryStrategy(
                action=RecoveryAction.SIMPLE_RETRY,
                description="Simple retry with same approach",
            ),
            2: RecoveryStrategy(
                action=RecoveryAction.ALTERNATE_APPROACH,
                description="Generate alternate implementation strategy",
            ),
            3: RecoveryStrategy(
                action=RecoveryAction.INJECT_ARCHITECT,
                description="Inject architect agent for deeper analysis",
            ),
            4: RecoveryStrategy(
                action=RecoveryAction.ASK_HUMAN,
                description="Ask human for guidance with specific question",
                requires_human=True,
            ),
            5: RecoveryStrategy(
                action=RecoveryAction.REDUCE_SCOPE,
                description="Reduce scope to 80% of original functionality",
            ),
            6: RecoveryStrategy(
                action=RecoveryAction.MARK_BLOCKED,
                description="Mark story as blocked (last resort)",
            ),
        }
        self.error_history: dict[str, list[str]] = {}  # story_id -> errors

    def record_failure(self, story_id: str, error: str) -> None:
        """Record a failure for a story.

        Args:
            story_id: The story identifier.
            error: Error message or description.
        """
        if story_id not in self.error_history:
            self.error_history[story_id] = []
        self.error_history[story_id].append(error)

    def get_error_history(self, story_id: str) -> list[str]:
        """Get error history for a story.

        Args:
            story_id: The story identifier.

        Returns:
            List of error messages.
        """
        return self.error_history.get(story_id, [])

    def get_recovery_action(self, attempt: int) -> tuple[RecoveryAction, str]:
        """Get the recovery action for a given attempt number.

        Args:
            attempt: The current attempt number (1-indexed).

        Returns:
            Tuple of (RecoveryAction, description).
        """
        # Clamp to valid range
        level = min(max(attempt, 1), 6)
        strategy = self.escalation_levels[level]
        return strategy.action, strategy.description

    def _generate_alternate_approach(
        self, story: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate an alternate implementation approach.

        Args:
            story: The story dict.
            context: Execution context with error history.

        Returns:
            Modified context with alternate approach suggestion.
        """
        errors = context.get("error_history", [])
        error_summary = "; ".join(errors[-3:]) if errors else "Previous attempts failed"

        alternate_prompt = f"""
The previous approach failed with: {error_summary}

Try a DIFFERENT strategy:
- If the last approach used external libraries, try standard library
- If the last approach was complex, try a simpler solution
- If the last approach involved file operations, check permissions first
- Consider breaking the task into smaller steps

Story: {story.get('title', '')}
Description: {story.get('description', '')}
"""
        return {
            "alternate_approach_prompt": alternate_prompt,
            "use_alternate_strategy": True,
        }

    def _build_human_question(
        self, story: dict[str, Any], context: dict[str, Any]
    ) -> HumanQuestion:
        """Build a specific question to ask the human.

        Args:
            story: The story dict.
            context: Execution context with error history.

        Returns:
            HumanQuestion with specific details.
        """
        story_id = story.get("id", "unknown")
        errors = self.get_error_history(story_id) or context.get("error_history", [])

        # Build a specific question based on error patterns
        question = f"How should we handle the failures in '{story.get('title', 'this task')}'?"

        # Analyze errors to suggest options
        options = [
            "Provide specific implementation guidance",
            "Skip this task and continue",
            "Modify the acceptance criteria",
            "Break into smaller sub-tasks",
        ]

        # Add error-specific options
        error_text = " ".join(errors).lower()
        if "permission" in error_text or "access" in error_text:
            options.insert(0, "Grant necessary permissions/access")
        if "dependency" in error_text or "import" in error_text:
            options.insert(0, "Install missing dependencies")
        if "timeout" in error_text or "connection" in error_text:
            options.insert(0, "Check network/service availability")

        return HumanQuestion(
            question=question,
            context=f"Story: {story.get('title', '')}\n\nDescription: {story.get('description', '')}",
            error_history=errors[-5:],  # Last 5 errors
            options=options[:4],  # Max 4 options
        )

    def _reduce_scope(
        self, story: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Reduce the scope of the task to 80% functionality.

        Args:
            story: The story dict.
            context: Execution context.

        Returns:
            Modified story/context with reduced scope.
        """
        original_criteria = story.get("acceptanceCriteria", [])

        # Keep only 80% of criteria (round up)
        reduced_count = max(1, int(len(original_criteria) * 0.8 + 0.5))
        reduced_criteria = original_criteria[:reduced_count]

        return {
            "reduced_scope": True,
            "original_criteria_count": len(original_criteria),
            "reduced_criteria_count": reduced_count,
            "reduced_acceptance_criteria": reduced_criteria,
            "scope_note": "Scope reduced to 80% - focus on core functionality first",
        }

    def execute_recovery(
        self,
        action: RecoveryAction,
        story: dict[str, Any],
        context: dict[str, Any],
        human_input_handler: Callable[[HumanQuestion], str] | None = None,
    ) -> dict[str, Any]:
        """Execute a recovery action and return modifications.

        Args:
            action: The recovery action to execute.
            story: The story dict.
            context: Current execution context.
            human_input_handler: Optional callable for getting human input.

        Returns:
            Dict with modifications to apply, including:
            - continue_execution: bool
            - modifications: dict of changes to make
            - human_question: HumanQuestion if action is ASK_HUMAN
        """
        result: dict[str, Any] = {
            "continue_execution": True,
            "modifications": {},
            "action_taken": action.value,
        }

        if action == RecoveryAction.SIMPLE_RETRY:
            # No modifications, just retry
            result["modifications"] = {"retry_note": "Simple retry with same approach"}

        elif action == RecoveryAction.ALTERNATE_APPROACH:
            result["modifications"] = self._generate_alternate_approach(story, context)

        elif action == RecoveryAction.INJECT_ARCHITECT:
            result["modifications"] = {
                "inject_architect": True,
                "architect_prompt": f"""
Analyze why this story keeps failing and provide architectural guidance:

Story: {story.get('title', '')}
Description: {story.get('description', '')}
Previous errors: {context.get('error_history', [])}

Provide:
1. Root cause analysis
2. Recommended approach
3. Potential blockers to watch for
""",
            }

        elif action == RecoveryAction.ASK_HUMAN:
            question = self._build_human_question(story, context)
            result["human_question"] = question
            result["requires_human_input"] = True

            # If we have a handler, get input
            if human_input_handler:
                human_response = human_input_handler(question)
                result["modifications"] = {
                    "human_guidance": human_response,
                    "has_human_input": True,
                }
            else:
                result["continue_execution"] = False  # Can't continue without human

        elif action == RecoveryAction.REDUCE_SCOPE:
            result["modifications"] = self._reduce_scope(story, context)

        elif action == RecoveryAction.MARK_BLOCKED:
            result["continue_execution"] = False
            result["modifications"] = {
                "status": "blocked",
                "blocked_reason": "Exhausted all recovery strategies",
                "error_history": self.get_error_history(story.get("id", "")),
            }

        return result

    def should_escalate(self, story_id: str, current_attempt: int) -> bool:
        """Check if we should escalate to the next level.

        Args:
            story_id: The story identifier.
            current_attempt: Current attempt number.

        Returns:
            True if should escalate (attempt failed).
        """
        # Always escalate after each failure until we hit max level
        return current_attempt < 6

    def reset_story(self, story_id: str) -> None:
        """Reset escalation state for a story.

        Args:
            story_id: The story identifier.
        """
        if story_id in self.error_history:
            del self.error_history[story_id]

    def get_escalation_summary(self, story_id: str) -> dict[str, Any]:
        """Get a summary of escalation state for a story.

        Args:
            story_id: The story identifier.

        Returns:
            Summary dict with error count and history.
        """
        errors = self.get_error_history(story_id)
        return {
            "story_id": story_id,
            "error_count": len(errors),
            "errors": errors,
            "current_level": min(len(errors) + 1, 6),
            "next_action": self.get_recovery_action(len(errors) + 1),
        }
