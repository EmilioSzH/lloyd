"""Progress tracking for AEGIS."""

import gzip
import shutil
from datetime import UTC, datetime
from pathlib import Path


class ProgressTracker:
    """Tracks and persists progress/learnings across iterations."""

    # Log rotation settings
    MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5MB
    MAX_ARCHIVES = 10

    def __init__(self, progress_path: str | Path = ".aegis/progress.txt") -> None:
        """Initialize progress tracker.

        Args:
            progress_path: Path to the progress file.
        """
        self.progress_path = Path(progress_path)
        self.archive_dir = self.progress_path.parent / "progress_archive"

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

        # Check for rotation before writing
        self._check_and_rotate()

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

    def _check_and_rotate(self) -> bool:
        """Check file size and rotate if needed.

        Returns:
            True if rotation occurred.
        """
        if not self.progress_path.exists():
            return False

        file_size = self.progress_path.stat().st_size
        if file_size < self.MAX_SIZE_BYTES:
            return False

        # Perform rotation
        self._rotate_log()
        return True

    def _rotate_log(self) -> None:
        """Rotate the current log to archive and start fresh."""
        # Ensure archive directory exists
        self.archive_dir.mkdir(parents=True, exist_ok=True)

        # Generate archive filename with timestamp
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        archive_name = f"progress_{timestamp}.txt.gz"
        archive_path = self.archive_dir / archive_name

        # Compress and archive current log
        with open(self.progress_path, "rb") as f_in:
            with gzip.open(archive_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        # Clear current log with continuation note
        self.progress_path.write_text(
            f"# AEGIS Progress Log (continued)\n"
            f"# Previous entries archived to: {archive_name}\n\n",
            encoding="utf-8",
        )

        # Clean up old archives
        self._cleanup_old_archives()

    def _cleanup_old_archives(self) -> None:
        """Keep only the last MAX_ARCHIVES archives."""
        if not self.archive_dir.exists():
            return

        # Get all archive files sorted by modification time (oldest first)
        archives = sorted(
            self.archive_dir.glob("progress_*.txt.gz"),
            key=lambda p: p.stat().st_mtime,
        )

        # Remove old archives beyond the limit
        while len(archives) > self.MAX_ARCHIVES:
            oldest = archives.pop(0)
            oldest.unlink()

    def get_archive_list(self) -> list[dict]:
        """Get list of archived logs.

        Returns:
            List of archive info dicts with name and timestamp.
        """
        if not self.archive_dir.exists():
            return []

        archives = []
        for archive in sorted(self.archive_dir.glob("progress_*.txt.gz")):
            archives.append({
                "name": archive.name,
                "path": str(archive),
                "size": archive.stat().st_size,
                "modified": datetime.fromtimestamp(archive.stat().st_mtime, UTC),
            })

        return archives

    def read_archive(self, archive_name: str) -> str:
        """Read a specific archived log.

        Args:
            archive_name: Name of the archive file.

        Returns:
            Decompressed contents of the archive.
        """
        archive_path = self.archive_dir / archive_name
        if not archive_path.exists():
            return ""

        with gzip.open(archive_path, "rt", encoding="utf-8") as f:
            return f.read()
