"""System architect agent for AEGIS."""

from typing import Any

from lloyd.agents.base import AgentConfig, BaseAgent


class ArchitectAgent(BaseAgent):
    """System Architect agent.

    Designs scalable, maintainable system architectures that balance
    simplicity with extensibility.
    """

    def __init__(self) -> None:
        """Initialize the architect agent with default configuration."""
        config = AgentConfig(
            role="System Architect",
            goal="Design scalable, maintainable system architectures that balance "
            "simplicity with extensibility",
            backstory=(
                "You are a principal engineer with 15+ years of experience designing "
                "systems at scale. You believe in YAGNI (You Aren't Gonna Need It) and "
                "favor simple solutions over complex ones. You document your decisions "
                "and their rationale."
            ),
            tools=["file_read", "file_write", "web_search"],
            allow_delegation=True,
            verbose=True,
        )
        super().__init__(config)

    def get_tools(self) -> list[Any]:
        """Get tools for the architect agent.

        Returns:
            List of tools including file operations and web search.
        """
        from lloyd.tools import get_tools_by_names

        return get_tools_by_names(self.config.tools)
