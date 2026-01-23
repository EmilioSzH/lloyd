# tests/benchmark/compare_executors.py

"""
Benchmark comparing Lloyd native parallel vs Ralphy execution.

Run: python -m tests.benchmark.compare_executors
"""

import time
import subprocess
import json
import sys
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict
import tempfile
import shutil

# Windows compatibility
IS_WINDOWS = sys.platform == "win32"

@dataclass
class BenchmarkResult:
    executor: str
    total_time_seconds: float
    tasks_completed: int
    tasks_failed: int
    estimated_tokens: int
    estimated_cost: float
    merge_conflicts: int
    output_hash: str  # Hash of final codebase for quality comparison

@dataclass  
class BenchmarkTask:
    title: str
    description: str
    expected_files: List[str]  # Files this should create/modify
    can_parallel: bool  # True if no dependencies

# Standard benchmark task set - deterministic, measurable
BENCHMARK_TASKS = [
    BenchmarkTask(
        title="Create User model",
        description="Create a User model with id, email, name, created_at fields in src/models/user.py",
        expected_files=["src/models/user.py"],
        can_parallel=True
    ),
    BenchmarkTask(
        title="Create Post model", 
        description="Create a Post model with id, title, body, user_id, created_at in src/models/post.py",
        expected_files=["src/models/post.py"],
        can_parallel=True
    ),
    BenchmarkTask(
        title="Create Comment model",
        description="Create a Comment model with id, body, user_id, post_id, created_at in src/models/comment.py", 
        expected_files=["src/models/comment.py"],
        can_parallel=True
    ),
    BenchmarkTask(
        title="Add User API endpoints",
        description="Create CRUD endpoints for User in src/api/users.py",
        expected_files=["src/api/users.py"],
        can_parallel=True
    ),
    BenchmarkTask(
        title="Add Post API endpoints",
        description="Create CRUD endpoints for Post in src/api/posts.py",
        expected_files=["src/api/posts.py"],
        can_parallel=True
    ),
    BenchmarkTask(
        title="Add relationships",
        description="Add User.posts and Post.comments relationships to models",
        expected_files=["src/models/user.py", "src/models/post.py"],
        can_parallel=False  # Depends on models existing
    ),
]

class ExecutorBenchmark:
    def __init__(self, project_template: Path, output_dir: Path):
        self.template = project_template
        self.output_dir = output_dir
        self.results: Dict[str, BenchmarkResult] = {}
    
    def setup_fresh_project(self, name: str) -> Path:
        """Copy template to fresh directory."""
        project_path = self.output_dir / name
        if project_path.exists():
            # On Windows, git marks some files read-only, requiring special handling
            def remove_readonly(func, path, excinfo):
                import stat
                os.chmod(path, stat.S_IWRITE)
                func(path)
            shutil.rmtree(project_path, onexc=remove_readonly)
        shutil.copytree(self.template, project_path)
        
        # Initialize git
        subprocess.run(["git", "init"], cwd=project_path, capture_output=True, shell=IS_WINDOWS)
        subprocess.run(["git", "add", "."], cwd=project_path, capture_output=True, shell=IS_WINDOWS)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=project_path, capture_output=True, shell=IS_WINDOWS)
        
        return project_path
    
    def run_lloyd_native(self, tasks: List[BenchmarkTask], max_parallel: int = 3) -> BenchmarkResult:
        """Run tasks using Lloyd's native parallel executor."""
        project_path = self.setup_fresh_project("lloyd_native")
        
        # Generate Lloyd PRD
        prd = self._tasks_to_lloyd_prd(tasks)
        prd_path = project_path / ".lloyd" / "prd.json"
        prd_path.parent.mkdir(exist_ok=True)
        prd_path.write_text(json.dumps(prd))
        
        start = time.time()

        # Run Lloyd
        lloyd_cmd = ["uv", "run", "lloyd", "run", "--max-parallel", str(max_parallel)]
        result = subprocess.run(
            lloyd_cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            shell=IS_WINDOWS,
        )

        elapsed = time.time() - start

        if result.returncode != 0:
            print(f"  Lloyd returned non-zero: {result.returncode}")
            if result.stderr:
                print(f"  stderr: {result.stderr[:500]}")
        
        return BenchmarkResult(
            executor="lloyd_native",
            total_time_seconds=elapsed,
            tasks_completed=self._count_completed(project_path, tasks),
            tasks_failed=self._count_failed(project_path, tasks),
            estimated_tokens=self._parse_tokens(result.stdout),
            estimated_cost=self._parse_cost(result.stdout),
            merge_conflicts=0,  # No merging in Lloyd native
            output_hash=self._hash_codebase(project_path)
        )
    
    def run_ralphy(self, tasks: List[BenchmarkTask], max_parallel: int = 3) -> BenchmarkResult:
        """Run tasks using Ralphy."""
        project_path = self.setup_fresh_project("ralphy")
        
        # Generate Ralphy YAML
        yaml_content = self._tasks_to_ralphy_yaml(tasks)
        yaml_path = project_path / "benchmark.yaml"
        yaml_path.write_text(yaml_content)
        
        start = time.time()

        # Run Ralphy
        ralphy_cmd = [
            "ralphy",
            "--yaml", str(yaml_path),
            "--parallel",
            "--max-parallel", str(max_parallel),
            "--no-commit",  # We'll check files directly
        ]
        result = subprocess.run(
            ralphy_cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            shell=IS_WINDOWS,
        )

        elapsed = time.time() - start

        if result.returncode != 0:
            print(f"  Ralphy returned non-zero: {result.returncode}")
            if result.stderr:
                print(f"  stderr: {result.stderr[:500]}")
        
        return BenchmarkResult(
            executor="ralphy",
            total_time_seconds=elapsed,
            tasks_completed=self._count_completed(project_path, tasks),
            tasks_failed=self._count_failed(project_path, tasks),
            estimated_tokens=self._parse_tokens(result.stdout),
            estimated_cost=self._parse_cost(result.stdout),
            merge_conflicts=result.stdout.count("conflict"),
            output_hash=self._hash_codebase(project_path)
        )
    
    def run_hybrid(self, tasks: List[BenchmarkTask], max_parallel: int = 3) -> BenchmarkResult:
        """Run with Lloyd planning + Ralphy execution."""
        project_path = self.setup_fresh_project("hybrid")
        
        start = time.time()
        
        # Step 1: Lloyd analyzes and generates optimized Ralphy YAML
        optimized_yaml = self._lloyd_plan_for_ralphy(tasks, project_path)
        yaml_path = project_path / "optimized.yaml"
        yaml_path.write_text(optimized_yaml)
        
        # Step 2: Ralphy executes
        ralphy_cmd = [
            "ralphy",
            "--yaml", str(yaml_path),
            "--parallel",
            "--max-parallel", str(max_parallel),
        ]
        result = subprocess.run(
            ralphy_cmd,
            cwd=project_path,
            capture_output=True,
            text=True,
            shell=IS_WINDOWS,
        )
        
        elapsed = time.time() - start
        
        # Step 3: Lloyd records learnings (would happen in real integration)
        
        return BenchmarkResult(
            executor="hybrid",
            total_time_seconds=elapsed,
            tasks_completed=self._count_completed(project_path, tasks),
            tasks_failed=self._count_failed(project_path, tasks),
            estimated_tokens=self._parse_tokens(result.stdout),
            estimated_cost=self._parse_cost(result.stdout),
            merge_conflicts=result.stdout.count("conflict"),
            output_hash=self._hash_codebase(project_path)
        )
    
    def _tasks_to_lloyd_prd(self, tasks: List[BenchmarkTask]) -> dict:
        """Convert benchmark tasks to Lloyd PRD format."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        stories = []
        for i, task in enumerate(tasks):
            stories.append({
                "id": f"story-{i:03d}",
                "title": task.title,
                "description": task.description,
                "priority": 1,
                "dependencies": [] if task.can_parallel else [f"story-{j:03d}" for j in range(i)],
                "acceptanceCriteria": [f"File {f} exists and contains valid code" for f in task.expected_files],
                "passes": False,
                "attempts": 0,
                "lastAttemptAt": None,
                "notes": "",
                "status": "pending",
                "workerId": None,
                "startedAt": None,
                "completedAt": None,
            })
        return {
            "projectName": "Benchmark Project",
            "description": "Auto-generated benchmark project for executor comparison",
            "branchName": "main",
            "createdAt": now,
            "updatedAt": now,
            "status": "idle",
            "stories": stories,
            "metadata": {
                "totalStories": len(stories),
                "completedStories": 0,
                "inProgressStories": 0,
                "currentStory": None,
                "estimatedIterations": len(stories),
                "actualIterations": 0,
            }
        }
    
    def _tasks_to_ralphy_yaml(self, tasks: List[BenchmarkTask]) -> str:
        """Convert benchmark tasks to Ralphy YAML format."""
        import yaml
        
        # Simple grouping: all parallel tasks in group 1, sequential in group 2
        yaml_tasks = []
        for task in tasks:
            yaml_tasks.append({
                "title": task.title,
                "description": task.description,
                "parallel_group": 1 if task.can_parallel else 2
            })
        
        return yaml.dump({"tasks": yaml_tasks})
    
    def _lloyd_plan_for_ralphy(self, tasks: List[BenchmarkTask], project_path: Path) -> str:
        """Use Lloyd's intelligence to generate optimized Ralphy YAML."""
        import yaml
        
        # This would call Lloyd's planning crew in real implementation
        # For benchmark, we simulate intelligent grouping
        
        yaml_tasks = []
        parallel_group = 1
        
        # Group by expected file overlap (smarter than simple can_parallel flag)
        file_groups = {}
        for task in tasks:
            key = tuple(sorted(task.expected_files))
            if key not in file_groups:
                file_groups[key] = []
            file_groups[key].append(task)
        
        for files, group_tasks in file_groups.items():
            for task in group_tasks:
                yaml_tasks.append({
                    "title": task.title,
                    "description": task.description,
                    "parallel_group": parallel_group
                })
            parallel_group += 1
        
        return yaml.dump({"tasks": yaml_tasks})
    
    def _count_completed(self, project_path: Path, tasks: List[BenchmarkTask]) -> int:
        """Count tasks that created expected files."""
        completed = 0
        for task in tasks:
            if all((project_path / f).exists() for f in task.expected_files):
                completed += 1
        return completed
    
    def _count_failed(self, project_path: Path, tasks: List[BenchmarkTask]) -> int:
        """Count tasks that didn't create expected files."""
        return len(tasks) - self._count_completed(project_path, tasks)
    
    def _hash_codebase(self, project_path: Path) -> str:
        """Hash all source files for quality comparison."""
        import hashlib
        
        hasher = hashlib.sha256()
        for f in sorted(project_path.rglob("*.py")):
            if ".git" not in str(f):
                hasher.update(f.read_bytes())
        return hasher.hexdigest()[:16]
    
    def _parse_tokens(self, output: str) -> int:
        """Extract token count from output."""
        # Implementation depends on output format
        return 0
    
    def _parse_cost(self, output: str) -> float:
        """Extract cost from output."""
        return 0.0
    
    def compare(self, tasks: List[BenchmarkTask], max_parallel: int = 3) -> Dict[str, BenchmarkResult]:
        """Run all executors and compare."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Running benchmark with {len(tasks)} tasks, {max_parallel} max parallel agents")
        print(f"Output directory: {self.output_dir}\n")
        
        print("=" * 60)
        print("Running Lloyd Native...")
        self.results["lloyd_native"] = self.run_lloyd_native(tasks, max_parallel)
        print(f"  Completed in {self.results['lloyd_native'].total_time_seconds:.1f}s")
        
        print("=" * 60)
        print("Running Ralphy...")
        self.results["ralphy"] = self.run_ralphy(tasks, max_parallel)
        print(f"  Completed in {self.results['ralphy'].total_time_seconds:.1f}s")
        
        print("=" * 60)
        print("Running Hybrid (Lloyd planning + Ralphy execution)...")
        self.results["hybrid"] = self.run_hybrid(tasks, max_parallel)
        print(f"  Completed in {self.results['hybrid'].total_time_seconds:.1f}s")
        
        return self.results
    
    def print_report(self):
        """Print comparison report."""
        print("\n" + "=" * 60)
        print("BENCHMARK RESULTS")
        print("=" * 60)
        
        headers = ["Metric", "Lloyd Native", "Ralphy", "Hybrid"]
        rows = [
            ["Time (s)", 
             f"{self.results['lloyd_native'].total_time_seconds:.1f}",
             f"{self.results['ralphy'].total_time_seconds:.1f}",
             f"{self.results['hybrid'].total_time_seconds:.1f}"],
            ["Completed",
             str(self.results['lloyd_native'].tasks_completed),
             str(self.results['ralphy'].tasks_completed),
             str(self.results['hybrid'].tasks_completed)],
            ["Failed",
             str(self.results['lloyd_native'].tasks_failed),
             str(self.results['ralphy'].tasks_failed),
             str(self.results['hybrid'].tasks_failed)],
            ["Merge Conflicts",
             str(self.results['lloyd_native'].merge_conflicts),
             str(self.results['ralphy'].merge_conflicts),
             str(self.results['hybrid'].merge_conflicts)],
            ["Output Hash",
             self.results['lloyd_native'].output_hash,
             self.results['ralphy'].output_hash,
             self.results['hybrid'].output_hash],
        ]
        
        # Print table
        col_widths = [max(len(row[i]) for row in [headers] + rows) for i in range(4)]
        
        header_line = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
        print(header_line)
        print("-" * len(header_line))
        
        for row in rows:
            print(" | ".join(cell.ljust(w) for cell, w in zip(row, col_widths)))
        
        # Winner determination
        print("\n" + "-" * 60)
        fastest = min(self.results.items(), key=lambda x: x[1].total_time_seconds)
        most_complete = max(self.results.items(), key=lambda x: x[1].tasks_completed)
        
        print(f">> Fastest: {fastest[0]} ({fastest[1].total_time_seconds:.1f}s)")
        print(f">> Most Complete: {most_complete[0]} ({most_complete[1].tasks_completed}/{len(BENCHMARK_TASKS)})")

        # Quality comparison
        hashes = [r.output_hash for r in self.results.values()]
        if len(set(hashes)) == 1:
            print(">> Output Quality: IDENTICAL (all executors produced same code)")
        else:
            print(">> Output Quality: DIFFERENT (manual review needed)")
            print(f"   Review outputs in: {self.output_dir}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Benchmark Lloyd vs Ralphy execution")
    parser.add_argument("--template", type=Path, default=Path("tests/benchmark/template"),
                       help="Path to project template")
    parser.add_argument("--output", type=Path, default=Path(tempfile.gettempdir()) / "lloyd_benchmark",
                       help="Output directory for benchmark runs")
    parser.add_argument("--max-parallel", type=int, default=3,
                       help="Max parallel agents")
    parser.add_argument("--tasks", type=int, default=None,
                       help="Number of tasks to run (default: all)")
    
    args = parser.parse_args()
    
    tasks = BENCHMARK_TASKS[:args.tasks] if args.tasks else BENCHMARK_TASKS
    
    benchmark = ExecutorBenchmark(args.template, args.output)
    benchmark.compare(tasks, args.max_parallel)
    benchmark.print_report()


if __name__ == "__main__":
    main()