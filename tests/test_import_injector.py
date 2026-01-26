"""Tests for the import injection utility."""

import tempfile
from pathlib import Path

import pytest

from lloyd.utils.import_injector import (
    detect_missing_imports,
    fix_file_imports,
    fix_imports,
    fix_testclient_pattern,
    inject_imports,
)


class TestDetectMissingImports:
    """Tests for detecting missing imports."""

    def test_detect_json_usage(self):
        """Detect json module usage."""
        code = """
def load_config(path):
    with open(path) as f:
        return json.load(f)
"""
        missing = detect_missing_imports(code)
        assert "import json" in missing

    def test_detect_pytest_usage(self):
        """Detect pytest usage."""
        code = """
def test_raises_error():
    with pytest.raises(ValueError):
        raise ValueError("test")
"""
        missing = detect_missing_imports(code)
        assert "import pytest" in missing

    def test_detect_datetime_usage(self):
        """Detect datetime module usage."""
        code = """
def get_now():
    return datetime.datetime.now()
"""
        missing = detect_missing_imports(code)
        assert any("datetime" in imp for imp in missing)

    def test_detect_typing_usage(self):
        """Detect typing module usage."""
        code = """
def process(items: List[str]) -> Dict[str, Any]:
    pass
"""
        missing = detect_missing_imports(code)
        assert any("typing" in imp for imp in missing)

    def test_no_duplicate_when_already_imported(self):
        """Don't add import if already present."""
        code = """
import json

def load_config(path):
    return json.load(open(path))
"""
        missing = detect_missing_imports(code)
        assert "import json" not in missing

    def test_detect_testclient_usage(self):
        """Detect FastAPI TestClient usage."""
        code = """
client = TestClient(app)

def test_api():
    response = client.get("/")
"""
        missing = detect_missing_imports(code)
        assert "from fastapi.testclient import TestClient" in missing

    def test_detect_path_usage(self):
        """Detect pathlib Path usage."""
        code = """
def get_config():
    return Path("/etc/config")
"""
        missing = detect_missing_imports(code)
        assert "from pathlib import Path" in missing

    def test_detect_multiple_missing(self):
        """Detect multiple missing imports."""
        code = """
def complex_function():
    data = json.loads('{}')
    path = Path('/tmp')
    now = datetime.datetime.now()
"""
        missing = detect_missing_imports(code)
        assert len(missing) >= 3


class TestInjectImports:
    """Tests for injecting imports into code."""

    def test_inject_at_top(self):
        """Inject imports at the top of code."""
        code = """def hello():
    pass
"""
        imports = ["import json"]
        result = inject_imports(code, imports)
        assert result.startswith("import json")
        assert "def hello():" in result

    def test_inject_after_existing_imports(self):
        """Inject after existing imports."""
        code = """import os

def hello():
    pass
"""
        imports = ["import json"]
        result = inject_imports(code, imports)
        lines = result.split("\n")
        os_index = next(i for i, l in enumerate(lines) if "import os" in l)
        json_index = next(i for i, l in enumerate(lines) if "import json" in l)
        assert json_index > os_index

    def test_inject_after_docstring(self):
        """Inject after module docstring."""
        code = '''"""Module docstring."""

def hello():
    pass
'''
        imports = ["import json"]
        result = inject_imports(code, imports)
        assert '"""Module docstring."""' in result
        assert "import json" in result
        # Docstring should be before import
        assert result.index('"""') < result.index("import json")

    def test_no_injection_when_empty(self):
        """Return unchanged when no imports to add."""
        code = "def hello(): pass"
        result = inject_imports(code, [])
        assert result == code


class TestFixImports:
    """Tests for the combined fix_imports function."""

    def test_fix_missing_json(self):
        """Fix missing json import."""
        code = """
def load(path):
    return json.load(open(path))
"""
        fixed, added = fix_imports(code)
        assert "import json" in fixed
        assert "import json" in added

    def test_fix_multiple_imports(self):
        """Fix multiple missing imports."""
        code = """
def process():
    data = json.loads('{}')
    with pytest.raises(ValueError):
        pass
"""
        fixed, added = fix_imports(code)
        assert "import json" in fixed
        assert "import pytest" in fixed
        assert len(added) >= 2

    def test_no_changes_when_complete(self):
        """No changes when imports are complete."""
        code = """
import json

def load(path):
    return json.load(open(path))
"""
        fixed, added = fix_imports(code)
        assert added == []


class TestFixFileImports:
    """Tests for fixing imports in files."""

    def test_fix_file(self, tmp_path: Path):
        """Fix imports in a file."""
        test_file = tmp_path / "test_example.py"
        test_file.write_text("""
def test_load():
    data = json.loads('{"key": "value"}')
    assert data["key"] == "value"
""")
        added = fix_file_imports(test_file)
        assert "import json" in added

        # Verify file was updated
        content = test_file.read_text()
        assert "import json" in content

    def test_fix_nonexistent_file(self, tmp_path: Path):
        """Handle nonexistent file gracefully."""
        test_file = tmp_path / "nonexistent.py"
        added = fix_file_imports(test_file)
        assert added == []


class TestRealWorldScenarios:
    """Test real-world code patterns from stress test failures."""

    def test_config_manager_test_pattern(self):
        """Test pattern that failed in ConfigManager test."""
        code = """
import pytest
from configmanager import ConfigManager

def test_save_writes_config_to_file(tmp_path):
    cm = ConfigManager()
    cm.load(tmp_path / "config.json")
    cm.save(tmp_path / "output.json")
    with open(tmp_path / "output.json") as f:
        data = json.load(f)
    assert data is not None
"""
        fixed, added = fix_imports(code)
        assert "import json" in added
        assert "import json" in fixed

    def test_fastapi_test_pattern(self):
        """Test pattern that failed in FastAPI test."""
        code = """
from main import app

client = TestClient(app)

def test_get_todos():
    response = client.get("/todos")
    assert response.status_code == 200
"""
        fixed, added = fix_imports(code)
        assert "from fastapi.testclient import TestClient" in added

    def test_typing_in_function_signature(self):
        """Test typing annotations in signatures."""
        code = """
def get_todos() -> List[Dict[str, Any]]:
    return []
"""
        fixed, added = fix_imports(code)
        assert any("typing" in imp for imp in added)

    def test_datetime_in_model(self):
        """Test datetime in Pydantic model."""
        code = """
class Todo(BaseModel):
    id: int
    created_at: datetime.datetime = datetime.datetime.now()
"""
        fixed, added = fix_imports(code)
        assert any("datetime" in imp for imp in added)

    def test_preserves_existing_code(self):
        """Ensure existing code is preserved after injection."""
        code = """def test_example():
    result = json.loads('{"a": 1}')
    assert result["a"] == 1

def test_another():
    data = json.dumps({"b": 2})
    assert "b" in data
"""
        fixed, added = fix_imports(code)
        assert "def test_example():" in fixed
        assert "def test_another():" in fixed
        assert 'result = json.loads' in fixed
        assert "import json" in fixed


class TestFixTestClientPattern:
    """Tests for fixing missing TestClient initialization."""

    def test_detect_missing_client(self):
        """Detect when client is used but not defined."""
        code = """
from todo_api import Todo

def test_get_todos():
    response = client.get("/todos")
    assert response.status_code == 200
"""
        fixed, fixes = fix_testclient_pattern(code)
        assert "from fastapi.testclient import TestClient" in fixes
        assert "client = TestClient(app)" in fixes

    def test_no_fix_when_client_defined(self):
        """No fix needed when client is properly defined."""
        code = """
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_todos():
    response = client.get("/todos")
    assert response.status_code == 200
"""
        fixed, fixes = fix_testclient_pattern(code)
        assert len(fixes) == 0

    def test_adds_app_to_existing_import(self):
        """Add app to existing import from module."""
        code = """
from todo_api import Todo

def test_get_todos():
    response = client.get("/todos")
"""
        fixed, fixes = fix_testclient_pattern(code)
        assert "from todo_api import Todo, app" in fixed or "Added 'app' to todo_api import" in fixes

    def test_injects_testclient_import(self):
        """Inject TestClient import when missing."""
        code = """
from main import Todo

def test_post():
    response = client.post("/items")
"""
        fixed, fixes = fix_testclient_pattern(code)
        assert "from fastapi.testclient import TestClient" in fixed

    def test_injects_client_initialization(self):
        """Inject client initialization."""
        code = """
from api import Model

def test_delete():
    response = client.delete("/items/1")
"""
        fixed, fixes = fix_testclient_pattern(code)
        assert "client = TestClient(app)" in fixed

    def test_handles_multiple_client_methods(self):
        """Handle test file with multiple client methods."""
        code = """
from todo_api import Todo

def test_crud():
    client.post("/todos", json={})
    client.get("/todos")
    client.put("/todos/1", json={})
    client.delete("/todos/1")
"""
        fixed, fixes = fix_testclient_pattern(code)
        assert "client = TestClient(app)" in fixed
        # Should only add once, not for each usage
        assert fixed.count("client = TestClient(app)") == 1

    def test_real_world_failure_case(self):
        """Test the exact pattern that failed in stress test."""
        code = """import pytest
from datetime import datetime
from todo_api import Todo

def test_get_todos_empty():
    response = client.get("/todos")
    assert response.status_code == 200
    assert response.json() == []

def test_post_todo():
    new_todo = {"title": "Test"}
    response = client.post("/todos", json=new_todo)
    assert response.status_code == 201
"""
        fixed, fixes = fix_testclient_pattern(code)
        assert "from fastapi.testclient import TestClient" in fixed
        assert "client = TestClient(app)" in fixed
        # Verify app is added to todo_api import
        assert "from todo_api import Todo, app" in fixed or "Added 'app'" in str(fixes)
