"""Unit tests for system health endpoint."""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Assert GET /api/v1/health returns 200 with required fields."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert "agentdojo_version" in data
    assert data["db_ok"] is True
