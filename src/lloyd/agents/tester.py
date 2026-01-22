"""QA engineer agent for AEGIS."""

from typing import Any

from lloyd.agents.base import AgentConfig, BaseAgent


class TesterAgent(BaseAgent):
    """QA Engineer agent.

    Ensures code quality through comprehensive testing—unit, integration,
    and end-to-end.
    """

    def __init__(self) -> None:
        """Initialize the tester agent with default configuration."""
        config = AgentConfig(
            role="QA Engineer",
            goal="Ensure code quality through comprehensive testing—unit, integration, "
            "and end-to-end",
            backstory=(
                "You have a knack for finding edge cases and breaking things. You "
                "write tests that actually catch bugs, not just increase coverage "
                "numbers. You believe tests are documentation."
            ),
            tools=["file_read", "file_write", "code_exec", "shell"],
            allow_delegation=False,
            verbose=True,
        )
        super().__init__(config)

    def get_tools(self) -> list[Any]:
        """Get tools for the tester agent.

        Returns:
            List of tools including file operations, code execution, and shell.
        """
        from lloyd.tools import get_tools_by_names

        return get_tools_by_names(self.config.tools)
