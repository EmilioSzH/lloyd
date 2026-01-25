"""Centralized enums for Lloyd orchestration.

This module provides all status and type enums used throughout Lloyd,
replacing magic strings with type-safe constants.
"""

from enum import Enum


class FlowStatus(str, Enum):
    """Lloyd workflow status."""

    IDLE = "idle"
    PLANNING = "planning"
    DECOMPOSING = "decomposing"
    EXECUTING = "executing"
    TESTING = "testing"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    FAILED = "failed"
    BLOCKED = "blocked"


class StoryStatus(str, Enum):
    """Story execution status.

    Note: This is also defined in memory/prd_manager.py for Pydantic models.
    Import from there for PRD-related code.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class TaskComplexity(str, Enum):
    """Task complexity levels for adaptive execution."""

    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class RiskLevel(str, Enum):
    """Self-modification risk levels."""

    SAFE = "safe"
    MODERATE = "moderate"
    RISKY = "risky"
    BLOCKED = "blocked"


class InputType(str, Enum):
    """Types of user input."""

    IDEA = "idea"
    SPEC = "spec"
    QUESTION = "question"
    COMMAND = "command"
    CLARIFICATION = "clarification"


class RecoveryAction(str, Enum):
    """Recovery actions for failed tasks."""

    RETRY = "retry"
    SIMPLIFY = "simplify"
    DECOMPOSE = "decompose"
    ESCALATE_COMPLEXITY = "escalate_complexity"
    REDUCE_SCOPE = "reduce_scope"
    HUMAN_INTERVENTION = "human_intervention"


class PolicyType(str, Enum):
    """Types of policies that can be applied."""

    RETRY = "retry"
    PLANNING = "planning"
    TOOL = "tool"
    VERIFICATION = "verification"
    ROUTING = "routing"


class ExecutionMode(str, Enum):
    """Execution modes for Lloyd."""

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DRY_RUN = "dry_run"


class IdeaStatus(str, Enum):
    """Status of an idea in the queue."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
