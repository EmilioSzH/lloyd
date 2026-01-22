"""Parallel story execution using ThreadPoolExecutor."""

import uuid
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable

from rich.console import Console

from lloyd.memory.prd_manager import Story
from lloyd.orchestrator.thread_safe_state import ThreadSafeStateManager

console = Console()


@dataclass
class StoryResult:
    """Result of executing a single story."""

    story_id: str
    story_title: str
    passed: bool
    execution_result: Any
    error: str | None = None
    worker_id: str = ""


class ParallelStoryExecutor:
    """Execute multiple stories in parallel using ThreadPoolExecutor.

    This executor manages concurrent story execution while ensuring thread-safe
    access to shared PRD state through file locking.
    """

    def __init__(
        self,
        state_manager: ThreadSafeStateManager,
        max_workers: int = 3,
    ) -> None:
        """Initialize the parallel executor.

        Args:
            state_manager: Thread-safe state manager for PRD operations.
            max_workers: Maximum number of parallel workers.
        """
        self.state_manager = state_manager
        self.max_workers = max_workers
        self._executor: ThreadPoolExecutor | None = None

    def __enter__(self) -> "ParallelStoryExecutor":
        """Enter context manager."""
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

    def execute_story(
        self,
        story: Story,
        execute_fn: Callable[[Story], Any],
        verify_fn: Callable[[Story, Any], bool],
        worker_id: str,
    ) -> StoryResult:
        """Execute a single story with the provided functions.

        Args:
            story: Story to execute.
            execute_fn: Function to execute the story implementation.
            verify_fn: Function to verify the story passes acceptance criteria.
            worker_id: Unique identifier for this worker.

        Returns:
            StoryResult with execution outcome.
        """
        try:
            console.print(
                f"[cyan]Worker {worker_id}:[/cyan] Starting story '{story.title}'"
            )

            # Try to claim the story
            claimed = self.state_manager.claim_story(story.id, worker_id)
            if claimed is None:
                console.print(
                    f"[yellow]Worker {worker_id}:[/yellow] "
                    f"Story '{story.title}' already claimed, skipping"
                )
                return StoryResult(
                    story_id=story.id,
                    story_title=story.title,
                    passed=False,
                    execution_result=None,
                    error="Story already claimed by another worker",
                    worker_id=worker_id,
                )

            # Execute the story
            console.print(
                f"[yellow]Worker {worker_id}:[/yellow] Executing '{story.title}'"
            )
            execution_result = execute_fn(story)

            # Verify the story
            console.print(
                f"[yellow]Worker {worker_id}:[/yellow] Verifying '{story.title}'"
            )
            passed = verify_fn(story, execution_result)

            # Release the story with result
            notes = f"Executed by worker {worker_id}"
            self.state_manager.release_story(story.id, passed, notes)

            if passed:
                console.print(
                    f"[green]Worker {worker_id}:[/green] "
                    f"Story '{story.title}' PASSED"
                )
            else:
                console.print(
                    f"[red]Worker {worker_id}:[/red] "
                    f"Story '{story.title}' FAILED"
                )

            return StoryResult(
                story_id=story.id,
                story_title=story.title,
                passed=passed,
                execution_result=execution_result,
                worker_id=worker_id,
            )

        except Exception as e:
            console.print(
                f"[red]Worker {worker_id}:[/red] "
                f"Error executing story '{story.title}': {e}"
            )
            # Release the story as failed
            self.state_manager.release_story(
                story.id, False, f"Error: {e}"
            )
            return StoryResult(
                story_id=story.id,
                story_title=story.title,
                passed=False,
                execution_result=None,
                error=str(e),
                worker_id=worker_id,
            )

    def run_parallel_batch(
        self,
        stories: list[Story],
        execute_fn: Callable[[Story], Any],
        verify_fn: Callable[[Story, Any], bool],
    ) -> list[StoryResult]:
        """Execute a batch of stories in parallel.

        Args:
            stories: List of stories to execute.
            execute_fn: Function to execute story implementation.
            verify_fn: Function to verify story passes acceptance criteria.

        Returns:
            List of StoryResult for each story.
        """
        if not stories:
            return []

        if self._executor is None:
            raise RuntimeError(
                "Executor not initialized. Use 'with ParallelStoryExecutor(...) as executor:'"
            )

        console.print(
            f"\n[bold blue]Starting parallel batch with {len(stories)} stories "
            f"(max {self.max_workers} workers)[/bold blue]"
        )

        results: list[StoryResult] = []
        futures: dict[Future[StoryResult], Story] = {}

        for i, story in enumerate(stories):
            worker_id = f"W{i+1}-{uuid.uuid4().hex[:4]}"
            future = self._executor.submit(
                self.execute_story,
                story,
                execute_fn,
                verify_fn,
                worker_id,
            )
            futures[future] = story

        # Collect results as they complete
        for future in as_completed(futures):
            story = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                console.print(f"[red]Error in future for story {story.id}: {e}[/red]")
                results.append(
                    StoryResult(
                        story_id=story.id,
                        story_title=story.title,
                        passed=False,
                        execution_result=None,
                        error=str(e),
                    )
                )

        # Summary
        passed_count = sum(1 for r in results if r.passed)
        console.print(
            f"\n[bold]Batch complete:[/bold] {passed_count}/{len(results)} stories passed"
        )

        return results

    def run_until_complete(
        self,
        execute_fn: Callable[[Story], Any],
        verify_fn: Callable[[Story, Any], bool],
        max_iterations: int = 50,
    ) -> dict[str, Any]:
        """Run parallel execution until all stories complete or blocked.

        Args:
            execute_fn: Function to execute story implementation.
            verify_fn: Function to verify story passes acceptance criteria.
            max_iterations: Maximum number of batch iterations.

        Returns:
            Dictionary with final execution status.
        """
        if self._executor is None:
            raise RuntimeError(
                "Executor not initialized. Use 'with ParallelStoryExecutor(...) as executor:'"
            )

        iteration = 0
        total_passed = 0
        total_failed = 0

        while iteration < max_iterations:
            iteration += 1

            # Check if all complete
            if self.state_manager.is_all_complete():
                console.print("[bold green]All stories complete![/bold green]")
                break

            # Check if blocked
            if self.state_manager.is_blocked():
                console.print("[bold red]Execution blocked - all remaining stories blocked[/bold red]")
                break

            # Get ready stories
            ready_stories = self.state_manager.get_ready_stories(self.max_workers)
            if not ready_stories:
                console.print("[yellow]No stories ready to execute[/yellow]")
                # Reset failed stories and try again
                reset_count = self.state_manager.reset_failed_stories()
                if reset_count > 0:
                    console.print(f"[cyan]Reset {reset_count} failed stories[/cyan]")
                    continue
                else:
                    console.print("[red]No stories to reset, execution blocked[/red]")
                    break

            console.print(f"\n[bold]Iteration {iteration}[/bold]")

            # Run batch
            results = self.run_parallel_batch(ready_stories, execute_fn, verify_fn)

            # Count results
            for result in results:
                if result.passed:
                    total_passed += 1
                else:
                    total_failed += 1

        # Final status
        status = self.state_manager.get_status_summary()

        return {
            "iterations": iteration,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "final_status": status,
            "complete": self.state_manager.is_all_complete(),
            "blocked": self.state_manager.is_blocked(),
        }
