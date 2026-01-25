"""Tests for Lloyd API endpoints."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Create a test API key."""
    key = "test-api-key-12345"
    key_file = tmp_path / ".lloyd" / "api_key"
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_text(key)
    monkeypatch.setattr("lloyd.api.API_KEY_FILE", key_file)
    monkeypatch.setattr("lloyd.api.API_KEY", key)
    return key


@pytest.fixture
def client(api_key: str) -> TestClient:
    """Create test client with mocked API key."""
    from lloyd.api import app
    return TestClient(app)


@pytest.fixture
def auth_headers(api_key: str) -> dict[str, str]:
    """Get authorization headers."""
    return {"Authorization": f"Bearer {api_key}"}


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_endpoint(self, client: TestClient) -> None:
        """Test /health endpoint returns OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]
        assert "version" in data
        assert "checks" in data

    def test_api_health_endpoint(self, client: TestClient) -> None:
        """Test /api/health endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_liveness_probe(self, client: TestClient) -> None:
        """Test liveness probe always returns 200."""
        response = client.get("/api/health/live")
        assert response.status_code == 200
        assert response.json() == {"alive": True}

    def test_readiness_probe(self, client: TestClient) -> None:
        """Test readiness probe."""
        response = client.get("/api/health/ready")
        # May be 200 or 503 depending on workspace
        assert response.status_code in [200, 503]


class TestStatusEndpoint:
    """Tests for status endpoint."""

    def test_status_no_prd(self, client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test status when no PRD exists."""
        monkeypatch.chdir(tmp_path)
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data["project_name"] == "No Project"
        assert data["status"] == "idle"
        assert data["total_stories"] == 0


class TestAuthenticationRequired:
    """Tests for authentication on protected endpoints."""

    def test_idea_requires_auth(self, client: TestClient) -> None:
        """Test POST /api/idea requires authentication."""
        response = client.post("/api/idea", json={"description": "test"})
        assert response.status_code == 401

    def test_init_requires_auth(self, client: TestClient) -> None:
        """Test POST /api/init requires authentication."""
        response = client.post("/api/init")
        assert response.status_code == 401

    def test_queue_post_requires_auth(self, client: TestClient) -> None:
        """Test POST /api/queue requires authentication."""
        response = client.post("/api/queue", json={"description": "test"})
        assert response.status_code == 401

    def test_queue_delete_requires_auth(self, client: TestClient) -> None:
        """Test DELETE /api/queue/<id> requires authentication."""
        response = client.delete("/api/queue/test-id")
        assert response.status_code == 401

    def test_selfmod_approve_requires_auth(self, client: TestClient) -> None:
        """Test POST /api/selfmod/<id>/approve requires authentication."""
        response = client.post("/api/selfmod/test-id/approve")
        assert response.status_code == 401

    def test_invalid_token(self, client: TestClient) -> None:
        """Test invalid token returns 403."""
        headers = {"Authorization": "Bearer wrong-token"}
        response = client.post("/api/idea", json={"description": "test"}, headers=headers)
        assert response.status_code == 403


class TestAuthenticatedEndpoints:
    """Tests for endpoints with valid authentication."""

    def test_idea_with_auth(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        """Test idea submission with authentication (queue_only mode)."""
        # Use queue_only mode to avoid needing to mock LloydFlow
        response = client.post(
            "/api/idea",
            json={"description": "test idea", "queue_only": True},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["queued"] is True

    def test_init_with_auth(self, client: TestClient, auth_headers: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test project initialization with authentication."""
        monkeypatch.chdir(tmp_path)
        response = client.post("/api/init", headers=auth_headers)
        assert response.status_code == 200
        assert (tmp_path / ".lloyd").exists()


class TestQueueEndpoints:
    """Tests for idea queue endpoints."""

    def test_get_queue_no_auth(self, client: TestClient) -> None:
        """Test GET /api/queue does not require auth (read-only)."""
        response = client.get("/api/queue")
        assert response.status_code == 200

    def test_get_queue_stats(self, client: TestClient) -> None:
        """Test queue statistics endpoint."""
        response = client.get("/api/queue/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data

    def test_add_to_queue(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        """Test adding idea to queue."""
        response = client.post(
            "/api/queue",
            json={"description": "test idea", "priority": 1},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "idea_id" in data

    def test_batch_add_to_queue(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        """Test batch adding ideas to queue."""
        response = client.post(
            "/api/queue/batch",
            json={"ideas": ["idea 1", "idea 2", "idea 3"], "priority": 1},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3


class TestKnowledgeEndpoints:
    """Tests for knowledge base endpoints."""

    def test_get_knowledge_no_auth(self, client: TestClient) -> None:
        """Test GET /api/knowledge does not require auth (read-only)."""
        response = client.get("/api/knowledge")
        assert response.status_code == 200


class TestInboxEndpoints:
    """Tests for inbox endpoints."""

    def test_get_inbox_no_auth(self, client: TestClient) -> None:
        """Test GET /api/inbox does not require auth (read-only)."""
        response = client.get("/api/inbox")
        assert response.status_code == 200


class TestBrainstormEndpoints:
    """Tests for brainstorm endpoints."""

    def test_get_brainstorm_sessions(self, client: TestClient) -> None:
        """Test getting brainstorm sessions."""
        response = client.get("/api/brainstorm")
        assert response.status_code == 200


class TestExtensionsEndpoints:
    """Tests for extensions endpoints."""

    def test_get_extensions(self, client: TestClient) -> None:
        """Test getting extensions list."""
        response = client.get("/api/extensions")
        assert response.status_code == 200


class TestSelfModEndpoints:
    """Tests for self-modification endpoints."""

    def test_get_selfmod_queue(self, client: TestClient) -> None:
        """Test getting self-mod queue."""
        response = client.get("/api/selfmod/queue")
        assert response.status_code == 200
