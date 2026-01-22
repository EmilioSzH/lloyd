"""Filesystem tools for Lloyd agents."""

from pathlib import Path

from crewai.tools import tool

# Protected paths that Lloyd should never modify (its own source code)
PROTECTED_PATHS = [
    "src/lloyd",
    "src\\lloyd",
    "lloyd/src/lloyd",
    "lloyd\\src\\lloyd",
]


def _is_protected_path(file_path: str) -> bool:
    """Check if a path is within Lloyd's protected source directories.

    Args:
        file_path: Path to check.

    Returns:
        True if the path is protected and should not be modified.
    """
    path_str = str(Path(file_path).resolve()).replace("\\", "/").lower()
    for protected in PROTECTED_PATHS:
        if protected.replace("\\", "/").lower() in path_str:
            return True
    return False


@tool("Read File")
def read_file(file_path: str) -> str:
    """Read the contents of a file.

    Args:
        file_path: Path to the file to read.

    Returns:
        Contents of the file as a string.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"
    if not path.is_file():
        return f"Error: Path is not a file: {file_path}"

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Error: Unable to read file as text: {file_path}"
    except Exception as e:
        return f"Error reading file: {e}"


@tool("Write File")
def write_file(file_path: str, content: str) -> str:
    """Write content to a file.

    Args:
        file_path: Path to the file to write.
        content: Content to write to the file.

    Returns:
        Success message or error description.
    """
    # SAFETY: Prevent Lloyd from modifying its own source code
    if _is_protected_path(file_path):
        return f"Error: Cannot modify Lloyd's source files. Path '{file_path}' is protected."

    path = Path(file_path)

    try:
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} bytes to {file_path}"
    except Exception as e:
        return f"Error writing file: {e}"


@tool("List Directory")
def list_directory(dir_path: str = ".") -> str:
    """List contents of a directory.

    Args:
        dir_path: Path to the directory to list. Defaults to current directory.

    Returns:
        Directory listing as a formatted string.
    """
    path = Path(dir_path)
    if not path.exists():
        return f"Error: Directory not found: {dir_path}"
    if not path.is_dir():
        return f"Error: Path is not a directory: {dir_path}"

    try:
        entries = []
        for entry in sorted(path.iterdir()):
            entry_type = "DIR" if entry.is_dir() else "FILE"
            size = entry.stat().st_size if entry.is_file() else "-"
            entries.append(f"{entry_type}\t{size}\t{entry.name}")

        if not entries:
            return f"Directory is empty: {dir_path}"

        return "\n".join(entries)
    except Exception as e:
        return f"Error listing directory: {e}"


@tool("Create Directory")
def create_directory(dir_path: str) -> str:
    """Create a directory (including parent directories).

    Args:
        dir_path: Path to the directory to create.

    Returns:
        Success message or error description.
    """
    path = Path(dir_path)

    try:
        path.mkdir(parents=True, exist_ok=True)
        return f"Successfully created directory: {dir_path}"
    except Exception as e:
        return f"Error creating directory: {e}"


@tool("Delete File")
def delete_file(file_path: str) -> str:
    """Delete a file.

    Args:
        file_path: Path to the file to delete.

    Returns:
        Success message or error description.
    """
    # SAFETY: Prevent Lloyd from deleting its own source code
    if _is_protected_path(file_path):
        return f"Error: Cannot delete Lloyd's source files. Path '{file_path}' is protected."

    path = Path(file_path)

    if not path.exists():
        return f"Error: File not found: {file_path}"
    if not path.is_file():
        return f"Error: Path is not a file: {file_path}"

    try:
        path.unlink()
        return f"Successfully deleted: {file_path}"
    except Exception as e:
        return f"Error deleting file: {e}"


# Export all filesystem tools
FILESYSTEM_TOOLS = [read_file, write_file, list_directory, create_directory, delete_file]
