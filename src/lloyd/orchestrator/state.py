"""Global state management for Lloyd."""

from typing import Any

from pydantic import BaseModel, Field


class LloydState(BaseModel):
    """Global state for the Lloyd flow."""

    idea: str = ""
    prd: dict[str, Any] = Field(default_factory=dict)
    current_story: dict[str, Any] | None = None
    current_stories: list[dict[str, Any]] = Field(default_factory=list)
    iteration: int = 0
    max_iterations: int = 50
    max_parallel: int = 3
    status: str = "idle"  # idle, planning, executing, testing, complete, blocked
    parallel_mode: bool = True
    complexity: str = "moderate"  # trivial, simple, moderate, complex

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    def is_complete(self) -> bool:
        """Check if all work is complete.

        Returns:
            True if status is complete.
        """
        return self.status == "complete"

    def is_blocked(self) -> bool:
        """Check if execution is blocked.

        Returns:
            True if status is blocked or max iterations reached.
        """
        return self.status == "blocked" or self.iteration >= self.max_iterations

    def can_continue(self) -> bool:
        """Check if execution can continue.

        Returns:
            True if not complete and not blocked.
        """
        return not self.is_complete() and not self.is_blocked()
