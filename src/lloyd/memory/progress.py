"""Progress tracking for AEGIS."""

from datetime import UTC, datetime
from pathlib import Path


class ProgressTracker:
    """Tracks and persists progress/learnings across iterations."""

    def __init__(self, progress_path: str | Path = ".aegis/progress.txt") -> None:
        """Initialize progress tracker.

        Args:
            progress_path: Path to the progress file.
        """
        self.progress_path = Path(progress_path)

    def read(self) -> str:
        """Read the current progress file.

        Returns:
            Contents of the progress file, or empty string if not found.
        """
        if not self.progress_path.exists():
            return ""
        return self.progress_path.read_text(encoding="utf-8")

    def append(self, entry: str, section: str | None = None) -> None:
        """Append an entry to the progress file.

        Args:
            entry: Text to append.
            section: Optional section header.
        """
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        content = self.read()

        if section:
            new_entry = f"\n### {section}\n- [{timestamp}] {entry}\n"
        else:
            new_entry = f"\n- [{timestamp}] {entry}"

        content += new_entry

        self.progress_path.write_text(content, encoding="utf-8")

    def log_iteration(
        self,
        iteration: int,
        task: str,
        status: str,
        notes: str = "",
    ) -> None:
        """Log an iteration result.

        Args:
            iteration: Iteration number.
            task: Task that was worked on.
            status: Result status (PASSED, FAILED, BLOCKED, etc.).
            notes: Additional notes.
        """
        entry = f"Iteration {iteration} - Task: {task} - Status: {status}"
        if notes:
            entry += f"\n  Notes: {notes}"

        self.append(entry, section=f"Iteration {iteration}")

    def log_learning(self, learning: str) -> None:
        """Log a learning/insight.

        Args:
            learning: The learning or insight to record.
        """
        self.append(learning, section="Learnings")

    def log_error(self, error: str, context: str = "") -> None:
        """Log an error.

        Args:
            error: Error message.
            context: Additional context about the error.
        """
        entry = f"ERROR: {error}"
        if context:
            entry += f"\n  Context: {context}"

        self.append(entry, section="Errors")

    def start_session(self, description: str = "") -> None:
        """Mark the start of a new session.

        Args:
            description: Optional session description.
        """
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)

        date = datetime.now(UTC).strftime("%Y-%m-%d")
        header = f"\n\n## Session: {date}"
        if description:
            header += f"\n{description}"
        header += "\n"

        content = self.read()
        content += header
        self.progress_path.write_text(content, encoding="utf-8")

    def get_recent_entries(self, count: int = 10) -> list[str]:
        """Get the most recent entries.

        Args:
            count: Number of entries to retrieve.

        Returns:
            List of recent entries.
        """
        content = self.read()
        lines = content.split("\n")

        # Find lines that start with "- [" (timestamped entries)
        entries = [line for line in lines if line.strip().startswith("- [")]

        return entries[-count:] if len(entries) > count else entries

    def clear(self) -> None:
        """Clear the progress file (use with caution)."""
        if self.progress_path.exists():
            self.progress_path.write_text("# AEGIS Progress Log\n\n", encoding="utf-8")
