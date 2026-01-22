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

        # Check trivial patterns first
        for pattern in self.TRIVIAL_PATTERNS:
            if re.search(pattern, idea_lower):
                if self._has_specific_target(idea):
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

        # Simple: short and focused with specific target
        word_count = len(idea.split())
        if word_count < 15 and self._has_specific_target(idea):
            return ComplexityAssessment(
                complexity=TaskComplexity.SIMPLE,
                reasoning="Short request with specific target",
                suggested_agents=["planner", "executor"],
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
