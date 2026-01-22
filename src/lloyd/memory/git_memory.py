"""Git-based memory and persistence for AEGIS."""

import subprocess
from pathlib import Path


class GitMemory:
    """Git-based persistence for AEGIS state."""

    def __init__(self, repo_path: str | Path = ".") -> None:
        """Initialize git memory.

        Args:
            repo_path: Path to the git repository.
        """
        self.repo_path = Path(repo_path)

    def _run_git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run a git command.

        Args:
            *args: Git command arguments.
            check: Whether to raise on non-zero exit.

        Returns:
            Completed process result.
        """
        return subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=check,
        )

    def is_git_repo(self) -> bool:
        """Check if the current directory is a git repository.

        Returns:
            True if in a git repo, False otherwise.
        """
        result = self._run_git("rev-parse", "--git-dir", check=False)
        return result.returncode == 0

    def init_repo(self) -> bool:
        """Initialize a git repository if not exists.

        Returns:
            True if repo was initialized or already exists.
        """
        if self.is_git_repo():
            return True

        result = self._run_git("init", check=False)
        return result.returncode == 0

    def get_current_branch(self) -> str | None:
        """Get the current branch name.

        Returns:
            Branch name or None if not in a repo.
        """
        result = self._run_git("rev-parse", "--abbrev-ref", "HEAD", check=False)
        if result.returncode == 0:
            return result.stdout.strip()
        return None

    def create_branch(self, branch_name: str, checkout: bool = True) -> bool:
        """Create a new branch.

        Args:
            branch_name: Name for the new branch.
            checkout: Whether to checkout the branch after creation.

        Returns:
            True if successful.
        """
        result = self._run_git("checkout", "-b", branch_name, check=False)
        if result.returncode != 0 and checkout:
            # Branch might exist, try to checkout
            result = self._run_git("checkout", branch_name, check=False)
        return result.returncode == 0

    def checkout_branch(self, branch_name: str) -> bool:
        """Checkout an existing branch.

        Args:
            branch_name: Branch to checkout.

        Returns:
            True if successful.
        """
        result = self._run_git("checkout", branch_name, check=False)
        return result.returncode == 0

    def commit(self, message: str, add_all: bool = True) -> bool:
        """Create a commit.

        Args:
            message: Commit message.
            add_all: Whether to add all changes before committing.

        Returns:
            True if commit was created.
        """
        if add_all:
            self._run_git("add", "-A", check=False)

        result = self._run_git("commit", "-m", message, check=False)
        return result.returncode == 0

    def get_recent_commits(self, count: int = 10) -> list[dict[str, str]]:
        """Get recent commit information.

        Args:
            count: Number of commits to retrieve.

        Returns:
            List of commit dictionaries with hash, message, and date.
        """
        result = self._run_git(
            "log",
            f"-{count}",
            "--pretty=format:%H|%s|%ai",
            check=False,
        )

        if result.returncode != 0:
            return []

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append(
                    {
                        "hash": parts[0],
                        "message": parts[1],
                        "date": parts[2],
                    }
                )
        return commits

    def get_diff(self, staged: bool = False) -> str:
        """Get the current diff.

        Args:
            staged: Whether to get staged changes only.

        Returns:
            Diff output as string.
        """
        args = ["diff"]
        if staged:
            args.append("--staged")

        result = self._run_git(*args, check=False)
        return result.stdout

    def get_status(self) -> str:
        """Get git status.

        Returns:
            Status output as string.
        """
        result = self._run_git("status", "--short", check=False)
        return result.stdout

    def has_uncommitted_changes(self) -> bool:
        """Check if there are uncommitted changes.

        Returns:
            True if there are uncommitted changes.
        """
        status = self.get_status()
        return bool(status.strip())

    def stash(self, message: str = "AEGIS auto-stash") -> bool:
        """Stash current changes.

        Args:
            message: Stash message.

        Returns:
            True if stash was created.
        """
        result = self._run_git("stash", "push", "-m", message, check=False)
        return result.returncode == 0

    def stash_pop(self) -> bool:
        """Pop the most recent stash.

        Returns:
            True if successful.
        """
        result = self._run_git("stash", "pop", check=False)
        return result.returncode == 0

    def reset_hard(self, ref: str = "HEAD") -> bool:
        """Hard reset to a reference.

        Args:
            ref: Git reference to reset to.

        Returns:
            True if successful.
        """
        result = self._run_git("reset", "--hard", ref, check=False)
        return result.returncode == 0

    def get_file_at_ref(self, file_path: str, ref: str = "HEAD") -> str | None:
        """Get file contents at a specific ref.

        Args:
            file_path: Path to the file.
            ref: Git reference (commit, branch, tag).

        Returns:
            File contents or None if not found.
        """
        result = self._run_git("show", f"{ref}:{file_path}", check=False)
        if result.returncode == 0:
            return result.stdout
        return None

    def create_story_branch(self, story_id: str, base: str = "main") -> str | None:
        """Create a branch for a story.

        Args:
            story_id: The story ID to use in branch name.
            base: Base branch to branch from.

        Returns:
            Branch name if successful, None otherwise.
        """
        branch_name = f"lloyd/{story_id}"

        # Try to checkout base first
        base_result = self._run_git("checkout", base, check=False)
        if base_result.returncode != 0:
            # Base branch might not exist, try current branch
            pass

        # Create and checkout new branch
        result = self._run_git("checkout", "-b", branch_name, check=False)
        if result.returncode == 0:
            return branch_name

        # Branch might already exist, try to checkout
        result = self._run_git("checkout", branch_name, check=False)
        if result.returncode == 0:
            return branch_name

        return None

    def create_pull_request(
        self, title: str, body: str, draft: bool = False
    ) -> str | None:
        """Create a PR using gh CLI.

        Args:
            title: PR title.
            body: PR body/description.
            draft: Whether to create as draft.

        Returns:
            PR URL if successful, None otherwise.
        """
        try:
            cmd = ["gh", "pr", "create", "--title", title, "--body", body]
            if draft:
                cmd.append("--draft")
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except FileNotFoundError:
            print("Warning: gh CLI not installed, skipping PR creation")
            return None
        except subprocess.CalledProcessError as e:
            print(f"Warning: PR creation failed: {e.stderr}")
            return None

    def commit_all(self, message: str) -> bool:
        """Stage and commit all changes.

        Args:
            message: Commit message.

        Returns:
            True if commit was created.
        """
        self._run_git("add", "-A", check=False)
        result = self._run_git("commit", "-m", message, check=False)
        return result.returncode == 0

    def push(self, set_upstream: bool = False) -> bool:
        """Push current branch to remote.

        Args:
            set_upstream: Whether to set upstream tracking.

        Returns:
            True if successful.
        """
        if set_upstream:
            branch = self.get_current_branch()
            if branch:
                result = self._run_git("push", "-u", "origin", branch, check=False)
            else:
                return False
        else:
            result = self._run_git("push", check=False)
        return result.returncode == 0
