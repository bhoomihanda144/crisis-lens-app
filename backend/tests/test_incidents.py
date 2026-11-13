"""
Phase 4 Tests: Incidents Endpoints & Contract Validation
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_incidents():
    response = client.get("/incidents")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total"], int)


def test_get_incident_not_found():
    response = client.get("/incidents/inc_nonexistent_999")
    assert response.status_code == 404
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "not_found"
    assert "inc_nonexistent_999" in data["error"]["message"]
