"""Tests for the progress tracker."""

import tempfile
from pathlib import Path

from lloyd.memory.progress import ProgressTracker


def test_append_entry() -> None:
    """Test appending an entry to progress."""
    with tempfile.TemporaryDirectory() as tmpdir:
        progress_path = Path(tmpdir) / "progress.txt"
        tracker = ProgressTracker(progress_path)

        tracker.append("Test entry")

        content = tracker.read()
        assert "Test entry" in content


def test_append_with_section() -> None:
    """Test appending an entry with a section header."""
    with tempfile.TemporaryDirectory() as tmpdir:
        progress_path = Path(tmpdir) / "progress.txt"
        tracker = ProgressTracker(progress_path)

        tracker.append("Test entry", section="Test Section")

        content = tracker.read()
        assert "### Test Section" in content
        assert "Test entry" in content


def test_log_iteration() -> None:
    """Test logging an iteration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        progress_path = Path(tmpdir) / "progress.txt"
        tracker = ProgressTracker(progress_path)

        tracker.log_iteration(1, "Test Task", "PASSED", "Notes here")

        content = tracker.read()
        assert "Iteration 1" in content
        assert "Test Task" in content
        assert "PASSED" in content


def test_log_learning() -> None:
    """Test logging a learning."""
    with tempfile.TemporaryDirectory() as tmpdir:
        progress_path = Path(tmpdir) / "progress.txt"
        tracker = ProgressTracker(progress_path)

        tracker.log_learning("Important insight")

        content = tracker.read()
        assert "Learnings" in content
        assert "Important insight" in content


def test_start_session() -> None:
    """Test starting a new session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        progress_path = Path(tmpdir) / "progress.txt"
        tracker = ProgressTracker(progress_path)

        tracker.start_session("Test session description")

        content = tracker.read()
        assert "## Session:" in content
        assert "Test session description" in content


def test_get_recent_entries() -> None:
    """Test getting recent entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        progress_path = Path(tmpdir) / "progress.txt"
        tracker = ProgressTracker(progress_path)

        # Add multiple entries
        for i in range(5):
            tracker.append(f"Entry {i}")

        entries = tracker.get_recent_entries(3)
        assert len(entries) == 3


def test_clear() -> None:
    """Test clearing progress file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        progress_path = Path(tmpdir) / "progress.txt"
        progress_path.write_text("Some content")
        tracker = ProgressTracker(progress_path)

        tracker.clear()

        content = tracker.read()
        assert content == "# AEGIS Progress Log\n\n"
