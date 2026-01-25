"""Filesystem tools for Lloyd agents."""

import os
from pathlib import Path

from crewai.tools import tool

# Protected paths that Lloyd should never modify (its own source code)
PROTECTED_PATHS = [
    "src/lloyd",
    "src\\lloyd",
    "lloyd/src/lloyd",
    "lloyd\\src\\lloyd",
]

# Sensitive files that should never be read or written
SENSITIVE_PATTERNS = [
    ".env",
    ".env.local",
    ".env.production",
    "credentials",
    "secret",
    "private_key",
    "id_rsa",
    "id_ed25519",
    ".ssh/",
    ".aws/",
    ".gnupg/",
]

# Maximum directory listing size to prevent memory issues
MAX_DIRECTORY_ENTRIES = 1000

# Maximum file size to read (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


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


def _is_sensitive_path(file_path: str) -> bool:
    """Check if a path contains sensitive data that shouldn't be accessed.

    Args:
        file_path: Path to check.

    Returns:
        True if the path may contain sensitive data.
    """
    path_lower = file_path.lower().replace("\\", "/")
    for pattern in SENSITIVE_PATTERNS:
        if pattern in path_lower:
            return True
    return False


def _is_path_traversal(file_path: str, base_dir: Path | None = None) -> bool:
    """Check for path traversal attacks.

    Args:
        file_path: Path to check.
        base_dir: Optional base directory to check against.

    Returns:
        True if path traversal is detected.
    """
    try:
        resolved = Path(file_path).resolve()

        # Check for suspicious patterns
        path_str = str(file_path)
        if ".." in path_str:
            # Allow relative paths within reasonable bounds
            # but reject obvious traversal attempts
            if path_str.count("..") > 3:
                return True
            # Reject paths going to system directories
            resolved_str = str(resolved).lower()
            dangerous_dirs = ["/etc", "/usr", "/bin", "/sbin", "\\windows", "\\system32"]
            for dangerous in dangerous_dirs:
                if dangerous in resolved_str:
                    return True

        # If base_dir is provided, ensure path stays within it
        if base_dir:
            base_resolved = base_dir.resolve()
            try:
                resolved.relative_to(base_resolved)
            except ValueError:
                return True

        return False
    except (OSError, ValueError):
        return True


def _validate_path_security(file_path: str, operation: str = "access") -> str | None:
    """Validate path security for read/write operations.

    Args:
        file_path: Path to validate.
        operation: Type of operation (read/write/delete).

    Returns:
        Error message if validation fails, None if path is safe.
    """
    if _is_path_traversal(file_path):
        return f"Error: Path traversal detected in '{file_path}'. Access denied."

    if _is_sensitive_path(file_path):
        return f"Error: Cannot {operation} sensitive file '{file_path}'. Access denied."

    if operation in ("write", "delete") and _is_protected_path(file_path):
        return f"Error: Cannot {operation} Lloyd's source files. Path '{file_path}' is protected."

    return None


@tool("Read File")
def read_file(file_path: str) -> str:
    """Read the contents of a file.

    Args:
        file_path: Path to the file to read.

    Returns:
        Contents of the file as a string.
    """
    # Security validation
    security_error = _validate_path_security(file_path, "read")
    if security_error:
        return security_error

    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found: {file_path}"
    if not path.is_file():
        return f"Error: Path is not a file: {file_path}"

    # Check file size to prevent memory issues
    try:
        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return f"Error: File too large ({file_size} bytes). Maximum allowed: {MAX_FILE_SIZE} bytes."
    except OSError as e:
        return f"Error checking file size: {e}"

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"Error: Unable to read file as text: {file_path}"
    except PermissionError:
        return f"Error: Permission denied reading file: {file_path}"
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
    # Security validation (includes protected path check)
    security_error = _validate_path_security(file_path, "write")
    if security_error:
        return security_error

    path = Path(file_path)

    try:
        # Create parent directories if they don't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} bytes to {file_path}"
    except PermissionError:
        return f"Error: Permission denied writing to: {file_path}"
    except OSError as e:
        return f"Error writing file (OS error): {e}"
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
    # Security validation
    security_error = _validate_path_security(dir_path, "read")
    if security_error:
        return security_error

    path = Path(dir_path)
    if not path.exists():
        return f"Error: Directory not found: {dir_path}"
    if not path.is_dir():
        return f"Error: Path is not a directory: {dir_path}"

    try:
        entries = []
        entry_count = 0
        for entry in sorted(path.iterdir()):
            entry_count += 1
            if entry_count > MAX_DIRECTORY_ENTRIES:
                entries.append(f"... (truncated, {entry_count}+ entries)")
                break

            entry_type = "DIR" if entry.is_dir() else "FILE"
            try:
                size = entry.stat().st_size if entry.is_file() else "-"
            except (OSError, PermissionError):
                size = "?"
            entries.append(f"{entry_type}\t{size}\t{entry.name}")

        if not entries:
            return f"Directory is empty: {dir_path}"

        return "\n".join(entries)
    except PermissionError:
        return f"Error: Permission denied accessing directory: {dir_path}"
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
    # Security validation (includes protected path check)
    security_error = _validate_path_security(file_path, "delete")
    if security_error:
        return security_error

    path = Path(file_path)

    if not path.exists():
        return f"Error: File not found: {file_path}"
    if not path.is_file():
        return f"Error: Path is not a file: {file_path}"

    try:
        path.unlink()
        return f"Successfully deleted: {file_path}"
    except PermissionError:
        return f"Error: Permission denied deleting: {file_path}"
    except Exception as e:
        return f"Error deleting file: {e}"


# Export all filesystem tools
FILESYSTEM_TOOLS = [read_file, write_file, list_directory, create_directory, delete_file]
