"""Requirements analyst agent for AEGIS."""

from typing import Any

from lloyd.agents.base import AgentConfig, BaseAgent


class AnalystAgent(BaseAgent):
    """Senior Requirements Analyst agent.

    Transforms vague product ideas into precise, actionable requirements
    with clear acceptance criteria.
    """

    def __init__(self) -> None:
        """Initialize the analyst agent with default configuration."""
        config = AgentConfig(
            role="Senior Requirements Analyst",
            goal="Transform vague product ideas into precise, actionable requirements "
            "with clear acceptance criteria",
            backstory=(
                "You are a seasoned product analyst who has worked at top tech companies. "
                "You excel at asking clarifying questions, identifying edge cases, and "
                "breaking down complex ideas into manageable pieces. You never assume—"
                "you always verify."
            ),
            tools=["web_search", "file_read"],
            allow_delegation=False,
            verbose=True,
        )
        super().__init__(config)

    def get_tools(self) -> list[Any]:
        """Get tools for the analyst agent.

        Returns:
            List of tools including web search and file read.
        """
        # Tools will be loaded from the tools module
        from lloyd.tools import get_tools_by_names

        return get_tools_by_names(self.config.tools)
