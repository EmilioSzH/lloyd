"""Planning crew for Lloyd."""

from pathlib import Path
from typing import Any

import yaml
from crewai import Agent, Crew, Process, Task

from lloyd.config import get_llm
from lloyd.tools import get_tools_by_names


class PlanningCrew:
    """Planning crew for requirements analysis and architecture design."""

    def __init__(self) -> None:
        """Initialize the planning crew."""
        self.agents_config = self._load_config("agents.yaml")
        self.tasks_config = self._load_config("tasks.yaml")
        self._agents: dict[str, Agent] = {}
        self._crew: Crew | None = None

    def _load_config(self, filename: str) -> dict[str, Any]:
        """Load a YAML config file.

        Args:
            filename: Name of the config file.

        Returns:
            Parsed YAML content.
        """
        config_path = Path(__file__).parent / filename
        with open(config_path) as f:
            return yaml.safe_load(f)

    def _create_agent(self, name: str) -> Agent:
        """Create an agent from config.

        Args:
            name: Agent name from config.

        Returns:
            Configured CrewAI Agent.
        """
        if name in self._agents:
            return self._agents[name]

        config = self.agents_config[name]
        tools = get_tools_by_names(config.get("tools", []))

        agent = Agent(
            role=config["role"],
            goal=config["goal"],
            backstory=config["backstory"],
            tools=tools,
            llm=get_llm(),
            allow_delegation=config.get("allow_delegation", False),
            verbose=config.get("verbose", True),
        )

        self._agents[name] = agent
        return agent

    def _create_task(self, name: str, inputs: dict[str, Any]) -> Task:
        """Create a task from config.

        Args:
            name: Task name from config.
            inputs: Input values for task description formatting.

        Returns:
            Configured CrewAI Task.
        """
        config = self.tasks_config[name]
        agent = self._create_agent(config["agent"])

        # Format description with inputs
        description = config["description"].format(**inputs)

        return Task(
            description=description,
            expected_output=config["expected_output"],
            agent=agent,
        )

    def create_crew(self, inputs: dict[str, Any]) -> Crew:
        """Create the planning crew with all tasks.

        Args:
            inputs: Input values for task formatting.

        Returns:
            Configured Crew ready for execution.
        """
        tasks = [
            self._create_task("analyze_idea", inputs),
            self._create_task("research_solutions", inputs),
            self._create_task("design_architecture", inputs),
        ]

        self._crew = Crew(
            agents=list(self._agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )

        return self._crew

    def kickoff(self, inputs: dict[str, Any]) -> Any:
        """Run the planning crew.

        Args:
            inputs: Input dictionary with 'idea' key.

        Returns:
            Crew execution result.
        """
        crew = self.create_crew(inputs)
        return crew.kickoff()
