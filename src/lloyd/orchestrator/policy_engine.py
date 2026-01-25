"""Policy Engine for transforming memory into behavior-changing policies.

The Policy Engine evaluates context and applies learned policies to modify
execution behavior - such as skipping agents, injecting validation steps,
biasing tool selection, or triggering warnings.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from lloyd.memory.knowledge import KnowledgeBase

logger = logging.getLogger(__name__)


class PolicyType(str, Enum):
    """Types of policies that can be applied."""

    RETRY = "retry"  # Policies that modify retry behavior
    PLANNING = "planning"  # Policies that affect planning phase
    TOOL = "tool"  # Policies that bias tool selection
    VERIFICATION = "verification"  # Policies that modify verification
    ROUTING = "routing"  # Policies that affect agent routing


@dataclass
class Policy:
    """A policy that can modify execution behavior.

    Attributes:
        name: Human-readable policy name.
        policy_type: The type of policy.
        condition: Callable that takes context and returns True if policy applies.
        action: Callable that takes context and returns modifications.
        confidence: How confident we are in this policy (0.0 to 1.0).
        source: Where this policy came from (default, learned, user).
    """

    name: str
    policy_type: PolicyType
    condition: Callable[[dict[str, Any]], bool]
    action: Callable[[dict[str, Any]], dict[str, Any]]
    confidence: float = 0.5
    source: str = "default"


@dataclass
class PolicyEffect:
    """The effects of evaluated policies.

    Attributes:
        skip_agents: List of agents to skip.
        inject_steps: List of steps to inject before execution.
        tool_bias: Dict mapping tool names to bias scores (positive = prefer).
        warnings: List of warning messages to display.
        context_additions: Additional context to inject into prompts.
        applied_policies: Names of policies that were applied.
    """

    skip_agents: list[str] = field(default_factory=list)
    inject_steps: list[str] = field(default_factory=list)
    tool_bias: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    context_additions: dict[str, Any] = field(default_factory=dict)
    applied_policies: list[str] = field(default_factory=list)


class PolicyEngine:
    """Engine that evaluates context and applies policies.

    The Policy Engine transforms learned patterns and user preferences into
    actionable policies that modify Lloyd's execution behavior.
    """

    def __init__(self, lloyd_dir: Path | None = None) -> None:
        """Initialize the Policy Engine.

        Args:
            lloyd_dir: Lloyd data directory. Defaults to .lloyd
        """
        self.lloyd_dir = lloyd_dir or Path(".lloyd")
        self.knowledge_base = KnowledgeBase(self.lloyd_dir)
        self.policies: list[Policy] = []
        self._register_default_policies()

    def _register_default_policies(self) -> None:
        """Register the default built-in policies."""
        # Policy 1: JWT failure with retry_count >= 2 -> inject env validation
        self.policies.append(
            Policy(
                name="jwt_env_validation",
                policy_type=PolicyType.RETRY,
                condition=lambda ctx: (
                    "jwt" in ctx.get("description", "").lower()
                    and ctx.get("retry_count", 0) >= 2
                ),
                action=lambda ctx: {
                    "inject_steps": ["Validate JWT_SECRET environment variable exists"],
                    "warnings": ["JWT tasks have failed twice - adding env validation step"],
                },
                confidence=0.9,
                source="default",
            )
        )

        # Policy 2: Auth tasks -> require config story completed first
        self.policies.append(
            Policy(
                name="auth_requires_config",
                policy_type=PolicyType.ROUTING,
                condition=lambda ctx: (
                    any(
                        kw in ctx.get("description", "").lower()
                        for kw in ["auth", "login", "oauth", "jwt"]
                    )
                    and "config" in ctx.get("categories", [])
                    and not ctx.get("config_completed", False)
                ),
                action=lambda ctx: {
                    "warnings": ["Auth task detected - ensure config story is complete first"],
                    "context_additions": {"priority_dependency": "config"},
                },
                confidence=0.8,
                source="default",
            )
        )

        # Policy 3: User prefers pytest -> bias tool selection
        self.policies.append(
            Policy(
                name="prefer_pytest",
                policy_type=PolicyType.TOOL,
                condition=lambda ctx: (
                    "pytest" in ctx.get("user_preferences", {}).get("test_framework", "")
                    or "pytest" in ctx.get("project_files", [])
                ),
                action=lambda ctx: {
                    "tool_bias": {"pytest": 1.0, "unittest": -0.5},
                    "context_additions": {"preferred_test_framework": "pytest"},
                },
                confidence=0.95,
                source="default",
            )
        )

        # Policy 4: High-confidence coder on SIMPLE task -> skip reviewer
        self.policies.append(
            Policy(
                name="skip_reviewer_simple",
                policy_type=PolicyType.VERIFICATION,
                condition=lambda ctx: (
                    ctx.get("complexity", "") in ["trivial", "simple"]
                    and ctx.get("coder_success_rate", 0) >= 0.85
                ),
                action=lambda ctx: {
                    "skip_agents": ["reviewer"],
                    "warnings": ["Skipping reviewer for high-confidence simple task"],
                },
                confidence=0.7,
                source="default",
            )
        )

        # Policy 5: Multiple file changes -> require architect review
        self.policies.append(
            Policy(
                name="architect_for_multi_file",
                policy_type=PolicyType.PLANNING,
                condition=lambda ctx: ctx.get("estimated_files_changed", 0) > 5,
                action=lambda ctx: {
                    "inject_steps": ["Get architect review before implementation"],
                    "context_additions": {"requires_architect": True},
                },
                confidence=0.75,
                source="default",
            )
        )

        # Policy 6: Database tasks with retry -> add migration safety
        self.policies.append(
            Policy(
                name="db_migration_safety",
                policy_type=PolicyType.RETRY,
                condition=lambda ctx: (
                    any(
                        kw in ctx.get("description", "").lower()
                        for kw in ["database", "migration", "schema", "table"]
                    )
                    and ctx.get("retry_count", 0) >= 1
                ),
                action=lambda ctx: {
                    "inject_steps": ["Create database backup before migration"],
                    "warnings": ["Database task with retries - adding backup step"],
                },
                confidence=0.85,
                source="default",
            )
        )

    def load_learned_policies(self) -> None:
        """Load additional policies from knowledge base patterns.

        Patterns with frequency >= 3 are converted to policies.
        """
        # Query high-frequency patterns from knowledge base
        all_entries = self.knowledge_base.store.list_all()

        for entry in all_entries:
            if entry.frequency >= 3 and entry.confidence >= 0.6:
                # Convert pattern to policy based on category
                policy = self._entry_to_policy(entry)
                if policy:
                    self.policies.append(policy)

    def _entry_to_policy(self, entry: Any) -> Policy | None:
        """Convert a learning entry to a policy.

        Args:
            entry: Learning entry from knowledge base.

        Returns:
            Policy or None if entry can't be converted.
        """
        # Extract keywords from entry for condition matching
        keywords = set()
        for word in entry.description.lower().split():
            if len(word) > 3:  # Skip short words
                keywords.add(word)

        if not keywords:
            return None

        # Determine policy type based on entry category
        policy_type = PolicyType.ROUTING  # Default
        if "test" in entry.category:
            policy_type = PolicyType.VERIFICATION
        elif "tool" in entry.category:
            policy_type = PolicyType.TOOL
        elif "retry" in entry.category or "error" in entry.category:
            policy_type = PolicyType.RETRY

        # Build condition that checks for keyword overlap
        def make_condition(kws: set[str]) -> Callable[[dict[str, Any]], bool]:
            def condition(ctx: dict[str, Any]) -> bool:
                desc = ctx.get("description", "").lower()
                return any(kw in desc for kw in kws)

            return condition

        # Build action based on entry type
        is_positive = "positive_pattern" in entry.tags or entry.confidence >= 0.7

        def make_action(ent: Any, positive: bool) -> Callable[[dict[str, Any]], dict[str, Any]]:
            def action(ctx: dict[str, Any]) -> dict[str, Any]:
                if positive:
                    return {
                        "context_additions": {
                            "learned_pattern": ent.description,
                            "pattern_confidence": ent.confidence,
                        }
                    }
                else:
                    return {
                        "warnings": [f"Past failure: {ent.description[:100]}"],
                        "context_additions": {"avoid_pattern": ent.description},
                    }

            return action

        return Policy(
            name=f"learned_{entry.id}",
            policy_type=policy_type,
            condition=make_condition(keywords),
            action=make_action(entry, is_positive),
            confidence=entry.confidence,
            source="learned",
        )

    def evaluate(self, context: dict[str, Any]) -> PolicyEffect:
        """Evaluate all policies against the given context.

        Args:
            context: Context dict with keys like:
                - description: Story/task description
                - complexity: Task complexity level
                - categories: List of detected categories
                - retry_count: Number of retries so far
                - user_preferences: User preference dict
                - coder_success_rate: Historical success rate

        Returns:
            PolicyEffect with all applicable modifications.
        """
        effect = PolicyEffect()

        # Load learned policies (could be cached)
        self.load_learned_policies()

        for policy in self.policies:
            try:
                if policy.condition(context):
                    # Apply the policy action
                    action_result = policy.action(context)

                    # Merge results into effect
                    if "skip_agents" in action_result:
                        effect.skip_agents.extend(action_result["skip_agents"])

                    if "inject_steps" in action_result:
                        effect.inject_steps.extend(action_result["inject_steps"])

                    if "tool_bias" in action_result:
                        for tool, bias in action_result["tool_bias"].items():
                            effect.tool_bias[tool] = effect.tool_bias.get(tool, 0) + bias

                    if "warnings" in action_result:
                        effect.warnings.extend(action_result["warnings"])

                    if "context_additions" in action_result:
                        effect.context_additions.update(action_result["context_additions"])

                    effect.applied_policies.append(policy.name)

            except Exception as e:
                # Policy evaluation failed - log but continue
                logger.debug(f"Policy {policy.name} evaluation failed: {e}")

        return effect

    def add_policy(self, policy: Policy) -> None:
        """Add a new policy to the engine.

        Args:
            policy: Policy to add.
        """
        self.policies.append(policy)

    def remove_policy(self, name: str) -> bool:
        """Remove a policy by name.

        Args:
            name: Policy name to remove.

        Returns:
            True if removed, False if not found.
        """
        original_len = len(self.policies)
        self.policies = [p for p in self.policies if p.name != name]
        return len(self.policies) < original_len

    def list_policies(self) -> list[dict[str, Any]]:
        """List all registered policies.

        Returns:
            List of policy info dicts.
        """
        return [
            {
                "name": p.name,
                "type": p.policy_type.value,
                "confidence": p.confidence,
                "source": p.source,
            }
            for p in self.policies
        ]
