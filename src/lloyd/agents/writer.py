"""Technical writer agent for AEGIS."""

from typing import Any

from lloyd.agents.base import AgentConfig, BaseAgent


class WriterAgent(BaseAgent):
    """Technical Writer agent.

    Creates clear, accurate documentation that helps users and developers
    understand the system.
    """

    def __init__(self) -> None:
        """Initialize the writer agent with default configuration."""
        config = AgentConfig(
            role="Technical Writer",
            goal="Create clear, accurate documentation that helps users and developers "
            "understand the system",
            backstory=(
                "You believe good documentation is as important as good code. You "
                "write for your audience—concise for experts, detailed for beginners. "
                "You keep docs in sync with code."
            ),
            tools=["file_read", "file_write", "web_search"],
            allow_delegation=False,
            verbose=True,
        )
        super().__init__(config)

    def get_tools(self) -> list[Any]:
        """Get tools for the writer agent.

        Returns:
            List of tools including file operations and web search.
        """
        from lloyd.tools import get_tools_by_names

        return get_tools_by_names(self.config.tools)
