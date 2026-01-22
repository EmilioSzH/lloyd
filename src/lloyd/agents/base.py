"""Base agent class for AEGIS."""

from abc import ABC, abstractmethod
from typing import Any

from crewai import Agent
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for an AEGIS agent."""

    role: str = Field(..., description="The agent's role title")
    goal: str = Field(..., description="The agent's primary objective")
    backstory: str = Field(..., description="The agent's background and expertise")
    tools: list[str] = Field(default_factory=list, description="List of tool names")
    allow_delegation: bool = Field(default=False, description="Whether agent can delegate")
    verbose: bool = Field(default=True, description="Whether to show verbose output")


class BaseAgent(ABC):
    """Base class for all AEGIS agents.

    Provides common functionality and interface that all specialized
    agents inherit from.
    """

    def __init__(self, config: AgentConfig) -> None:
        """Initialize the agent with configuration.

        Args:
            config: Agent configuration including role, goal, backstory, etc.
        """
        self.config = config
        self._agent: Agent | None = None

    @property
    def role(self) -> str:
        """Get the agent's role."""
        return self.config.role

    @property
    def goal(self) -> str:
        """Get the agent's goal."""
        return self.config.goal

    @property
    def backstory(self) -> str:
        """Get the agent's backstory."""
        return self.config.backstory

    @abstractmethod
    def get_tools(self) -> list[Any]:
        """Get the tools available to this agent.

        Must be implemented by subclasses to return appropriate tools.

        Returns:
            List of tool instances for the agent.
        """
        pass

    def create_agent(self) -> Agent:
        """Create and return a CrewAI Agent instance.

        Returns:
            Configured CrewAI Agent.
        """
        if self._agent is None:
            self._agent = Agent(
                role=self.config.role,
                goal=self.config.goal,
                backstory=self.config.backstory,
                tools=self.get_tools(),
                allow_delegation=self.config.allow_delegation,
                verbose=self.config.verbose,
            )
        return self._agent

    def execute(self, task_description: str, context: dict[str, Any] | None = None) -> str:
        """Execute a task with this agent.

        Args:
            task_description: Description of the task to execute.
            context: Optional context dictionary with additional information.

        Returns:
            Result of task execution as a string.
        """
        agent = self.create_agent()
        # Note: In CrewAI, tasks are executed through crews, not directly.
        # This method provides a simplified interface for single-agent execution.
        from crewai import Crew, Task

        task = Task(
            description=task_description,
            expected_output="Detailed result of the task execution",
            agent=agent,
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=self.config.verbose,
        )

        result = crew.kickoff()
        return str(result)

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(role='{self.config.role}')"
