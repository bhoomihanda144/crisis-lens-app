"""
Phase 4 Tests: Reports Endpoints & Contract Validation
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_report_success():
    payload = {
        "text": "Water entering ground floor houses on Lake Road",
        "source": {
            "type": "citizen",
            "name": "Citizen reporter"
        },
        "location": {
            "lat": 12.9304,
            "lng": 77.6784,
            "label": "Lake Road, Bellandur"
        },
        "reported_at": "2026-11-11T14:13:00Z",
        "forwarded_from": None
    }
    response = client.post("/reports", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["id"].startswith("rpt_")
    assert data["text"] == payload["text"]
    assert data["source"]["type"] == "citizen"
    assert data["source"]["name"] == "Citizen reporter"
    assert data["location"]["lat"] == 12.9304
    assert data["location"]["lng"] == 77.6784
    assert data["status"] == "pending_analysis"
    assert data["analysis"] is None
    assert data["verification"] is None


def test_create_report_validation_error():
    # Missing required text field
    invalid_payload = {
        "source": {"type": "citizen", "name": "Anonymous"},
        "location": {"lat": 12.9304, "lng": 77.6784, "label": "Lake Road"}
    }
    response = client.post("/reports", json=invalid_payload)
    assert response.status_code == 422
    data = response.json()

    # Check error format strictly adheres to contract
    assert "error" in data
    assert data["error"]["code"] == "validation_error"
    assert data["error"]["message"] == "Request failed validation"
    assert data["error"]["details"] is not None


def test_list_reports():
    response = client.get("/reports?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert isinstance(data["items"], list)


def test_get_report_not_found():
    response = client.get("/reports/rpt_nonexistent_999")
    assert response.status_code == 404
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "not_found"
    assert "not found" in data["error"]["message"].lower()
