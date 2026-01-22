"""Quality crew for Lloyd."""

from pathlib import Path
from typing import Any

import yaml
from crewai import Agent, Crew, Process, Task

from lloyd.config import get_llm
from lloyd.tools import get_tools_by_names


class QualityCrew:
    """Quality crew for testing and review."""

    def __init__(self) -> None:
        """Initialize the quality crew."""
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
        """Create the quality crew with verification tasks.

        Args:
            inputs: Input values including story and execution details.

        Returns:
            Configured Crew ready for execution.
        """
        story = inputs.get("story", {})
        execution_result = inputs.get("execution_result", "")
        acceptance_criteria = inputs.get("acceptance_criteria", [])

        formatted_inputs = {
            "story_title": story.get("title", "Unknown Story"),
            "acceptance_criteria": "\n".join(f"- {c}" for c in acceptance_criteria),
            "execution_result": str(execution_result)[:1000],
            "test_results": "",  # Filled by test task
            "review_results": "",  # Filled by review task
        }

        tasks = [
            self._create_task("run_tests", formatted_inputs),
            self._create_task("review_code", formatted_inputs),
            self._create_task("verify_acceptance", formatted_inputs),
        ]

        self._crew = Crew(
            agents=list(self._agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
        )

        return self._crew

    def kickoff(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Run the quality crew.

        Args:
            inputs: Input dictionary with story, execution_result, acceptance_criteria.

        Returns:
            Dictionary with 'passes' key and verification details.
        """
        crew = self.create_crew(inputs)
        result = crew.kickoff()

        # Parse result to determine if story passes
        result_str = str(result).lower()
        passes = "passes: true" in result_str or (
            "all criteria met" in result_str and "fail" not in result_str
        )

        return {"passes": passes, "details": str(result)}
