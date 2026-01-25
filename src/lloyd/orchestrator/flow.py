"""Main Lloyd orchestration flow."""

import logging
import os
import sys
import uuid
from pathlib import Path
from typing import Any

# Configure module logger
logger = logging.getLogger(__name__)

# Fix Windows console encoding
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        # Python versions < 3.7 don't have reconfigure
        logger.debug("Console reconfigure not available on this Python version")
    except Exception as e:
        # Log the actual error for debugging
        logger.warning(f"Failed to configure Windows console encoding: {e}")

from rich.console import Console

from lloyd.crews.execution import ExecutionCrew
from lloyd.crews.planning import PlanningCrew
from lloyd.crews.quality import QualityCrew
from lloyd.orchestrator.iterative_executor import IterativeExecutor, get_isolated_workspace
from lloyd.memory.prd_manager import PRD, PRDManager, Story
from lloyd.memory.progress import ProgressTracker
from lloyd.orchestrator.complexity import ComplexityAssessor, TaskComplexity
from lloyd.orchestrator.input_classifier import InputClassifier, InputType
from lloyd.orchestrator.metrics import MetricsStore, TaskMetrics
from lloyd.orchestrator.parallel_executor import ParallelStoryExecutor
from lloyd.orchestrator.policy_engine import PolicyEngine, PolicyEffect
from lloyd.orchestrator.project_context import ProjectContext, ProjectDetector
from lloyd.orchestrator.router import check_all_complete, get_next_story, get_ready_stories
from lloyd.orchestrator.spec_parser import SpecParser
from lloyd.orchestrator.state import LloydState
from lloyd.orchestrator.thread_safe_state import ThreadSafeStateManager

# Use safe_box for Windows compatibility
console = Console(force_terminal=True, safe_box=True)


class LloydFlow:
    """Main orchestration flow for Lloyd."""

    def __init__(
        self,
        prd_path: str = ".lloyd/prd.json",
        progress_path: str = ".lloyd/progress.txt",
        max_parallel: int = 3,
        use_iterative_executor: bool = True,
    ) -> None:
        """Initialize the Lloyd flow.

        Args:
            prd_path: Path to PRD file.
            progress_path: Path to progress file.
            max_parallel: Maximum number of parallel workers.
            use_iterative_executor: Use TDD-based iterative executor instead of crew.
        """
        self.state = LloydState()
        self.state.max_parallel = max_parallel
        self.prd_manager = PRDManager(prd_path)
        self.progress = ProgressTracker(progress_path)
        self.thread_safe_state = ThreadSafeStateManager(prd_path)
        self.planning_crew = PlanningCrew()
        self.execution_crew = ExecutionCrew()
        self.quality_crew = QualityCrew()
        self._prd: PRD | None = None

        # Iterative TDD executor (new approach)
        self.use_iterative_executor = use_iterative_executor
        # Generate a session ID for this flow instance
        self.session_id = str(uuid.uuid4())[:8]
        # Use isolated workspace to prevent source tree pollution
        self.output_dir = get_isolated_workspace(self.session_id)
        self.iterative_executor = IterativeExecutor(
            working_dir=self.output_dir,
            session_id=self.session_id
        ) if use_iterative_executor else None

        # New components for complexity routing
        self.complexity_assessor = ComplexityAssessor()
        self.project_detector = ProjectDetector()
        self.metrics_store = MetricsStore()
        self.project_context: ProjectContext | None = None
        self.current_metrics: TaskMetrics | None = None

        # Input classification
        self.input_classifier = InputClassifier()
        self.spec_parser = SpecParser()
        self.input_type: InputType = InputType.IDEA

        # Policy engine for behavior modification
        self.policy_engine = PolicyEngine()
        self.current_policy_effect: PolicyEffect | None = None

    @property
    def prd(self) -> PRD | None:
        """Get current PRD."""
        if self._prd is None:
            self._prd = self.prd_manager.load()
        return self._prd

    def receive_idea(self, idea: str) -> None:
        """Receive a product idea or spec document to execute.

        Args:
            idea: The product idea description or spec document.
        """
        console.print(f"[bold blue]Received input:[/bold blue] {idea[:200]}{'...' if len(idea) > 200 else ''}")
        self.state.idea = idea
        self.state.status = "planning"
        self.progress.start_session(f"Working on: {idea[:100]}...")

        # Classify input type (idea vs spec document)
        input_analysis = self.input_classifier.classify(idea)
        self.input_type = input_analysis.input_type
        console.print(f"[dim]Input type: {self.input_type.value} (confidence: {input_analysis.confidence:.0%}) - {input_analysis.reason}[/dim]")

        # Detect project context
        self.project_context = self.project_detector.detect()
        console.print(f"[dim]Project: {self.project_context.language} ({', '.join(self.project_context.detected_from) or 'no markers'})[/dim]")

        # Assess complexity (skip for specs - they define their own scope)
        if self.input_type == InputType.SPEC:
            self.state.complexity = "spec"
            console.print(f"[dim]Complexity: spec document with {input_analysis.requirement_count} requirements[/dim]")
        else:
            assessment = self.complexity_assessor.assess(idea)
            self.state.complexity = assessment.complexity.value
            console.print(f"[dim]Complexity: {assessment.complexity.value} - {assessment.reasoning}[/dim]")

        # Start metrics tracking
        self.current_metrics = TaskMetrics(
            task_id=str(uuid.uuid4())[:8],
            idea=idea,
            complexity=self.state.complexity,
        )

    def create_trivial_prd(self) -> PRD:
        """Create a simple PRD for trivial tasks (skips planning crew).

        Returns:
            Created PRD with a single story.
        """
        console.print("[green]TRIVIAL task - skipping planning crew[/green]")

        # Create PRD directly without planning crew
        prd = self.prd_manager.create_new(
            project_name=f"Trivial: {self.state.idea[:40]}...",
            description=self.state.idea,
        )

        # Add single story for trivial task
        self.prd_manager.add_story(
            prd,
            title="Execute Task",
            description=self.state.idea,
            acceptance_criteria=["Task completed as requested"],
            priority=1,
        )

        self._prd = prd
        self.prd_manager.save(prd)

        self.state.prd = prd.model_dump()
        self.progress.append(f"Created trivial PRD (skipped planning)")

        if self.current_metrics:
            self.current_metrics.agents_used.append("direct_execution")

        return prd

    def create_prd_from_spec(self) -> PRD:
        """Create a PRD directly from a parsed spec document.

        Skips the planning crew since the spec already defines requirements.

        Returns:
            Created PRD with stories from spec requirements.
        """
        console.print("[green]SPEC document detected - parsing requirements directly[/green]")

        # Parse the spec document
        parsed = self.spec_parser.parse(self.state.idea)
        console.print(f"[dim]Parsed: {parsed.title} with {len(parsed.requirements)} requirements[/dim]")

        # Create PRD
        prd = self.prd_manager.create_new(
            project_name=parsed.title,
            description=parsed.description,
        )

        # Convert requirements to stories
        stories_data = self.spec_parser.requirements_to_stories(parsed)

        # Add each story to PRD
        for story_data in stories_data:
            story = Story(
                id=story_data["id"],
                title=story_data["title"],
                description=story_data["description"],
                acceptance_criteria=story_data["acceptanceCriteria"],
                priority=story_data["priority"],
                dependencies=story_data["dependencies"],
                passes=False,
                attempts=0,
                notes=f"Section: {story_data['section']}",
            )
            prd.stories.append(story)

        self._prd = prd
        self.prd_manager.save(prd)

        self.state.prd = prd.model_dump()
        self.progress.append(f"Created PRD from spec with {len(prd.stories)} stories")

        if self.current_metrics:
            self.current_metrics.agents_used.append("spec_parser")

        console.print(f"[bold cyan]Created {len(prd.stories)} stories from spec:[/bold cyan]")
        for story in prd.stories[:5]:  # Show first 5
            console.print(f"  - [{story.id}] {story.title}")
        if len(prd.stories) > 5:
            console.print(f"  ... and {len(prd.stories) - 5} more")

        return prd

    def decompose_idea(self) -> PRD:
        """Decompose the idea into a structured PRD.

        Returns:
            Created PRD with stories.
        """
        console.print("[yellow]Decomposing idea into tasks...[/yellow]")

        # Use planning crew to analyze and create PRD
        result = self.planning_crew.kickoff(inputs={"idea": self.state.idea})

        if self.current_metrics:
            self.current_metrics.agents_used.extend(["analyst", "researcher", "architect"])

        # Create PRD from planning result
        prd = self.prd_manager.create_from_planning(result)
        prd.project_name = f"Project: {self.state.idea[:50]}..."

        # Add initial stories based on planning output
        # This is simplified - in practice, you'd parse the planning output
        self.prd_manager.add_story(
            prd,
            title="Initial Implementation",
            description=f"Implement the core functionality for: {self.state.idea}",
            acceptance_criteria=[
                "Core functionality works as described",
                "Tests pass",
                "Code follows project conventions",
            ],
            priority=1,
        )

        self._prd = prd
        self.prd_manager.save(prd)

        self.state.prd = prd.model_dump()
        self.progress.append(f"Created PRD with {len(prd.stories)} stories")

        return prd

    def select_next_story(self) -> dict[str, Any] | None:
        """Select the next story to work on.

        Returns:
            Story dictionary or None if all complete.
        """
        if not self.prd:
            return None

        story = get_next_story(self.prd)

        if story is None:
            console.print("[green]All tasks complete![/green]")
            self.state.status = "complete"
            return None

        console.print(f"[cyan]Selected task:[/cyan] {story.title}")
        self.state.current_story = story.model_dump()
        self.state.status = "executing"

        return self.state.current_story

    def _build_policy_context(self, story: dict[str, Any]) -> dict[str, Any]:
        """Build context dict for policy evaluation.

        Args:
            story: Current story dict.

        Returns:
            Context dict for policy engine.
        """
        # Get story's retry count from PRD
        retry_count = 0
        if self.prd:
            story_obj = self.prd_manager.get_story_by_id(self.prd, story.get("id", ""))
            if story_obj:
                retry_count = story_obj.attempts

        # Detect categories from story description
        description = f"{story.get('title', '')} {story.get('description', '')}"
        categories = []
        category_keywords = {
            "auth": ["auth", "login", "jwt", "token", "session"],
            "database": ["database", "db", "sql", "migration"],
            "api": ["api", "endpoint", "rest", "http"],
            "testing": ["test", "pytest", "unittest"],
            "config": ["config", "env", "settings"],
            "ui": ["ui", "frontend", "component", "render"],
        }
        for cat, keywords in category_keywords.items():
            if any(kw in description.lower() for kw in keywords):
                categories.append(cat)

        # Build context
        context = {
            "description": description,
            "complexity": self.state.complexity,
            "categories": categories,
            "retry_count": retry_count,
            "user_preferences": {},  # Could be loaded from config
            "coder_success_rate": 0.7,  # Could be computed from metrics
            "project_files": [],  # Could be detected
        }

        # Add project context if available
        if self.project_context:
            context["project_language"] = self.project_context.language
            context["project_files"] = list(self.project_context.detected_from)

        return context

    def _evaluate_policies(self, story: dict[str, Any]) -> PolicyEffect:
        """Evaluate policies for the current story.

        Args:
            story: Current story dict.

        Returns:
            PolicyEffect with applicable modifications.
        """
        context = self._build_policy_context(story)
        effect = self.policy_engine.evaluate(context)
        self.current_policy_effect = effect

        # Log applied policies
        if effect.applied_policies:
            console.print(f"[dim]Applied policies: {', '.join(effect.applied_policies)}[/dim]")

        # Log warnings
        for warning in effect.warnings:
            console.print(f"[yellow]Policy warning:[/yellow] {warning}")

        # Log injected steps
        for step in effect.inject_steps:
            self.progress.append(f"Policy injected step: {step}")

        return effect

    def execute_story(self) -> Any:
        """Execute the current story.

        Returns:
            Execution result.
        """
        if not self.state.current_story:
            return None

        story = self.state.current_story
        console.print(f"[yellow]Executing:[/yellow] {story['title']}")

        # Use iterative TDD executor if enabled
        if self.use_iterative_executor and self.iterative_executor:
            console.print("[dim]Using iterative TDD executor[/dim]")
            result = self.iterative_executor.execute_story(story)

            # Check if passed and update story directly
            if result.get("passes"):
                if self.prd:
                    story_obj = self.prd_manager.get_story_by_id(self.prd, story["id"])
                    if story_obj:
                        story_obj.passes = True
                        story_obj.attempts += 1
                        story_obj.notes += f"\nPassed via iterative executor ({result.get('passed_steps')}/{result.get('total_steps')} steps)"
                        self.prd_manager.save(self.prd)
        else:
            # Use traditional crew-based execution
            result = self.execution_crew.kickoff(
                inputs={
                    "story": story,
                    "prd": self.state.prd,
                    "progress": self.progress.read(),
                }
            )

        self.progress.append(f"Executed: {story['title']}")
        return result

    def verify_story(self, execution_result: Any) -> bool:
        """Verify the story meets acceptance criteria.

        Args:
            execution_result: Result from execution.

        Returns:
            True if story passes verification.
        """
        if not self.state.current_story:
            return False

        story = self.state.current_story
        console.print(f"[yellow]Verifying:[/yellow] {story['title']}")
        self.state.status = "testing"

        # If using iterative executor, result already contains pass/fail from pytest
        if self.use_iterative_executor and isinstance(execution_result, dict):
            passes = execution_result.get("passes", False)
            console.print(f"[dim]Iterative executor result: {execution_result.get('status')}[/dim]")

            # Update story in PRD (may already be updated by execute_story)
            if self.prd:
                story_obj = self.prd_manager.get_story_by_id(self.prd, story["id"])
                if story_obj and not story_obj.passes:  # Only update if not already passed
                    story_obj.passes = passes
                    story_obj.attempts += 1
                    if passes:
                        story_obj.notes += f"\nVerified via pytest on attempt {story_obj.attempts}"
                    else:
                        failures = execution_result.get("failures", [])
                        failure_info = "; ".join(f.get("description", "unknown") for f in failures[:3])
                        story_obj.notes += f"\nFailed: {failure_info}"
                    self.prd_manager.save(self.prd)

            self.progress.log_iteration(
                self.state.iteration,
                story["title"],
                "PASSED" if passes else "FAILED",
            )
            return passes

        # Traditional crew-based verification
        result = self.quality_crew.kickoff(
            inputs={
                "story": story,
                "execution_result": execution_result,
                "acceptance_criteria": story.get("acceptanceCriteria", []),
            }
        )

        passes = result.get("passes", False)

        # Update story in PRD
        if self.prd:
            story_obj = self.prd_manager.get_story_by_id(self.prd, story["id"])
            if story_obj:
                story_obj.passes = passes
                story_obj.attempts += 1
                if passes:
                    story_obj.notes += f"\nPassed on attempt {story_obj.attempts}"
                else:
                    story_obj.notes += f"\nFailed on attempt {story_obj.attempts}"
                self.prd_manager.save(self.prd)

        self.progress.log_iteration(
            self.state.iteration,
            story["title"],
            "PASSED" if passes else "FAILED",
        )

        return passes

    def run_iteration(self) -> bool:
        """Run a single iteration of the workflow.

        Returns:
            True if should continue, False if complete or blocked.
        """
        self.state.iteration += 1
        console.print(f"\n[bold]Iteration {self.state.iteration}[/bold]")

        # Select next story
        story = self.select_next_story()
        if not story:
            return False

        # Evaluate policies before execution
        policy_effect = self._evaluate_policies(story)

        # Execute story (policy effects can modify behavior)
        execution_result = self.execute_story()

        # Verify story (may skip if policy says so)
        if policy_effect and "reviewer" in policy_effect.skip_agents:
            console.print("[dim]Skipping verification per policy[/dim]")
            passes = True
            # Still update story in PRD
            if self.prd:
                story_obj = self.prd_manager.get_story_by_id(self.prd, story["id"])
                if story_obj:
                    story_obj.passes = True
                    story_obj.attempts += 1
                    story_obj.notes += f"\nSkipped verification per policy"
                    self.prd_manager.save(self.prd)
        else:
            passes = self.verify_story(execution_result)

        if passes:
            console.print(f"[green]Task completed:[/green] {story['title']}")
        else:
            console.print(f"[red]Task failed:[/red] {story['title']}")

        # Check if we've hit max iterations
        if self.state.iteration >= self.state.max_iterations:
            console.print("[red]Max iterations reached![/red]")
            self.state.status = "blocked"
            return False

        # Check if all complete
        if self.prd and check_all_complete(self.prd):
            self.state.status = "complete"
            return False

        return True

    def _execute_story_for_parallel(self, story: Story) -> Any:
        """Execute a single story (for parallel execution).

        Args:
            story: Story to execute.

        Returns:
            Execution result.
        """
        console.print(f"[yellow]Executing:[/yellow] {story.title}")

        # Use iterative TDD executor if enabled
        if self.use_iterative_executor and self.iterative_executor:
            console.print("[dim]Using iterative TDD executor (parallel)[/dim]")
            result = self.iterative_executor.execute_story(story.model_dump())

            # Update story if passed
            if result.get("passes"):
                story.passes = True
                story.attempts += 1
                story.notes += f"\nPassed via iterative executor ({result.get('passed_steps')}/{result.get('total_steps')} steps)"
                if self.prd:
                    self.prd_manager.save(self.prd)
        else:
            # Use traditional crew-based execution
            result = self.execution_crew.kickoff(
                inputs={
                    "story": story.model_dump(),
                    "prd": self.state.prd,
                    "progress": self.progress.read(),
                }
            )

        self.progress.append(f"Executed: {story.title}")
        return result

    def _verify_story_for_parallel(self, story: Story, execution_result: Any) -> bool:
        """Verify a single story (for parallel execution).

        Args:
            story: Story to verify.
            execution_result: Result from execution.

        Returns:
            True if story passes verification.
        """
        console.print(f"[yellow]Verifying:[/yellow] {story.title}")

        # If using iterative executor, result already contains pass/fail from pytest
        if self.use_iterative_executor and isinstance(execution_result, dict):
            passes = execution_result.get("passes", False)
            console.print(f"[dim]Iterative executor result: {execution_result.get('status')}[/dim]")
        else:
            # Use traditional crew-based verification
            result = self.quality_crew.kickoff(
                inputs={
                    "story": story.model_dump(),
                    "execution_result": execution_result,
                    "acceptance_criteria": story.acceptance_criteria,
                }
            )
            passes = result.get("passes", False)

        self.progress.log_iteration(
            self.state.iteration,
            story.title,
            "PASSED" if passes else "FAILED",
        )

        return passes

    def run_parallel_iteration(self) -> bool:
        """Run a single parallel iteration of the workflow.

        Executes multiple stories concurrently up to max_parallel.

        Returns:
            True if should continue, False if complete or blocked.
        """
        self.state.iteration += 1
        console.print(f"\n[bold]Parallel Iteration {self.state.iteration}[/bold]")

        # Reload PRD to get fresh state
        self._prd = self.prd_manager.load()
        if not self.prd:
            console.print("[red]No PRD found[/red]")
            return False

        # Get ready stories
        ready_stories = get_ready_stories(self.prd, self.state.max_parallel)

        if not ready_stories:
            # Check if complete
            if check_all_complete(self.prd):
                console.print("[green]All tasks complete![/green]")
                self.state.status = "complete"
                return False

            console.print("[yellow]No stories ready to execute[/yellow]")
            self.state.status = "blocked"
            return False

        console.print(
            f"[cyan]Found {len(ready_stories)} stories ready for parallel execution[/cyan]"
        )
        self.state.current_stories = [s.model_dump() for s in ready_stories]

        # Execute stories in parallel
        with ParallelStoryExecutor(
            self.thread_safe_state, max_workers=self.state.max_parallel
        ) as executor:
            results = executor.run_parallel_batch(
                ready_stories,
                self._execute_story_for_parallel,
                self._verify_story_for_parallel,
            )

        # Log results
        passed_count = sum(1 for r in results if r.passed)
        console.print(
            f"[bold]Batch result:[/bold] {passed_count}/{len(results)} stories passed"
        )

        # Reload PRD after parallel execution
        self._prd = self.prd_manager.load()

        # Check if we've hit max iterations
        if self.state.iteration >= self.state.max_iterations:
            console.print("[red]Max iterations reached![/red]")
            self.state.status = "blocked"
            return False

        # Check if all complete
        if self.prd and check_all_complete(self.prd):
            self.state.status = "complete"
            return False

        # Check if blocked
        if self.thread_safe_state.is_blocked():
            self.state.status = "blocked"
            return False

        return True

    def _run_sequential_loop(self) -> None:
        """Run the sequential execution loop."""
        while self.state.can_continue():
            should_continue = self.run_iteration()
            if not should_continue:
                break

    def _run_parallel_loop(self) -> None:
        """Run the parallel execution loop."""
        while self.state.can_continue():
            should_continue = self.run_parallel_iteration()
            if not should_continue:
                break

    def run(self, parallel: bool | None = None) -> LloydState:
        """Run the full Lloyd workflow.

        Args:
            parallel: Whether to run in parallel mode. If None, uses state.parallel_mode.

        Returns:
            Final state.
        """
        use_parallel = parallel if parallel is not None else self.state.parallel_mode

        if use_parallel:
            console.print("[bold blue]Starting Lloyd workflow (parallel mode)...[/bold blue]")
        else:
            console.print("[bold blue]Starting Lloyd workflow (sequential mode)...[/bold blue]")

        # Phase 1: Planning (route based on input type)
        if self.state.status == "planning" or not self.prd:
            if self.input_type == InputType.SPEC:
                # Spec document - parse directly, skip planning crew
                self.create_prd_from_spec()
            elif self.state.complexity in (TaskComplexity.TRIVIAL.value, TaskComplexity.SIMPLE.value):
                # Trivial/Simple idea - skip planning crew (direct to execution)
                self.create_trivial_prd()
            else:
                # Regular idea - use planning crew
                self.decompose_idea()

        # Phase 2: Execution loop
        if use_parallel:
            self._run_parallel_loop()
        else:
            self._run_sequential_loop()

        # Final status and metrics
        if self.state.is_complete():
            console.print("[bold green]All tasks complete! Project finished.[/bold green]")
            if self.current_metrics:
                self.current_metrics.iterations = self.state.iteration
                self.current_metrics.complete("success")
                self.metrics_store.save(self.current_metrics)
                console.print(f"[dim]Duration: {self.current_metrics.duration_human}[/dim]")
        elif self.state.is_blocked():
            console.print("[bold red]Workflow blocked. Manual intervention needed.[/bold red]")
            if self.current_metrics:
                self.current_metrics.iterations = self.state.iteration
                self.current_metrics.complete("failure")
                self.metrics_store.save(self.current_metrics)
                console.print(f"[dim]Duration: {self.current_metrics.duration_human}[/dim]")

        return self.state


def run_lloyd(
    idea: str,
    max_iterations: int = 50,
    max_parallel: int = 3,
    parallel: bool = True,
    use_iterative_executor: bool = True,
) -> LloydState:
    """Run Lloyd with a product idea.

    Args:
        idea: Product idea to execute.
        max_iterations: Maximum iterations before stopping.
        max_parallel: Maximum number of parallel workers.
        parallel: Whether to run in parallel mode.
        use_iterative_executor: Use TDD-based iterative executor (recommended).

    Returns:
        Final Lloyd state.
    """
    flow = LloydFlow(max_parallel=max_parallel, use_iterative_executor=use_iterative_executor)
    flow.state.max_iterations = max_iterations
    flow.state.parallel_mode = parallel
    flow.receive_idea(idea)
    return flow.run(parallel=parallel)
