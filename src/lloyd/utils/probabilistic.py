"""Probabilistic Verification Skipping for Lloyd.

Provides functions for making probabilistic decisions about
verification, learning injection, and complexity reassessment.
"""

import random
from dataclasses import dataclass
from typing import Any


@dataclass
class SkipDecision:
    """Result of a skip decision.

    Attributes:
        should_skip: Whether to skip.
        reason: Explanation of the decision.
        confidence: Confidence in the decision (0.0-1.0).
    """

    should_skip: bool
    reason: str
    confidence: float


@dataclass
class ComplexityDecision:
    """Result of complexity reassessment decision.

    Attributes:
        should_reassess: Whether to reassess complexity.
        reason: Explanation of the decision.
    """

    should_reassess: bool
    reason: str


def should_skip_verification(
    complexity: str,
    success_rate: float,
    threshold: float = 0.85,
    _random_func: Any | None = None,
) -> SkipDecision:
    """Determine if verification can be skipped for a task.

    Only skips for TRIVIAL/SIMPLE complexity with high success rates.
    This saves cost by not running verification on likely-successful tasks.

    Args:
        complexity: Task complexity (TRIVIAL, SIMPLE, MODERATE, COMPLEX).
        success_rate: Historical success rate for similar tasks (0.0-1.0).
        threshold: Minimum success rate to consider skipping.
        _random_func: Optional random function for testing.

    Returns:
        SkipDecision with recommendation.
    """
    complexity_upper = complexity.upper()

    # Never skip for complex tasks
    if complexity_upper in ("MODERATE", "COMPLEX"):
        return SkipDecision(
            should_skip=False,
            reason=f"{complexity_upper} tasks always require verification",
            confidence=1.0,
        )

    # Need high success rate to skip
    if success_rate < threshold:
        return SkipDecision(
            should_skip=False,
            reason=f"Success rate {success_rate:.0%} below threshold {threshold:.0%}",
            confidence=1.0,
        )

    # For trivial/simple with high success rate, skip verification
    return SkipDecision(
        should_skip=True,
        reason=f"High success rate ({success_rate:.0%}) for {complexity_upper} task",
        confidence=success_rate,
    )


def should_inject_learning(
    confidence: float,
    threshold: float = 0.7,
) -> bool:
    """Determine if a learning should be injected into context.

    Only injects learnings with sufficient confidence to avoid
    polluting context with low-quality information.

    Args:
        confidence: Confidence score of the learning (0.0-1.0).
        threshold: Minimum confidence to inject.

    Returns:
        True if learning should be injected.
    """
    return confidence >= threshold


def should_reassess_complexity(
    complexity: str,
    retry_count: int,
    _random_func: Any | None = None,
) -> ComplexityDecision:
    """Determine if task complexity should be reassessed.

    For TRIVIAL tasks, only reassesses 20% of the time unless
    retries indicate the task is harder than expected.

    Args:
        complexity: Current task complexity.
        retry_count: Number of retries so far.
        _random_func: Optional random function for testing.

    Returns:
        ComplexityDecision with recommendation.
    """
    complexity_upper = complexity.upper()
    rand = _random_func or random.random

    # Always reassess if retrying
    if retry_count >= 2:
        return ComplexityDecision(
            should_reassess=True,
            reason=f"Retry count {retry_count} indicates complexity mismatch",
        )

    # Always reassess MODERATE and COMPLEX
    if complexity_upper in ("MODERATE", "COMPLEX"):
        return ComplexityDecision(
            should_reassess=True,
            reason=f"{complexity_upper} tasks always reassess",
        )

    # TRIVIAL/SIMPLE: only reassess 20% of the time
    if complexity_upper == "TRIVIAL":
        if rand() <= 0.2:
            return ComplexityDecision(
                should_reassess=True,
                reason="Random sample for TRIVIAL task",
            )
        return ComplexityDecision(
            should_reassess=False,
            reason="Skipping reassessment for TRIVIAL task (80% skip rate)",
        )

    # SIMPLE: reassess 40% of the time
    if complexity_upper == "SIMPLE":
        if rand() <= 0.4:
            return ComplexityDecision(
                should_reassess=True,
                reason="Random sample for SIMPLE task",
            )
        return ComplexityDecision(
            should_reassess=False,
            reason="Skipping reassessment for SIMPLE task (60% skip rate)",
        )

    # Default: reassess
    return ComplexityDecision(
        should_reassess=True,
        reason="Default to reassess for unknown complexity",
    )


def calculate_skip_probability(
    complexity: str,
    success_rate: float,
    retry_count: int = 0,
) -> float:
    """Calculate the probability of skipping verification.

    Combines multiple factors to produce a skip probability.

    Args:
        complexity: Task complexity.
        success_rate: Historical success rate.
        retry_count: Number of retries.

    Returns:
        Probability of skipping (0.0-1.0).
    """
    complexity_upper = complexity.upper()

    # Base probability by complexity
    base_prob = {
        "TRIVIAL": 0.8,
        "SIMPLE": 0.6,
        "MODERATE": 0.2,
        "COMPLEX": 0.0,
    }.get(complexity_upper, 0.3)

    # Adjust by success rate
    prob = base_prob * success_rate

    # Reduce by retry count
    if retry_count > 0:
        prob *= 0.5 ** retry_count  # Halve for each retry

    return min(1.0, max(0.0, prob))


def should_skip_based_on_history(
    task_type: str,
    history: list[dict[str, Any]],
    min_samples: int = 5,
) -> SkipDecision:
    """Determine if verification can be skipped based on task history.

    Analyzes historical execution results for similar tasks.

    Args:
        task_type: Type of task (e.g., "coding", "testing").
        history: List of historical results with 'success' and 'task_type' keys.
        min_samples: Minimum samples needed for a decision.

    Returns:
        SkipDecision with recommendation.
    """
    # Filter history for matching task type
    matching = [h for h in history if h.get("task_type") == task_type]

    if len(matching) < min_samples:
        return SkipDecision(
            should_skip=False,
            reason=f"Insufficient history ({len(matching)}/{min_samples} samples)",
            confidence=0.0,
        )

    # Calculate success rate from history
    successes = sum(1 for h in matching if h.get("success", False))
    success_rate = successes / len(matching)

    if success_rate >= 0.9:
        return SkipDecision(
            should_skip=True,
            reason=f"High historical success rate: {success_rate:.0%} ({len(matching)} samples)",
            confidence=success_rate,
        )

    return SkipDecision(
        should_skip=False,
        reason=f"Historical success rate {success_rate:.0%} below threshold",
        confidence=success_rate,
    )


def get_sampling_rate(complexity: str) -> float:
    """Get the sampling rate for verification based on complexity.

    Returns the fraction of tasks that should be verified.

    Args:
        complexity: Task complexity.

    Returns:
        Sampling rate (0.0-1.0), where 1.0 means verify all.
    """
    complexity_upper = complexity.upper()

    rates = {
        "TRIVIAL": 0.2,  # Verify 20% of trivial tasks
        "SIMPLE": 0.4,  # Verify 40% of simple tasks
        "MODERATE": 0.8,  # Verify 80% of moderate tasks
        "COMPLEX": 1.0,  # Always verify complex tasks
    }

    return rates.get(complexity_upper, 1.0)


def should_sample_for_verification(
    complexity: str,
    _random_func: Any | None = None,
) -> bool:
    """Determine if this task should be sampled for verification.

    Uses the sampling rate for the complexity level.

    Args:
        complexity: Task complexity.
        _random_func: Optional random function for testing.

    Returns:
        True if task should be verified.
    """
    rand = _random_func or random.random
    rate = get_sampling_rate(complexity)
    return rand() <= rate
