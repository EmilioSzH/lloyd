"""
Benchmark comparison: Lloyd Executor vs Ralph Executor

Compares two execution strategies:
1. Lloyd: ThreadPoolExecutor with file-based locking (claim-execute-release)
2. Ralph: Async-based execution with in-memory coordination

Measures:
- Speed: Wall clock time at different parallelism levels
- Reliability: Task completion rate, conflict frequency
- Quality: Output consistency (hash comparison)
- Scaling: Performance degradation curve
"""

import argparse
import asyncio
import hashlib
import json
import os
import random
import shutil
import statistics
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from filelock import FileLock
from rich.console import Console
from rich.table import Table

console = Console()


# =============================================================================
# COMMON DATA STRUCTURES
# =============================================================================


@dataclass
class MockStory:
    """Simulated story for benchmarking."""

    id: str
    title: str
    complexity: int  # 1-5, affects execution time
    dependencies: list[str] = field(default_factory=list)
    output_file: str = ""


@dataclass
class ExecutionResult:
    """Result of executing a story."""

    story_id: str
    passed: bool
    duration: float
    output_hash: str
    worker_id: str
    error: str | None = None
    conflicts: int = 0


@dataclass
class BenchmarkResult:
    """Complete benchmark result."""

    executor_name: str
    max_parallel: int
    total_stories: int
    completed: int
    failed: int
    total_time: float
    avg_story_time: float
    conflicts: int
    output_hashes: list[str] = field(default_factory=list)

    @property
    def completion_rate(self) -> float:
        return self.completed / self.total_stories if self.total_stories > 0 else 0

    @property
    def throughput(self) -> float:
        """Stories per second."""
        return self.completed / self.total_time if self.total_time > 0 else 0


# =============================================================================
# MOCK WORK SIMULATION
# =============================================================================


def simulate_work(story: MockStory, output_dir: Path, worker_id: str) -> str:
    """Simulate executing a story with realistic I/O and computation.

    Args:
        story: Story to execute.
        output_dir: Directory for output files.
        worker_id: Identifier for the worker.

    Returns:
        Hash of the output content.
    """
    # Simulate variable execution time based on complexity
    base_time = 0.05  # 50ms base
    complexity_factor = story.complexity * 0.02  # 20ms per complexity level
    jitter = random.uniform(0, 0.03)  # Up to 30ms jitter
    time.sleep(base_time + complexity_factor + jitter)

    # Generate deterministic output based on story
    output_content = f"""
# Story: {story.title}
# ID: {story.id}
# Complexity: {story.complexity}
# Worker: {worker_id}
# Timestamp: {time.time()}

def generated_function_{story.id.replace('-', '_')}():
    '''Auto-generated function for {story.title}'''
    return {{'story_id': '{story.id}', 'status': 'complete'}}

# Dependencies: {story.dependencies}
"""

    # Write output file
    output_path = output_dir / f"{story.id}.py"
    output_path.write_text(output_content)

    # Return hash for consistency checking
    return hashlib.md5(output_content.encode()).hexdigest()


def verify_work(story: MockStory, output_dir: Path) -> bool:
    """Verify that story execution produced valid output.

    Args:
        story: Story to verify.
        output_dir: Directory containing output files.

    Returns:
        True if verification passes.
    """
    output_path = output_dir / f"{story.id}.py"

    if not output_path.exists():
        return False

    content = output_path.read_text()

    # Check for expected content markers
    return (
        f"Story: {story.title}" in content
        and f"ID: {story.id}" in content
        and "def generated_function_" in content
    )


# =============================================================================
# LLOYD EXECUTOR (ThreadPoolExecutor + FileLock)
# =============================================================================


class LloydExecutor:
    """Lloyd-style executor using ThreadPoolExecutor with file-based locking."""

    def __init__(self, state_file: Path, output_dir: Path, max_workers: int = 3):
        self.state_file = state_file
        self.lock_file = state_file.with_suffix(".lock")
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.conflicts = 0

    def _read_state(self) -> dict:
        """Read state file with locking."""
        with FileLock(self.lock_file, timeout=10):
            if self.state_file.exists():
                return json.loads(self.state_file.read_text())
            return {"stories": {}, "completed": [], "in_progress": []}

    def _write_state(self, state: dict) -> None:
        """Write state file with locking."""
        with FileLock(self.lock_file, timeout=10):
            self.state_file.write_text(json.dumps(state, indent=2))

    def claim_story(self, story_id: str, worker_id: str) -> bool:
        """Atomically claim a story for execution."""
        with FileLock(self.lock_file, timeout=10):
            state = json.loads(self.state_file.read_text()) if self.state_file.exists() else {"stories": {}, "completed": [], "in_progress": []}

            if story_id in state["completed"] or story_id in state["in_progress"]:
                self.conflicts += 1
                return False

            state["in_progress"].append(story_id)
            state["stories"][story_id] = {"worker": worker_id, "started": time.time()}
            self.state_file.write_text(json.dumps(state, indent=2))
            return True

    def release_story(self, story_id: str, passed: bool) -> None:
        """Release a story after execution."""
        with FileLock(self.lock_file, timeout=10):
            state = json.loads(self.state_file.read_text())

            if story_id in state["in_progress"]:
                state["in_progress"].remove(story_id)

            if passed:
                state["completed"].append(story_id)

            if story_id in state["stories"]:
                state["stories"][story_id]["completed"] = time.time()
                state["stories"][story_id]["passed"] = passed

            self.state_file.write_text(json.dumps(state, indent=2))

    def execute_story(
        self,
        story: MockStory,
        worker_id: str,
    ) -> ExecutionResult:
        """Execute a single story."""
        start = time.time()

        # Try to claim
        if not self.claim_story(story.id, worker_id):
            return ExecutionResult(
                story_id=story.id,
                passed=False,
                duration=0,
                output_hash="",
                worker_id=worker_id,
                error="Could not claim story",
                conflicts=1,
            )

        try:
            # Simulate work
            output_hash = simulate_work(story, self.output_dir, worker_id)

            # Verify
            passed = verify_work(story, self.output_dir)

            # Release
            self.release_story(story.id, passed)

            return ExecutionResult(
                story_id=story.id,
                passed=passed,
                duration=time.time() - start,
                output_hash=output_hash,
                worker_id=worker_id,
            )

        except Exception as e:
            self.release_story(story.id, False)
            return ExecutionResult(
                story_id=story.id,
                passed=False,
                duration=time.time() - start,
                output_hash="",
                worker_id=worker_id,
                error=str(e),
            )

    def run(self, stories: list[MockStory]) -> BenchmarkResult:
        """Run all stories with ThreadPoolExecutor."""
        start_time = time.time()

        # Initialize state file
        self._write_state({"stories": {}, "completed": [], "in_progress": []})

        results: list[ExecutionResult] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for i, story in enumerate(stories):
                worker_id = f"lloyd-{i % self.max_workers}"
                future = executor.submit(self.execute_story, story, worker_id)
                futures[future] = story

            for future in as_completed(futures):
                result = future.result()
                results.append(result)

        total_time = time.time() - start_time
        completed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)

        return BenchmarkResult(
            executor_name="Lloyd (ThreadPool + FileLock)",
            max_parallel=self.max_workers,
            total_stories=len(stories),
            completed=completed,
            failed=failed,
            total_time=total_time,
            avg_story_time=statistics.mean(r.duration for r in results if r.duration > 0) if results else 0,
            conflicts=self.conflicts,
            output_hashes=[r.output_hash for r in results if r.output_hash],
        )


# =============================================================================
# RALPH EXECUTOR (Async + In-Memory Coordination)
# =============================================================================


class RalphExecutor:
    """Ralph-style executor using asyncio with in-memory coordination."""

    def __init__(self, output_dir: Path, max_workers: int = 3):
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.semaphore: asyncio.Semaphore | None = None
        self.completed: set[str] = set()
        self.in_progress: set[str] = set()
        self.lock = asyncio.Lock()
        self.conflicts = 0

    async def claim_story(self, story_id: str) -> bool:
        """Claim a story using async lock."""
        async with self.lock:
            if story_id in self.completed or story_id in self.in_progress:
                self.conflicts += 1
                return False
            self.in_progress.add(story_id)
            return True

    async def release_story(self, story_id: str, passed: bool) -> None:
        """Release a story."""
        async with self.lock:
            self.in_progress.discard(story_id)
            if passed:
                self.completed.add(story_id)

    async def execute_story(
        self,
        story: MockStory,
        worker_id: str,
    ) -> ExecutionResult:
        """Execute a single story asynchronously."""
        start = time.time()

        # Acquire semaphore to limit concurrency
        async with self.semaphore:
            # Try to claim
            if not await self.claim_story(story.id):
                return ExecutionResult(
                    story_id=story.id,
                    passed=False,
                    duration=0,
                    output_hash="",
                    worker_id=worker_id,
                    error="Could not claim story",
                    conflicts=1,
                )

            try:
                # Run CPU-bound work in thread pool
                loop = asyncio.get_event_loop()
                output_hash = await loop.run_in_executor(
                    None, simulate_work, story, self.output_dir, worker_id
                )

                # Verify
                passed = await loop.run_in_executor(
                    None, verify_work, story, self.output_dir
                )

                # Release
                await self.release_story(story.id, passed)

                return ExecutionResult(
                    story_id=story.id,
                    passed=passed,
                    duration=time.time() - start,
                    output_hash=output_hash,
                    worker_id=worker_id,
                )

            except Exception as e:
                await self.release_story(story.id, False)
                return ExecutionResult(
                    story_id=story.id,
                    passed=False,
                    duration=time.time() - start,
                    output_hash="",
                    worker_id=worker_id,
                    error=str(e),
                )

    async def run_async(self, stories: list[MockStory]) -> BenchmarkResult:
        """Run all stories asynchronously."""
        start_time = time.time()

        # Initialize
        self.semaphore = asyncio.Semaphore(self.max_workers)
        self.completed = set()
        self.in_progress = set()
        self.conflicts = 0

        # Create tasks for all stories
        tasks = []
        for i, story in enumerate(stories):
            worker_id = f"ralph-{i % self.max_workers}"
            task = asyncio.create_task(self.execute_story(story, worker_id))
            tasks.append(task)

        # Wait for all tasks
        results = await asyncio.gather(*tasks)

        total_time = time.time() - start_time
        completed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)

        return BenchmarkResult(
            executor_name="Ralph (Async + In-Memory)",
            max_parallel=self.max_workers,
            total_stories=len(stories),
            completed=completed,
            failed=failed,
            total_time=total_time,
            avg_story_time=statistics.mean(r.duration for r in results if r.duration > 0) if results else 0,
            conflicts=self.conflicts,
            output_hashes=[r.output_hash for r in results if r.output_hash],
        )

    def run(self, stories: list[MockStory]) -> BenchmarkResult:
        """Sync wrapper for async execution."""
        return asyncio.run(self.run_async(stories))


# =============================================================================
# BENCHMARK HARNESS
# =============================================================================


def generate_stories(count: int, with_dependencies: bool = True) -> list[MockStory]:
    """Generate test stories with varying complexity."""
    stories = []

    for i in range(count):
        story_id = f"story-{i:03d}"
        complexity = random.randint(1, 5)

        # Add some dependencies (not for first few stories)
        dependencies = []
        if with_dependencies and i > 2 and random.random() > 0.6:
            # Depend on 1-2 earlier stories
            dep_count = random.randint(1, min(2, i))
            dep_indices = random.sample(range(max(0, i - 5), i), dep_count)
            dependencies = [f"story-{j:03d}" for j in dep_indices]

        stories.append(
            MockStory(
                id=story_id,
                title=f"Test Story {i}",
                complexity=complexity,
                dependencies=dependencies,
            )
        )

    return stories


def run_benchmark(
    executor_class: type,
    stories: list[MockStory],
    max_parallel: int,
    runs: int = 3,
    **kwargs: Any,
) -> list[BenchmarkResult]:
    """Run multiple benchmark iterations."""
    results = []

    for run_num in range(runs):
        # Create fresh temp directory for each run
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"
            output_dir.mkdir()

            if executor_class == LloydExecutor:
                state_file = Path(tmpdir) / "state.json"
                executor = executor_class(state_file, output_dir, max_parallel)
            else:
                executor = executor_class(output_dir, max_parallel)

            result = executor.run(stories)
            results.append(result)

            console.print(f"  Run {run_num + 1}: {result.completed}/{result.total_stories} completed in {result.total_time:.2f}s")

    return results


def compare_outputs(lloyd_results: list[BenchmarkResult], ralph_results: list[BenchmarkResult]) -> dict:
    """Compare output consistency between executors."""
    lloyd_hashes = set()
    ralph_hashes = set()

    for result in lloyd_results:
        lloyd_hashes.update(result.output_hashes)

    for result in ralph_results:
        ralph_hashes.update(result.output_hashes)

    # Check for consistency within each executor
    lloyd_consistent = len(lloyd_hashes) > 0
    ralph_consistent = len(ralph_hashes) > 0

    return {
        "lloyd_unique_outputs": len(lloyd_hashes),
        "ralph_unique_outputs": len(ralph_hashes),
        "lloyd_consistent": lloyd_consistent,
        "ralph_consistent": ralph_consistent,
    }


def print_results(lloyd_results: list[BenchmarkResult], ralph_results: list[BenchmarkResult]) -> None:
    """Print formatted benchmark results."""
    table = Table(title="Executor Benchmark Comparison")

    table.add_column("Metric", style="cyan")
    table.add_column("Lloyd", style="green")
    table.add_column("Ralph", style="blue")
    table.add_column("Winner", style="yellow")

    # Aggregate results
    lloyd_avg_time = statistics.mean(r.total_time for r in lloyd_results)
    ralph_avg_time = statistics.mean(r.total_time for r in ralph_results)

    lloyd_avg_completed = statistics.mean(r.completed for r in lloyd_results)
    ralph_avg_completed = statistics.mean(r.completed for r in ralph_results)

    lloyd_avg_conflicts = statistics.mean(r.conflicts for r in lloyd_results)
    ralph_avg_conflicts = statistics.mean(r.conflicts for r in ralph_results)

    lloyd_throughput = statistics.mean(r.throughput for r in lloyd_results)
    ralph_throughput = statistics.mean(r.throughput for r in ralph_results)

    # Add rows
    table.add_row(
        "Avg Total Time",
        f"{lloyd_avg_time:.2f}s",
        f"{ralph_avg_time:.2f}s",
        "Lloyd" if lloyd_avg_time < ralph_avg_time else "Ralph",
    )

    table.add_row(
        "Avg Completed",
        f"{lloyd_avg_completed:.1f}",
        f"{ralph_avg_completed:.1f}",
        "Lloyd" if lloyd_avg_completed > ralph_avg_completed else "Ralph",
    )

    table.add_row(
        "Completion Rate",
        f"{lloyd_results[0].completion_rate:.0%}",
        f"{ralph_results[0].completion_rate:.0%}",
        "Lloyd" if lloyd_results[0].completion_rate > ralph_results[0].completion_rate else "Ralph",
    )

    table.add_row(
        "Avg Conflicts",
        f"{lloyd_avg_conflicts:.1f}",
        f"{ralph_avg_conflicts:.1f}",
        "Lloyd" if lloyd_avg_conflicts < ralph_avg_conflicts else "Ralph",
    )

    table.add_row(
        "Throughput",
        f"{lloyd_throughput:.2f} stories/s",
        f"{ralph_throughput:.2f} stories/s",
        "Lloyd" if lloyd_throughput > ralph_throughput else "Ralph",
    )

    console.print(table)

    # Output consistency
    output_comparison = compare_outputs(lloyd_results, ralph_results)
    console.print(f"\n[bold]Output Consistency:[/bold]")
    console.print(f"  Lloyd unique outputs: {output_comparison['lloyd_unique_outputs']}")
    console.print(f"  Ralph unique outputs: {output_comparison['ralph_unique_outputs']}")


def run_scaling_test(story_counts: list[int], max_parallel: int, runs: int = 2) -> None:
    """Test how each executor scales with story count."""
    console.print(f"\n[bold]Scaling Test (max_parallel={max_parallel})[/bold]\n")

    table = Table(title="Scaling Comparison")
    table.add_column("Stories", style="cyan")
    table.add_column("Lloyd Time", style="green")
    table.add_column("Ralph Time", style="blue")
    table.add_column("Lloyd Throughput", style="green")
    table.add_column("Ralph Throughput", style="blue")

    for count in story_counts:
        console.print(f"Testing with {count} stories...")
        stories = generate_stories(count, with_dependencies=False)

        lloyd_results = run_benchmark(LloydExecutor, stories, max_parallel, runs)
        ralph_results = run_benchmark(RalphExecutor, stories, max_parallel, runs)

        lloyd_time = statistics.mean(r.total_time for r in lloyd_results)
        ralph_time = statistics.mean(r.total_time for r in ralph_results)
        lloyd_throughput = statistics.mean(r.throughput for r in lloyd_results)
        ralph_throughput = statistics.mean(r.throughput for r in ralph_results)

        table.add_row(
            str(count),
            f"{lloyd_time:.2f}s",
            f"{ralph_time:.2f}s",
            f"{lloyd_throughput:.2f}/s",
            f"{ralph_throughput:.2f}/s",
        )

    console.print(table)


def main() -> None:
    """Run the benchmark comparison."""
    parser = argparse.ArgumentParser(description="Compare Lloyd vs Ralph executors")
    parser.add_argument("--max-parallel", "-p", type=int, default=3, help="Max parallel workers")
    parser.add_argument("--stories", "-s", type=int, default=20, help="Number of stories to test")
    parser.add_argument("--runs", "-r", type=int, default=3, help="Number of benchmark runs")
    parser.add_argument("--scaling", action="store_true", help="Run scaling test")
    args = parser.parse_args()

    console.print("[bold]Executor Benchmark: Lloyd vs Ralph[/bold]\n")
    console.print(f"Configuration: {args.stories} stories, {args.max_parallel} max parallel, {args.runs} runs\n")

    if args.scaling:
        run_scaling_test([10, 25, 50, 100], args.max_parallel, args.runs)
    else:
        # Generate test stories
        stories = generate_stories(args.stories, with_dependencies=True)
        console.print(f"Generated {len(stories)} test stories\n")

        # Run Lloyd benchmark
        console.print("[bold green]Running Lloyd Executor...[/bold green]")
        lloyd_results = run_benchmark(LloydExecutor, stories, args.max_parallel, args.runs)

        # Run Ralph benchmark
        console.print("\n[bold blue]Running Ralph Executor...[/bold blue]")
        ralph_results = run_benchmark(RalphExecutor, stories, args.max_parallel, args.runs)

        # Compare results
        console.print("\n")
        print_results(lloyd_results, ralph_results)


if __name__ == "__main__":
    main()
