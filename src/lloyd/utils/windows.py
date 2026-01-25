"""Windows compatibility utilities.

This module provides centralized Windows-specific functionality to avoid
code duplication across the codebase.
"""

import logging
import os
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Reserved Windows filenames
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

# Invalid characters in Windows filenames
WINDOWS_INVALID_CHARS = r'[<>:"/\\|?*]'


def configure_console() -> None:
    """Configure console for UTF-8 encoding on Windows.

    This should be called early in application startup to ensure
    Unicode characters (including emojis) display correctly.

    On non-Windows platforms, this is a no-op.
    """
    if sys.platform != "win32":
        return

    # Set UTF-8 encoding for Python I/O
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    # Try to enable UTF-8 mode on Windows console
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        # Python versions < 3.7 don't have reconfigure
        logger.debug("Console reconfigure not available (Python < 3.7)")
    except Exception as e:
        logger.warning(f"Failed to configure Windows console encoding: {e}")


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for Windows compatibility.

    Args:
        filename: The filename to sanitize.

    Returns:
        Sanitized filename safe for Windows filesystem.
    """
    # Remove or replace invalid Windows filename characters
    sanitized = re.sub(WINDOWS_INVALID_CHARS, "_", filename)

    # Remove control characters (ASCII < 32)
    sanitized = "".join(c for c in sanitized if ord(c) >= 32)

    # Ensure it doesn't start/end with spaces or dots
    sanitized = sanitized.strip(". ")

    # Handle reserved Windows names
    name_without_ext = sanitized.split(".")[0].upper()
    if name_without_ext in WINDOWS_RESERVED_NAMES:
        sanitized = f"_{sanitized}"

    return sanitized or "unnamed"


def safe_write_text(path: Path, content: str) -> None:
    """Write text to a file with Windows-safe encoding handling.

    Args:
        path: Path to write to.
        content: Content to write.
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Sanitize the filename portion
    sanitized_name = sanitize_filename(path.name)
    safe_path = path.parent / sanitized_name

    # Replace problematic characters in content
    safe_content = content.encode("utf-8", errors="replace").decode("utf-8")

    # Write with explicit encoding and error handling
    try:
        with open(safe_path, "w", encoding="utf-8", errors="replace", newline="\n") as f:
            f.write(safe_content)
    except OSError as e:
        # If still failing, try with more aggressive sanitization
        logger.warning(f"Failed to write to {safe_path}: {e}")
        # Try replacing all non-ASCII characters in filename
        ascii_name = "".join(c if ord(c) < 128 else "_" for c in sanitized_name)
        fallback_path = path.parent / ascii_name
        with open(fallback_path, "w", encoding="utf-8", errors="replace", newline="\n") as f:
            f.write(safe_content)


def is_windows() -> bool:
    """Check if running on Windows.

    Returns:
        True if running on Windows, False otherwise.
    """
    return sys.platform == "win32"
