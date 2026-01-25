"""Iterative executor with TDD and self-verification loops.

This module implements a more robust execution approach that:
1. Breaks down stories into implementable chunks
2. Uses test-driven development
3. Iterates until tests pass (inner loop)
4. Integrates with ralph-loop for outer orchestration
"""

import logging
import os
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Configure logger
logger = logging.getLogger(__name__)

# Suppress litellm verbose logging
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
logging.getLogger("litellm").setLevel(logging.WARNING)
logging.getLogger("litellm.litellm_core_utils").setLevel(logging.ERROR)

# Fix Windows console encoding
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        logger.debug("Console reconfigure not available")
    except Exception as e:
        logger.warning(f"Failed to configure Windows console: {e}")

from rich.console import Console

from lloyd.config import get_llm_client

# Use safe_box for Windows compatibility
console = Console(force_terminal=True, safe_box=True)


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for Windows compatibility.

    Args:
        filename: The filename to sanitize.

    Returns:
        Sanitized filename safe for Windows.
    """
    # Remove or replace invalid Windows filename characters
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, "_", filename)

    # Remove control characters
    sanitized = "".join(c for c in sanitized if ord(c) >= 32)

    # Ensure it doesn't start/end with spaces or dots
    sanitized = sanitized.strip(". ")

    # Handle reserved Windows names
    reserved = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
                "COM5", "COM6", "COM7", "COM8", "COM9", "LPT1", "LPT2",
                "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}
    name_without_ext = sanitized.split(".")[0].upper()
    if name_without_ext in reserved:
        sanitized = f"_{sanitized}"

    return sanitized or "unnamed"


def safe_write_text(path: Path, content: str) -> None:
    """Write text to a file with Windows-safe encoding handling.

    Args:
        path: Path to write to.
        content: Content to write.
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Sanitize the filename portion
    sanitized_name = sanitize_filename(path.name)
    safe_path = path.parent / sanitized_name

    # Replace problematic characters in content
    # Some LLM outputs contain characters that cause issues on Windows
    safe_content = content.encode("utf-8", errors="replace").decode("utf-8")

    # Write with explicit encoding and error handling
    try:
        with open(safe_path, "w", encoding="utf-8", errors="replace", newline="\n") as f:
            f.write(safe_content)
    except OSError as e:
        # If still failing, try with even more aggressive sanitization
        console.print(f"[yellow]File write failed ({e}), retrying with sanitization...[/yellow]")
        # Remove any remaining problematic characters
        safe_content = "".join(c for c in safe_content if ord(c) < 128 or ord(c) >= 160)
        with open(safe_path, "w", encoding="utf-8", errors="ignore", newline="\n") as f:
            f.write(safe_content)


@dataclass
class ExecutionStep:
    """A single step in the implementation."""

    id: str
    description: str
    test_file: str | None = None
    impl_file: str | None = None
    status: str = "pending"  # pending, in_progress, passed, failed
    attempts: int = 0
    max_attempts: int = 5
    error: str | None = None


@dataclass
class ExecutionPlan:
    """Plan for implementing a story."""

    story_id: str
    story_title: str
    steps: list[ExecutionStep] = field(default_factory=list)
    current_step: int = 0


def get_isolated_workspace(session_id: str | None = None) -> Path:
    """Get an isolated workspace directory for Lloyd outputs.

    This prevents test outputs from polluting the source tree and
    overwriting config files like pyproject.toml.

    Args:
        session_id: Optional session identifier. If not provided, generates one.

    Returns:
        Path to isolated workspace directory.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())[:8]

    # Use user's home directory for isolation
    home = Path.home()
    workspace = home / ".lloyd" / "workspace" / session_id
    workspace.mkdir(parents=True, exist_ok=True)

    # Create tests subdirectory
    (workspace / "tests").mkdir(exist_ok=True)

    return workspace


class IterativeExecutor:
    """Executor that uses TDD and iterates until tests pass."""

    # Default test timeout in seconds
    DEFAULT_TEST_TIMEOUT = 60

    def __init__(
        self,
        working_dir: Path | None = None,
        max_iterations_per_step: int = 5,
        session_id: str | None = None,
        test_timeout: int | None = None,
    ) -> None:
        """Initialize the executor.

        Args:
            working_dir: Directory to work in. If None, uses isolated workspace.
            max_iterations_per_step: Max attempts per step before escalating.
            session_id: Optional session ID for workspace isolation.
            test_timeout: Timeout in seconds for running tests (default: 60).
        """
        # Use isolated workspace by default to prevent source tree pollution
        if working_dir is None:
            self.working_dir = get_isolated_workspace(session_id)
        else:
            self.working_dir = working_dir
        self.max_iterations = max_iterations_per_step
        self.test_timeout = test_timeout or self.DEFAULT_TEST_TIMEOUT
        self.llm = get_llm_client()

    def decompose_story(self, story: dict[str, Any]) -> ExecutionPlan:
        """Break a story into implementable steps.

        Args:
            story: Story dict with title, description, acceptance criteria.

        Returns:
            ExecutionPlan with concrete steps.
        """
        title = story.get("title", "Unknown")
        description = story.get("description", "")
        criteria = story.get("acceptanceCriteria", [])

        # Use LLM to decompose into steps
        prompt = f"""Decompose this user story into concrete implementation steps.

Story: {title}
Description: {description}
Acceptance Criteria:
{chr(10).join(f'- {c}' for c in criteria)}

Return a JSON list of steps, each with:
- description: What to implement (be specific - file names, function names)
- test_file: Path for the test file (MUST be in tests/ folder, e.g., tests/test_feature.py)
- impl_file: Path for the implementation (MUST be a simple filename in the root, e.g., feature.py - NO subdirectories)

CRITICAL RULES (FOLLOW EXACTLY):
1. impl_file MUST be a SIMPLE filename like "main.py" or "counter.py"
   - CORRECT: "counter.py", "calculator.py", "main.py"
   - WRONG: "src/counter.py", "app/calculator.py", "lib/main.py"
2. test_file MUST be in tests/ folder like "tests/test_main.py"
3. Keep it simple - 1-3 steps for simple projects, 2-4 for complex ones
4. Each step should be independently testable
5. DO NOT create nested directory structures - all implementation files go in the root

STEP ORDERING STRATEGY:
- Step 1: Core class/function with basic functionality
- Step 2: Add secondary methods that build on step 1
- Step 3: Add advanced features (error handling, edge cases, complex logic)
- Each step KEEPS the same impl_file - we're building incrementally!

For complex features (transactions, caching, etc.):
- Break into small, testable increments
- Each step should pass before moving to next
- Later steps can use the SAME test file with more tests added

Example for a Database with CRUD + Transactions:
[
  {{"description": "Create Database class with get and set methods", "test_file": "tests/test_database.py", "impl_file": "database.py"}},
  {{"description": "Add delete method to Database class", "test_file": "tests/test_database.py", "impl_file": "database.py"}},
  {{"description": "Add begin_transaction, commit, and rollback methods for transaction support", "test_file": "tests/test_database.py", "impl_file": "database.py"}}
]

Return ONLY the JSON array, no markdown or explanation."""

        try:
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # Parse JSON from response
            import json

            # Clean up response - remove markdown code blocks if present
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()

            steps_data = json.loads(content)

            steps = []
            for i, step_data in enumerate(steps_data):
                steps.append(
                    ExecutionStep(
                        id=f"step-{i+1:03d}",
                        description=step_data.get("description", f"Step {i+1}"),
                        test_file=step_data.get("test_file"),
                        impl_file=step_data.get("impl_file"),
                    )
                )

            return ExecutionPlan(
                story_id=story.get("id", str(uuid.uuid4())[:8]),
                story_title=title,
                steps=steps,
            )

        except Exception as e:
            console.print(f"[yellow]Decomposition failed: {e}, using single step[/yellow]")
            # Fallback to single step
            return ExecutionPlan(
                story_id=story.get("id", str(uuid.uuid4())[:8]),
                story_title=title,
                steps=[
                    ExecutionStep(
                        id="step-001",
                        description=f"Implement: {title}",
                        test_file="tests/test_main.py",
                        impl_file="main.py",
                    )
                ],
            )

    def write_test(self, step: ExecutionStep, context: str = "") -> str:
        """Generate test code for a step.

        Args:
            step: The execution step.
            context: Additional context (existing code, etc.)

        Returns:
            Generated test code.
        """
        # Determine module name from impl_file (e.g., "cli_tool.py" -> "cli_tool")
        # Extract just the filename without path or extension
        impl_file = step.impl_file or "main.py"
        impl_module = Path(impl_file).stem  # e.g., "counter.py" -> "counter"

        prompt = f"""Write pytest tests for this implementation step:

Step: {step.description}
Test file: {step.test_file}
Implementation file: {step.impl_file}

{f'Context: {context}' if context else ''}

CRITICAL IMPORT RULES (FOLLOW EXACTLY):
- The implementation file "{step.impl_file}" will be at the ROOT of the working directory
- Import MUST be: `from {impl_module} import ...`
- DO NOT use nested paths like "from src.{impl_module}" or "from app.{impl_module}"
- DO NOT add any prefix - just use the module name directly

CORRECT import example:
```python
from {impl_module} import MyClass, my_function
```

WRONG import examples (DO NOT USE):
```python
from src.{impl_module} import ...  # WRONG - no src prefix
from app.{impl_module} import ...  # WRONG - no app prefix
from .{impl_module} import ...     # WRONG - no relative import
```

ADDITIONAL REQUIREMENTS:
1. Use pytest with clear test function names (test_*)
2. Use pytest fixtures like `tmp_path` for any file operations - do NOT reference hardcoded file paths
3. All tests must be self-contained and create their own test data
4. Keep tests SIMPLE - only 3-5 basic test cases
5. Double-check your expected values are correct before writing them

CRITICAL IMPORT RULES:
- If you use `pytest.raises()`, `pytest.fixture`, or any pytest.* features, you MUST add `import pytest` at the top!
- If you use datetime, date, or timedelta, you MUST add `from datetime import datetime, date, timedelta` at the top!
- If you use typing features like Optional, List, Dict, you MUST add the appropriate import!

Example with all common imports:
```python
import pytest
from datetime import datetime, date, timedelta
from {impl_module} import MyClass

def test_raises_error():
    with pytest.raises(ValueError):
        MyClass().invalid_operation()

def test_with_date():
    due = datetime(2024, 12, 31)
    result = MyClass().add_task("test", due_date=due)
    assert result is not None
```

TEST ONLY PUBLIC API:
- Test through method return values and behavior, NOT internal attributes
- WRONG: `assert obj._internal_list == [1,2,3]` or `assert obj.edges == ...`
- RIGHT: `assert obj.get_items() == [1,2,3]` or `assert obj.has_edge('A', 'B')`
- If you need to check internal state, call a method that exposes it

VERY IMPORTANT - VERIFY YOUR EXPECTED VALUES:
- For string reversal: "hello" reversed is "olleh", "abc" reversed is "cba"
- For counting: count manually to verify your expected numbers
- DO NOT hallucinate or guess expected values - compute them correctly

Example of GOOD simple tests:
```python
from {impl_module} import some_function

def test_basic_case():
    result = some_function("hello")
    assert result == "olleh"  # Verified: h-e-l-l-o reversed is o-l-l-e-h

def test_empty_input():
    result = some_function("")
    assert result == ""

def test_single_char():
    result = some_function("a")
    assert result == "a"
```

Return ONLY the Python test code, no markdown or explanation.
Start with imports, then test functions. Keep it simple - 3-5 tests maximum."""

        response = self.llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        # Clean up - remove markdown code blocks
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        return content

    def write_implementation(
        self,
        step: ExecutionStep,
        test_code: str,
        error_output: str = "",
        previous_attempt: str = "",
    ) -> str:
        """Generate implementation code to pass tests.

        Args:
            step: The execution step.
            test_code: The test code to pass.
            error_output: Error output from previous test run.
            previous_attempt: Previous implementation attempt.

        Returns:
            Generated implementation code.
        """
        # Build context about existing code and errors
        existing_code_section = ""
        if previous_attempt:
            existing_code_section = f"""
EXISTING CODE (you MUST preserve and extend this):
```python
{previous_attempt}
```

CRITICAL: Your response must include ALL the code from above PLUS the new functionality.
Do NOT remove or replace existing methods - only ADD to them or extend them.
"""

        error_context = ""
        if error_output:
            error_context = f"""
TEST FAILURES TO FIX:
{error_output[:1500]}

Analyze the error and fix only what's broken. Keep working code intact.
"""

        prompt = f"""Write implementation code to pass these tests.

Step: {step.description}
Implementation file: {step.impl_file}

Tests to pass:
```python
{test_code}
```
{existing_code_section}{error_context}
CRITICAL REQUIREMENTS:
1. If existing code is provided above, you MUST include ALL of it in your response
2. ADD new methods/functionality to the existing code - don't replace it
3. Preserve all imports, class definitions, and methods from existing code
4. Only modify what's necessary to pass the new tests

IMPLEMENTATION RULES:
- Read the test assertions CAREFULLY - match exactly what they expect
- If test uses `obj.method()`, implement that method
- If test expects `ValueError`, raise `ValueError` (not a custom exception)
- If test expects a specific return format (list, tuple, dict), match it exactly
- Use proper type hints and docstrings
- Make it ACTUALLY WORK, not just scaffold/stub code

OUTPUT FORMAT:
Return ONLY the complete Python implementation code.
No markdown code blocks, no explanation - just the Python code.
Start with imports, then classes/functions.
Include ALL existing code plus new additions."""

        response = self.llm.invoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        # Clean up - remove markdown code blocks
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        return content

    def run_tests(self, test_file: str) -> tuple[bool, str]:
        """Run pytest on a test file.

        Args:
            test_file: Path to test file.

        Returns:
            Tuple of (passed, output).
        """
        # Resolve all paths to absolute for consistent behavior
        working_dir_abs = self.working_dir.resolve()
        test_path = (working_dir_abs / test_file).resolve()

        if not test_path.exists():
            return False, f"Test file not found: {test_path}"

        try:
            # Set PYTHONPATH to include the working directory so imports work
            env = os.environ.copy()
            existing_pythonpath = env.get("PYTHONPATH", "")
            if existing_pythonpath:
                env["PYTHONPATH"] = f"{working_dir_abs}{os.pathsep}{existing_pythonpath}"
            else:
                env["PYTHONPATH"] = str(working_dir_abs)

            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"],
                cwd=working_dir_abs,
                capture_output=True,
                text=True,
                timeout=self.test_timeout,
                env=env,
            )

            output = result.stdout + result.stderr
            passed = result.returncode == 0

            # Debug output for first run
            if not passed:
                console.print(f"[dim]Return code: {result.returncode}[/dim]")
                console.print(f"[dim]Working dir: {working_dir_abs}[/dim]")
                console.print(f"[dim]PYTHONPATH: {env.get('PYTHONPATH', 'not set')}[/dim]")
                # Print last 10 lines of output
                out_lines = output.strip().split('\n')[-10:]
                console.print(f"[dim]Output tail: {chr(10).join(out_lines)}[/dim]")

            return passed, output

        except subprocess.TimeoutExpired:
            return False, f"Test execution timed out ({self.test_timeout}s)"
        except Exception as e:
            return False, f"Test execution error: {e}"

    def execute_step(self, step: ExecutionStep, context: str = "", existing_impl: str = "") -> bool:
        """Execute a single step using TDD loop.

        Args:
            step: The step to execute.
            context: Additional context from previous steps.
            existing_impl: Existing implementation code to build upon.

        Returns:
            True if step passed, False otherwise.
        """
        step.status = "in_progress"
        console.print(f"\n[cyan]Step: {step.description}[/cyan]")

        # Phase 1: Write tests (include context about existing implementation)
        console.print("[dim]Writing tests...[/dim]")
        test_context = context
        if existing_impl:
            test_context += f"\n\nEXISTING IMPLEMENTATION (build on this):\n```python\n{existing_impl}\n```"
        test_code = self.write_test(step, test_context)

        # Save test file
        test_path = self.working_dir / step.test_file
        safe_write_text(test_path, test_code)
        console.print(f"[dim]Created: {step.test_file}[/dim]")

        # Phase 2: Iterate on implementation until tests pass
        # Start with existing implementation if available
        impl_code = existing_impl
        error_output = ""

        for attempt in range(1, self.max_iterations + 1):
            step.attempts = attempt
            console.print(f"[yellow]Attempt {attempt}/{self.max_iterations}[/yellow]")

            # Generate implementation (pass existing as base to build on)
            impl_code = self.write_implementation(
                step, test_code, error_output, impl_code
            )

            # Save implementation
            impl_path = self.working_dir / step.impl_file
            safe_write_text(impl_path, impl_code)

            # Run tests
            passed, output = self.run_tests(step.test_file)

            if passed:
                step.status = "passed"
                console.print(f"[green]PASSED on attempt {attempt}[/green]")
                return True

            error_output = output
            # Print truncated error for debugging
            if output:
                error_lines = output.split('\n')
                # Find the failure lines
                failure_summary = [l for l in error_lines if 'FAILED' in l or 'AssertionError' in l or 'Error' in l]
                if failure_summary:
                    console.print(f"[dim]{chr(10).join(failure_summary[:3])}[/dim]")
            console.print(f"[red]Tests failed, retrying...[/red]")

        # All attempts failed
        step.status = "failed"
        step.error = error_output[:500]
        console.print(f"[red]Step failed after {self.max_iterations} attempts[/red]")
        return False

    def execute_story(self, story: dict[str, Any]) -> dict[str, Any]:
        """Execute a full story using iterative TDD.

        Args:
            story: Story dict to execute.

        Returns:
            Result dict with status and details.
        """
        console.print(f"\n[bold blue]=== Executing: {story.get('title')} ===[/bold blue]")

        # Decompose into steps
        plan = self.decompose_story(story)
        console.print(f"[dim]Decomposed into {len(plan.steps)} steps[/dim]")

        # Execute each step
        passed_steps = 0
        failed_steps = []

        for step in plan.steps:
            # Build context from previous steps (for different files)
            context = ""
            existing_impl = ""

            if passed_steps > 0:
                # Include previous implementations as context
                for prev_step in plan.steps[:passed_steps]:
                    if prev_step.impl_file:
                        impl_path = self.working_dir / prev_step.impl_file
                        if impl_path.exists():
                            prev_content = impl_path.read_text()
                            # If same file, this IS the existing implementation to build on
                            if prev_step.impl_file == step.impl_file:
                                existing_impl = prev_content
                            else:
                                # Different file - add as context
                                context += f"\n# From {prev_step.impl_file}:\n"
                                context += prev_content[:1000]

            # Also check if the current impl file already exists (from earlier runs)
            if not existing_impl and step.impl_file:
                impl_path = self.working_dir / step.impl_file
                if impl_path.exists():
                    existing_impl = impl_path.read_text()

            success = self.execute_step(step, context, existing_impl)

            if success:
                passed_steps += 1
            else:
                failed_steps.append(step)
                # Continue trying other steps or stop?
                # For now, continue to see what can be done
                console.print(f"[yellow]Continuing despite failure...[/yellow]")

        # Summary
        total = len(plan.steps)
        all_passed = len(failed_steps) == 0

        result = {
            "story_id": plan.story_id,
            "story_title": plan.story_title,
            "total_steps": total,
            "passed_steps": passed_steps,
            "failed_steps": len(failed_steps),
            "status": "complete" if all_passed else "partial",
            "passes": all_passed,
        }

        if failed_steps:
            result["failures"] = [
                {"step": s.id, "description": s.description, "error": s.error}
                for s in failed_steps
            ]

        # Output completion promise for ralph-loop integration
        if all_passed:
            console.print(f"\n[green]<promise>STORY_COMPLETE</promise>[/green]")
        else:
            console.print(f"\n[yellow]<promise>STORY_PARTIAL:{passed_steps}/{total}</promise>[/yellow]")

        return result


def run_iterative_execution(story: dict[str, Any], working_dir: Path | None = None) -> dict[str, Any]:
    """Run iterative TDD execution on a story.

    Args:
        story: Story to execute.
        working_dir: Working directory.

    Returns:
        Execution result.
    """
    executor = IterativeExecutor(working_dir)
    return executor.execute_story(story)
