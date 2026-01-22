"""Shell command execution tools for AEGIS agents."""

import subprocess
from typing import Any

from crewai.tools import tool


@tool("Execute Shell Command")
def execute_shell(command: str, timeout: int = 60, cwd: str | None = None) -> str:
    """Execute a shell command and return the output.

    Args:
        command: The shell command to execute.
        timeout: Maximum execution time in seconds (default: 60).
        cwd: Working directory for the command (optional).

    Returns:
        Command output (stdout + stderr) or error message.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )

        output_parts = []
        if result.stdout:
            output_parts.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output_parts.append(f"STDERR:\n{result.stderr}")

        output = "\n\n".join(output_parts) or "Command completed with no output."

        if result.returncode != 0:
            output = f"Command exited with code {result.returncode}\n\n{output}"

        return output

    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing command: {e}"


@tool("Run Python Script")
def run_python_script(script_path: str, args: str = "", timeout: int = 120) -> str:
    """Run a Python script with optional arguments.

    Args:
        script_path: Path to the Python script to run.
        args: Command-line arguments to pass to the script.
        timeout: Maximum execution time in seconds (default: 120).

    Returns:
        Script output or error message.
    """
    command = f"python {script_path}"
    if args:
        command += f" {args}"

    return execute_shell.func(command, timeout=timeout)


@tool("Run Pytest")
def run_pytest(path: str = "tests/", args: str = "-v") -> str:
    """Run pytest on a test path.

    Args:
        path: Path to tests (file or directory).
        args: Additional pytest arguments (default: "-v").

    Returns:
        Test results or error message.
    """
    command = f"python -m pytest {path} {args}"
    return execute_shell.func(command, timeout=300)


@tool("Run Ruff Linter")
def run_ruff(path: str = ".", fix: bool = False) -> str:
    """Run ruff linter on a path.

    Args:
        path: Path to lint (file or directory).
        fix: Whether to automatically fix issues.

    Returns:
        Linting results or error message.
    """
    command = f"python -m ruff check {path}"
    if fix:
        command += " --fix"
    return execute_shell.func(command, timeout=60)


# Type alias for better readability
ToolFunc = Any

# Export all shell tools
SHELL_TOOLS: list[ToolFunc] = [execute_shell, run_python_script, run_pytest, run_ruff]
