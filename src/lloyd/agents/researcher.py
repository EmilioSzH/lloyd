"""Technical researcher agent for AEGIS."""

from typing import Any

from lloyd.agents.base import AgentConfig, BaseAgent


class ResearcherAgent(BaseAgent):
    """Technical Researcher agent.

    Finds and synthesizes relevant technical information, best practices,
    and existing solutions.
    """

    def __init__(self) -> None:
        """Initialize the researcher agent with default configuration."""
        config = AgentConfig(
            role="Technical Researcher",
            goal="Find and synthesize relevant technical information, best practices, "
            "and existing solutions",
            backstory=(
                "You are a research scientist who loves diving deep into documentation, "
                "papers, and codebases. You separate fact from opinion and always cite "
                "your sources. You're particularly skilled at finding non-obvious "
                "solutions to technical problems."
            ),
            tools=["web_search", "github_search", "file_read"],
            allow_delegation=False,
            verbose=True,
        )
        super().__init__(config)

    def get_tools(self) -> list[Any]:
        """Get tools for the researcher agent.

        Returns:
            List of tools including web search, GitHub search, and file read.
        """
        from lloyd.tools import get_tools_by_names

        return get_tools_by_names(self.config.tools)
