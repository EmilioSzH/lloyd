"""Tests for AEGIS tools."""

import tempfile
from pathlib import Path

from lloyd.tools.filesystem import (
    create_directory,
    delete_file,
    list_directory,
    read_file,
    write_file,
)


def test_read_file() -> None:
    """Test reading a file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test content")
        temp_path = f.name

    try:
        result = read_file.func(temp_path)
        assert "Test content" in result
    finally:
        Path(temp_path).unlink()


def test_read_file_not_found() -> None:
    """Test reading a non-existent file."""
    result = read_file.func("/nonexistent/file.txt")
    assert "Error" in result or "not found" in result.lower()


def test_write_file() -> None:
    """Test writing a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = Path(tmpdir) / "test.txt"

        result = write_file.func(str(file_path), "Test content")

        assert "Successfully" in result
        assert file_path.read_text() == "Test content"


def test_list_directory() -> None:
    """Test listing a directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create some files
        (Path(tmpdir) / "file1.txt").write_text("test")
        (Path(tmpdir) / "file2.txt").write_text("test")
        (Path(tmpdir) / "subdir").mkdir()

        result = list_directory.func(tmpdir)

        assert "file1.txt" in result
        assert "file2.txt" in result
        assert "subdir" in result


def test_create_directory() -> None:
    """Test creating a directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        new_dir = Path(tmpdir) / "new" / "nested" / "dir"

        result = create_directory.func(str(new_dir))

        assert "Successfully" in result
        assert new_dir.exists()


def test_delete_file() -> None:
    """Test deleting a file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Test content")
        temp_path = f.name

    result = delete_file.func(temp_path)

    assert "Successfully" in result
    assert not Path(temp_path).exists()
