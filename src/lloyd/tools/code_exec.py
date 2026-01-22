"""Secure code execution tools via E2B sandboxes."""

import os
from typing import Any

from crewai.tools import tool


def _get_e2b_api_key() -> str | None:
    """Get E2B API key from environment."""
    return os.environ.get("E2B_API_KEY")


@tool("Execute Python Code in Sandbox")
def execute_python_sandbox(code: str, timeout: int = 60) -> str:
    """Execute Python code in a secure E2B sandbox.

    Args:
        code: Python code to execute.
        timeout: Maximum execution time in seconds (default: 60).

    Returns:
        Execution output (stdout, stderr, return value) or error message.
    """
    api_key = _get_e2b_api_key()
    if not api_key:
        # Fall back to local execution with warning
        return _execute_local_python(code, timeout)

    try:
        from e2b_code_interpreter import Sandbox

        with Sandbox(api_key=api_key) as sandbox:
            execution = sandbox.run_code(code, timeout=timeout)

            output_parts = []
            if execution.logs.stdout:
                output_parts.append(f"STDOUT:\n{execution.logs.stdout}")
            if execution.logs.stderr:
                output_parts.append(f"STDERR:\n{execution.logs.stderr}")
            if execution.error:
                output_parts.append(f"ERROR:\n{execution.error}")
            if execution.results:
                output_parts.append(f"RESULT:\n{execution.results}")

            return "\n\n".join(output_parts) or "Code executed successfully with no output."

    except ImportError:
        return _execute_local_python(code, timeout)
    except Exception as e:
        return f"Error executing code in sandbox: {e}"


def _execute_local_python(code: str, timeout: int = 60) -> str:
    """Execute Python code locally (fallback when E2B not available).

    Args:
        code: Python code to execute.
        timeout: Maximum execution time in seconds.

    Returns:
        Execution output or error message.
    """
    import subprocess
    import tempfile
    from pathlib import Path

    # Write code to a temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_path = f.name

    try:
        result = subprocess.run(
            ["python", temp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output_parts = []
        if result.stdout:
            output_parts.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output_parts.append(f"STDERR:\n{result.stderr}")

        output = "\n\n".join(output_parts) or "Code executed successfully with no output."

        if result.returncode != 0:
            output = f"(Local execution) Exit code {result.returncode}\n\n{output}"
        else:
            output = "(Local execution - E2B not configured)\n\n" + output

        return output

    except subprocess.TimeoutExpired:
        return f"Error: Code execution timed out after {timeout} seconds"
    except Exception as e:
        return f"Error executing code locally: {e}"
    finally:
        # Clean up temp file
        Path(temp_path).unlink(missing_ok=True)


@tool("Install Python Package in Sandbox")
def install_package_sandbox(package: str) -> str:
    """Install a Python package in the E2B sandbox.

    Args:
        package: Package name to install (e.g., "requests" or "pandas==2.0.0").

    Returns:
        Installation result or error message.
    """
    code = f"""
import subprocess
result = subprocess.run(
    ["pip", "install", "{package}"],
    capture_output=True,
    text=True
)
print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
print("Return code:", result.returncode)
"""
    return execute_python_sandbox.func(code, timeout=120)


# Type alias for better readability
ToolFunc = Any

# Export all code execution tools
CODE_EXEC_TOOLS: list[ToolFunc] = [execute_python_sandbox, install_package_sandbox]
