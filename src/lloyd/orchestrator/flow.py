"""Main Lloyd orchestration flow."""

from typing import Any

from rich.console import Console

from lloyd.crews.execution import ExecutionCrew
from lloyd.crews.planning import PlanningCrew
from lloyd.crews.quality import QualityCrew
from lloyd.memory.prd_manager import PRD, PRDManager, Story
from lloyd.memory.progress import ProgressTracker
from lloyd.orchestrator.parallel_executor import ParallelStoryExecutor
from lloyd.orchestrator.router import check_all_complete, get_next_story, get_ready_stories
from lloyd.orchestrator.state import LloydState
from lloyd.orchestrator.thread_safe_state import ThreadSafeStateManager

console = Console()


class LloydFlow:
    """Main orchestration flow for Lloyd."""

    def __init__(
        self,
        prd_path: str = ".lloyd/prd.json",
        progress_path: str = ".lloyd/progress.txt",
        max_parallel: int = 3,
    ) -> None:
        """Initialize the Lloyd flow.

        Args:
            prd_path: Path to PRD file.
            progress_path: Path to progress file.
            max_parallel: Maximum number of parallel workers.
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

    @property
    def prd(self) -> PRD | None:
        """Get current PRD."""
        if self._prd is None:
            self._prd = self.prd_manager.load()
        return self._prd

    def receive_idea(self, idea: str) -> None:
        """Receive a product idea to execute.

        Args:
            idea: The product idea description.
        """
        console.print(f"[bold blue]Received idea:[/bold blue] {idea}")
        self.state.idea = idea
        self.state.status = "planning"
        self.progress.start_session(f"Working on: {idea[:100]}...")

    def decompose_idea(self) -> PRD:
        """Decompose the idea into a structured PRD.

        Returns:
            Created PRD with stories.
        """
        console.print("[yellow]Decomposing idea into tasks...[/yellow]")

        # Use planning crew to analyze and create PRD
        result = self.planning_crew.kickoff(inputs={"idea": self.state.idea})

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

    def execute_story(self) -> Any:
        """Execute the current story.

        Returns:
            Execution result.
        """
        if not self.state.current_story:
            return None

        story = self.state.current_story
        console.print(f"[yellow]Executing:[/yellow] {story['title']}")

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

        # Execute story
        execution_result = self.execute_story()

        # Verify story
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

        # Phase 1: Planning
        if self.state.status == "planning" or not self.prd:
            self.decompose_idea()

        # Phase 2: Execution loop
        if use_parallel:
            self._run_parallel_loop()
        else:
            self._run_sequential_loop()

        # Final status
        if self.state.is_complete():
            console.print("[bold green]All tasks complete! Project finished.[/bold green]")
        elif self.state.is_blocked():
            console.print("[bold red]Workflow blocked. Manual intervention needed.[/bold red]")

        return self.state


def run_lloyd(
    idea: str,
    max_iterations: int = 50,
    max_parallel: int = 3,
    parallel: bool = True,
) -> LloydState:
    """Run Lloyd with a product idea.

    Args:
        idea: Product idea to execute.
        max_iterations: Maximum iterations before stopping.
        max_parallel: Maximum number of parallel workers.
        parallel: Whether to run in parallel mode.

    Returns:
        Final Lloyd state.
    """
    flow = LloydFlow(max_parallel=max_parallel)
    flow.state.max_iterations = max_iterations
    flow.state.parallel_mode = parallel
    flow.receive_idea(idea)
    return flow.run(parallel=parallel)
