"""Code reviewer agent for AEGIS."""

from typing import Any

from lloyd.agents.base import AgentConfig, BaseAgent


class ReviewerAgent(BaseAgent):
    """Code Reviewer agent.

    Maintains code quality standards and catches issues before they reach production.
    """

    def __init__(self) -> None:
        """Initialize the reviewer agent with default configuration."""
        config = AgentConfig(
            role="Code Reviewer",
            goal="Maintain code quality standards and catch issues before they reach production",
            backstory=(
                "You've reviewed thousands of PRs and have seen every anti-pattern. "
                "You give constructive feedback that helps engineers grow. You focus "
                "on correctness, maintainability, and security."
            ),
            tools=["file_read", "github"],
            allow_delegation=False,
            verbose=True,
        )
        super().__init__(config)

    def get_tools(self) -> list[Any]:
        """Get tools for the reviewer agent.

        Returns:
            List of tools including file read and GitHub operations.
        """
        from lloyd.tools import get_tools_by_names

        return get_tools_by_names(self.config.tools)
