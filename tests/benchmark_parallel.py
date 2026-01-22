"""Benchmark parallel vs sequential execution speed."""

import time
from pathlib import Path
from typing import Any

from lloyd.memory.prd_manager import PRDManager, Story
from lloyd.orchestrator.parallel_executor import ParallelStoryExecutor
from lloyd.orchestrator.thread_safe_state import ThreadSafeStateManager


def simulate_work(duration: float = 0.5) -> dict[str, Any]:
    """Simulate work that takes some time."""
    time.sleep(duration)
    return {"done": True}


def run_sequential(stories: list[Story], work_duration: float) -> float:
    """Run stories sequentially and return total time."""
    start = time.perf_counter()

    for story in stories:
        # Simulate execute
        simulate_work(work_duration)
        # Simulate verify
        simulate_work(work_duration * 0.5)

    return time.perf_counter() - start


def run_parallel(
    state_manager: ThreadSafeStateManager,
    stories: list[Story],
    work_duration: float,
    max_workers: int,
) -> float:
    """Run stories in parallel and return total time."""

    def mock_execute(story: Story) -> dict[str, Any]:
        return simulate_work(work_duration)

    def mock_verify(story: Story, result: Any) -> bool:
        simulate_work(work_duration * 0.5)
        return True

    start = time.perf_counter()

    with ParallelStoryExecutor(state_manager, max_workers=max_workers) as executor:
        executor.run_parallel_batch(stories, mock_execute, mock_verify)

    return time.perf_counter() - start


def main() -> None:
    """Run the benchmark."""
    print("=" * 60)
    print("Lloyd Parallel Execution Benchmark")
    print("=" * 60)

    # Test parameters
    num_stories_list = [3, 6, 9]
    work_duration = 0.3  # seconds per task
    max_workers = 3

    for num_stories in num_stories_list:
        print(f"\n{'-' * 60}")
        print(f"Test: {num_stories} independent stories")
        print(f"Work duration: {work_duration}s execute + {work_duration * 0.5}s verify per story")
        print(f"Max parallel workers: {max_workers}")
        print("-" * 60)

        # Create temp PRD
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            prd_path = Path(tmpdir) / ".lloyd" / "prd.json"
            prd_manager = PRDManager(prd_path)
            state_manager = ThreadSafeStateManager(prd_path)

            # Create stories
            prd = prd_manager.create_new("Benchmark Test")
            for i in range(num_stories):
                prd_manager.add_story(
                    prd,
                    f"Story {i+1}",
                    f"Description {i+1}",
                    [f"AC{i+1}"],
                    priority=1,
                )
            prd_manager.save(prd)

            stories = prd.stories

            # Run sequential
            seq_time = run_sequential(stories, work_duration)
            print(f"\nSequential execution: {seq_time:.2f}s")

            # Reset PRD for parallel run
            prd = prd_manager.create_new("Benchmark Test")
            for i in range(num_stories):
                prd_manager.add_story(
                    prd,
                    f"Story {i+1}",
                    f"Description {i+1}",
                    [f"AC{i+1}"],
                    priority=1,
                )
            prd_manager.save(prd)
            stories = prd.stories

            # Run parallel
            par_time = run_parallel(state_manager, stories, work_duration, max_workers)
            print(f"Parallel execution:   {par_time:.2f}s")

            # Calculate speedup
            speedup = seq_time / par_time
            time_saved = seq_time - par_time
            print(f"\nSpeedup: {speedup:.2f}x faster")
            print(f"Time saved: {time_saved:.2f}s ({(time_saved/seq_time)*100:.1f}%)")

            # Theoretical max speedup
            effective_workers = min(max_workers, num_stories)
            theoretical_max = num_stories / effective_workers
            efficiency = (speedup / theoretical_max) * 100
            print(f"Theoretical max speedup: {theoretical_max:.2f}x")
            print(f"Parallel efficiency: {efficiency:.1f}%")

    print(f"\n{'=' * 60}")
    print("Benchmark Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
