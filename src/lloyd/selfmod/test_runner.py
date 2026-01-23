"""Test runner for self-modification validation."""

import subprocess
from pathlib import Path


class SelfModTestRunner:
    """Run tests to validate self-modifications."""

    def __init__(self, clone_path: Path):
        """Initialize the test runner.

        Args:
            clone_path: Path to the clone being tested
        """
        self.clone_path = clone_path

    def run_lint(self) -> tuple[bool, str]:
        """Run linting checks.

        Returns:
            (success, output)
        """
        try:
            result = subprocess.run(
                ["python", "-m", "ruff", "check", "src/lloyd"],
                cwd=self.clone_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)

    def run_import_check(self) -> tuple[bool, str]:
        """Check that imports work.

        Returns:
            (success, output)
        """
        try:
            result = subprocess.run(
                ["python", "-c", "import lloyd; print('OK')"],
                cwd=self.clone_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)

    def run_unit_tests(self) -> tuple[bool, str]:
        """Run unit tests.

        Returns:
            (success, output)
        """
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v", "--tb=short", "-x"],
                cwd=self.clone_path,
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)

    def test_cli(self) -> tuple[bool, str]:
        """Test CLI commands.

        Returns:
            (success, output)
        """
        results = []
        all_ok = True

        commands = [["lloyd", "--help"], ["lloyd", "inbox"], ["lloyd", "status"]]

        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd, cwd=self.clone_path, capture_output=True, text=True, timeout=10
                )
                icon = "OK" if result.returncode == 0 else "FAIL"
                results.append(f"{icon} {' '.join(cmd)}")
                if result.returncode != 0:
                    all_ok = False
            except Exception as e:
                results.append(f"FAIL {' '.join(cmd)}: {e}")
                all_ok = False

        return all_ok, "\n".join(results)

    def test_gui(self) -> tuple[bool, str]:
        """Test GUI imports.

        Returns:
            (success, output)
        """
        try:
            result = subprocess.run(
                ["python", "-c", "from lloyd.api import app; print('OK')"],
                cwd=self.clone_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)

    def run_smoke_test(self) -> tuple[bool, str]:
        """Run a smoke test (NEEDS GPU).

        Returns:
            (success, output)
        """
        try:
            result = subprocess.run(
                ["lloyd", "idea", "Add comment '# smoke' to main.py"],
                cwd=self.clone_path,
                capture_output=True,
                text=True,
                timeout=180,
            )
            return result.returncode == 0, result.stdout + result.stderr
        except Exception as e:
            return False, str(e)

    def run_safe_tests(self) -> dict[str, tuple[bool, str]]:
        """Run all tests that don't need GPU.

        Returns:
            Dictionary of test name to (success, output)
        """
        return {
            "lint": self.run_lint(),
            "imports": self.run_import_check(),
            "unit": self.run_unit_tests(),
            "cli": self.test_cli(),
            "gui": self.test_gui(),
        }

    def run_gpu_tests(self) -> dict[str, tuple[bool, str]]:
        """Run tests that need GPU.

        Returns:
            Dictionary of test name to (success, output)
        """
        return {"smoke": self.run_smoke_test()}

    def all_passed(self, results: dict[str, tuple[bool, str]]) -> bool:
        """Check if all tests passed.

        Args:
            results: Test results dictionary

        Returns:
            True if all tests passed
        """
        return all(r[0] for r in results.values())
