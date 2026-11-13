"""Tests for FastAPI microservice health and root endpoints."""

from fastapi.testclient import TestClient
from ai_engine.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify that GET /health returns 200 OK with expected structure."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "crisis-lens-ai-engine"
    assert data["version"] == "0.1.0"
    assert data["port"] == 8001
    assert "stage" in data


def test_root_endpoint():
    """Verify that GET / returns service information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["port"] == 8001
    assert data["health_url"] == "/health"
