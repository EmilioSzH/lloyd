"""Senior software engineer agent for AEGIS."""

from typing import Any

from lloyd.agents.base import AgentConfig, BaseAgent


class CoderAgent(BaseAgent):
    """Senior Software Engineer agent.

    Writes clean, tested, production-ready code that solves the problem at hand.
    """

    def __init__(self) -> None:
        """Initialize the coder agent with default configuration."""
        config = AgentConfig(
            role="Senior Software Engineer",
            goal="Write clean, tested, production-ready code that solves the problem at hand",
            backstory=(
                "You are a pragmatic engineer who values working software over perfect "
                "abstractions. You write code that your future self will thank you for—"
                "clear variable names, helpful comments, and comprehensive tests. "
                "You follow TDD when appropriate."
            ),
            tools=["file_read", "file_write", "code_exec", "shell"],
            allow_delegation=False,
            verbose=True,
        )
        super().__init__(config)

    def get_tools(self) -> list[Any]:
        """Get tools for the coder agent.

        Returns:
            List of tools including file operations, code execution, and shell.
        """
        from lloyd.tools import get_tools_by_names

        return get_tools_by_names(self.config.tools)
