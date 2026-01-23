"""Manage Lloyd clones for safe self-modification."""

import shutil
import subprocess
from pathlib import Path


class LloydCloneManager:
    """Manage isolated clones of Lloyd for safe modifications."""

    def __init__(self, lloyd_root: Path | None = None):
        """Initialize the clone manager.

        Args:
            lloyd_root: Root directory of Lloyd. Defaults to cwd.
        """
        self.lloyd_root = lloyd_root or Path.cwd()
        self.clones_dir = self.lloyd_root.parent / "lloyd-clones"

    def create_clone(self, task_id: str) -> Path:
        """Create an isolated clone for modification.

        Args:
            task_id: Unique identifier for this modification task

        Returns:
            Path to the clone directory
        """
        self.clones_dir.mkdir(exist_ok=True)
        clone_path = self.clones_dir / f"lloyd-{task_id}"

        try:
            # Try git worktree first (more efficient)
            subprocess.run(
                ["git", "worktree", "add", str(clone_path), "-b", f"self-mod/{task_id}"],
                cwd=self.lloyd_root,
                check=True,
                capture_output=True,
            )
        except Exception:
            # Fall back to full copy
            if clone_path.exists():
                shutil.rmtree(clone_path)
            shutil.copytree(
                self.lloyd_root,
                clone_path,
                ignore=shutil.ignore_patterns(
                    ".git", "__pycache__", "*.pyc", ".venv", "node_modules"
                ),
            )

        return clone_path

    def get_clone_path(self, task_id: str) -> Path:
        """Get the path to a clone.

        Args:
            task_id: Task identifier

        Returns:
            Path to clone directory
        """
        return self.clones_dir / f"lloyd-{task_id}"

    def merge_clone(self, task_id: str) -> bool:
        """Merge changes from clone back to main.

        Args:
            task_id: Task identifier

        Returns:
            True if merge succeeded
        """
        clone = self.get_clone_path(task_id)

        try:
            # Stage and commit changes in clone
            subprocess.run(["git", "add", "-A"], cwd=clone, check=True)
            subprocess.run(
                ["git", "commit", "-m", f"self-mod: {task_id}"], cwd=clone, capture_output=True
            )

            # Merge to main
            subprocess.run(["git", "checkout", "main"], cwd=self.lloyd_root, check=True)
            result = subprocess.run(
                ["git", "merge", f"self-mod/{task_id}", "--no-edit"], cwd=self.lloyd_root
            )
            return result.returncode == 0
        except Exception:
            return False

    def cleanup_clone(self, task_id: str) -> None:
        """Remove a clone after merge or rejection.

        Args:
            task_id: Task identifier
        """
        clone = self.get_clone_path(task_id)

        try:
            # Try git worktree removal first
            subprocess.run(
                ["git", "worktree", "remove", str(clone), "--force"],
                cwd=self.lloyd_root,
                capture_output=True,
            )
            subprocess.run(
                ["git", "branch", "-D", f"self-mod/{task_id}"],
                cwd=self.lloyd_root,
                capture_output=True,
            )
        except Exception:
            pass

        # Fall back to direct deletion
        if clone.exists():
            shutil.rmtree(clone)

    def get_diff(self, task_id: str) -> str:
        """Get a summary diff of changes in the clone.

        Args:
            task_id: Task identifier

        Returns:
            Diff summary string
        """
        result = subprocess.run(
            ["git", "diff", "main", "--stat"],
            cwd=self.get_clone_path(task_id),
            capture_output=True,
            text=True,
        )
        return result.stdout

    def get_full_diff(self, task_id: str) -> str:
        """Get the full diff of changes.

        Args:
            task_id: Task identifier

        Returns:
            Full diff string
        """
        result = subprocess.run(
            ["git", "diff", "main"],
            cwd=self.get_clone_path(task_id),
            capture_output=True,
            text=True,
        )
        return result.stdout
