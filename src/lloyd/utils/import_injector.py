"""Import injection utility for fixing missing imports in generated code.

This module scans Python code for patterns that require specific imports
and automatically injects any missing imports at the top of the file.
It also handles common test patterns like FastAPI TestClient initialization.
"""

import re
from pathlib import Path


# Mapping of usage patterns to required imports
IMPORT_PATTERNS: dict[str, tuple[str, list[str]]] = {
    # json module
    r"\bjson\.(load|loads|dump|dumps|JSONDecodeError)\b": (
        "import json",
        [],
    ),
    # pytest
    r"\bpytest\.(raises|fixture|mark|param|skip|fail|approx)\b": (
        "import pytest",
        [],
    ),
    r"\bpytest\.raises\b": (
        "import pytest",
        [],
    ),
    # datetime module
    r"\bdatetime\.(datetime|date|time|timedelta|timezone)\b": (
        "from datetime import datetime, date, timedelta, timezone",
        [],
    ),
    r"\b(datetime|timedelta|timezone)\(": (
        "from datetime import datetime, date, timedelta, timezone",
        [],
    ),
    # typing module
    r"\b(List|Dict|Optional|Any|Tuple|Set|Union|Callable)\[": (
        "from typing import List, Dict, Optional, Any, Tuple, Set, Union, Callable",
        [],
    ),
    # os module
    r"\bos\.(path|environ|getcwd|listdir|makedirs|remove|rename)\b": (
        "import os",
        [],
    ),
    # pathlib
    r"\bPath\(": (
        "from pathlib import Path",
        [],
    ),
    # re module
    r"\bre\.(match|search|sub|compile|findall|split)\b": (
        "import re",
        [],
    ),
    # tempfile module
    r"\btempfile\.(NamedTemporaryFile|TemporaryDirectory|mktemp|mkdtemp)\b": (
        "import tempfile",
        [],
    ),
    # unittest.mock
    r"\b(Mock|MagicMock|patch|call)\(": (
        "from unittest.mock import Mock, MagicMock, patch, call",
        [],
    ),
    # uuid module
    r"\buuid\.(uuid4|uuid1|UUID)\b": (
        "import uuid",
        [],
    ),
    r"\buuid4\(\)": (
        "from uuid import uuid4",
        [],
    ),
    # collections
    r"\b(defaultdict|Counter|OrderedDict|deque)\(": (
        "from collections import defaultdict, Counter, OrderedDict, deque",
        [],
    ),
    # dataclasses
    r"@dataclass": (
        "from dataclasses import dataclass, field",
        [],
    ),
    # abc module
    r"\b(ABC|abstractmethod)\b": (
        "from abc import ABC, abstractmethod",
        [],
    ),
    # functools
    r"@(lru_cache|cached_property|wraps)": (
        "from functools import lru_cache, cached_property, wraps",
        [],
    ),
    # io module
    r"\b(StringIO|BytesIO)\(": (
        "from io import StringIO, BytesIO",
        [],
    ),
    # sys module
    r"\bsys\.(path|argv|exit|stdout|stderr)\b": (
        "import sys",
        [],
    ),
    # time module
    r"\btime\.(sleep|time|perf_counter)\b": (
        "import time",
        [],
    ),
    # httpx/requests for API testing
    r"\bhttpx\.(Client|AsyncClient|get|post)\b": (
        "import httpx",
        [],
    ),
    # FastAPI TestClient
    r"\bTestClient\(": (
        "from fastapi.testclient import TestClient",
        [],
    ),
    # pydantic
    r"\b(BaseModel|Field|validator)\b.*:": (
        "from pydantic import BaseModel, Field",
        [],
    ),
}


def detect_missing_imports(code: str) -> list[str]:
    """Detect imports that are used but not imported.

    Args:
        code: Python source code to analyze.

    Returns:
        List of import statements that should be added.
    """
    missing_imports: set[str] = set()

    # Get existing imports from the code
    existing_imports = set()
    for line in code.split("\n"):
        line = line.strip()
        if line.startswith("import ") or line.startswith("from "):
            existing_imports.add(line)

    # Check each pattern
    for pattern, (import_stmt, _) in IMPORT_PATTERNS.items():
        if re.search(pattern, code):
            # Check if this import already exists
            # Handle both "import X" and "from X import Y" cases
            import_module = import_stmt.split()[1]  # Get module name

            # Check if any existing import covers this
            already_imported = False
            for existing in existing_imports:
                if import_module in existing:
                    already_imported = True
                    break

            if not already_imported:
                missing_imports.add(import_stmt)

    return sorted(missing_imports)


def inject_imports(code: str, imports_to_add: list[str]) -> str:
    """Inject import statements at the top of the code.

    Args:
        code: Original Python source code.
        imports_to_add: List of import statements to add.

    Returns:
        Modified code with imports injected.
    """
    if not imports_to_add:
        return code

    lines = code.split("\n")

    # Find the right place to insert imports
    # After docstrings and existing imports, before other code
    insert_index = 0
    in_docstring = False
    docstring_char = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Handle docstrings
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                in_docstring = True
                docstring_char = stripped[:3]
                # Check if docstring ends on same line
                if stripped.count(docstring_char) >= 2:
                    in_docstring = False
                insert_index = i + 1
                continue
        else:
            if docstring_char in stripped:
                in_docstring = False
                insert_index = i + 1
                continue

        # Skip comments
        if stripped.startswith("#"):
            insert_index = i + 1
            continue

        # Skip empty lines at the top
        if not stripped and i < 5:
            insert_index = i + 1
            continue

        # Keep going past existing imports
        if stripped.startswith("import ") or stripped.startswith("from "):
            insert_index = i + 1
            continue

        # Found non-import code, stop here
        break

    # Build the new import section
    import_section = "\n".join(imports_to_add)

    # Insert imports
    if insert_index == 0:
        new_code = import_section + "\n\n" + code
    else:
        before = "\n".join(lines[:insert_index])
        after = "\n".join(lines[insert_index:])

        # Avoid double newlines
        if before.endswith("\n"):
            new_code = before + import_section + "\n" + after
        else:
            new_code = before + "\n" + import_section + "\n" + after

    return new_code


def fix_imports(code: str) -> tuple[str, list[str]]:
    """Detect and fix missing imports in Python code.

    Args:
        code: Python source code to fix.

    Returns:
        Tuple of (fixed_code, list_of_added_imports).
    """
    missing = detect_missing_imports(code)

    if not missing:
        return code, []

    fixed_code = inject_imports(code, missing)
    return fixed_code, missing


def fix_testclient_pattern(code: str) -> tuple[str, list[str]]:
    """Fix missing FastAPI TestClient initialization.

    Detects when code uses 'client.get()', 'client.post()' etc. without
    defining 'client = TestClient(app)' and fixes it.

    Args:
        code: Python source code.

    Returns:
        Tuple of (fixed_code, list_of_fixes_applied).
    """
    fixes_applied = []

    # Check if code uses client.get/post/put/delete/patch without defining client
    client_usage = re.search(r"\bclient\.(get|post|put|delete|patch)\(", code)
    client_defined = re.search(r"\bclient\s*=\s*(TestClient|httpx\.|requests\.)", code)

    if client_usage and not client_defined:
        # Need to add TestClient initialization
        # First, find what app/module to import from

        # Look for existing imports to determine the main module
        main_module = None
        impl_import = re.search(r"from\s+(\w+)\s+import", code)
        if impl_import:
            main_module = impl_import.group(1)
        else:
            # Default to common names
            main_module = "main"

        # Build the fixes
        testclient_import = "from fastapi.testclient import TestClient"
        app_import = f"from {main_module} import app"
        client_init = "client = TestClient(app)"

        # Check what's already there
        if "from fastapi.testclient import TestClient" not in code:
            fixes_applied.append(testclient_import)

        if f"from {main_module} import" in code:
            # Already imports from the module, check if 'app' is included
            import_match = re.search(
                rf"from\s+{main_module}\s+import\s+([^#\n]+)", code
            )
            if import_match:
                imported_items = import_match.group(1)
                if "app" not in imported_items:
                    # Add app to existing import
                    new_import = f"from {main_module} import {imported_items.strip()}, app"
                    code = code.replace(import_match.group(0), new_import)
                    fixes_applied.append(f"Added 'app' to {main_module} import")
        else:
            # Need to add the import entirely
            fixes_applied.append(app_import)

        if "client = TestClient" not in code and "client=TestClient" not in code:
            fixes_applied.append(client_init)

        # Now inject the fixes
        if fixes_applied:
            lines = code.split("\n")

            # Find where to insert
            insert_index = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    insert_index = i + 1
                elif stripped and not stripped.startswith("#"):
                    break

            # Build injection block
            injection_lines = []
            for fix in fixes_applied:
                if fix.startswith("from ") or fix.startswith("import "):
                    injection_lines.append(fix)
                elif fix.startswith("client ="):
                    # Add after a blank line
                    if injection_lines:
                        injection_lines.append("")
                    injection_lines.append(fix)
                    injection_lines.append("")

            if injection_lines:
                # Insert the lines
                for j, inj_line in enumerate(injection_lines):
                    lines.insert(insert_index + j, inj_line)

                code = "\n".join(lines)

    return code, fixes_applied


def fix_file_imports(file_path: Path) -> list[str]:
    """Fix missing imports in a Python file.

    Args:
        file_path: Path to the Python file.

    Returns:
        List of imports that were added.
    """
    if not file_path.exists():
        return []

    code = file_path.read_text(encoding="utf-8")

    # First fix standard imports
    fixed_code, added_imports = fix_imports(code)

    # Then fix TestClient pattern if this looks like a test file
    if file_path.name.startswith("test_"):
        fixed_code, testclient_fixes = fix_testclient_pattern(fixed_code)
        added_imports.extend(testclient_fixes)

    if added_imports:
        file_path.write_text(fixed_code, encoding="utf-8")

    return added_imports
