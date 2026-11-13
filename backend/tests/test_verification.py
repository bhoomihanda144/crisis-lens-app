"""
Phase 7 Tests: Human Verification & Contract Validation
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _create_sample_report(text: str = "Test report for verification"):
    res = client.post("/reports", json={
        "text": text,
        "source": {"type": "citizen", "name": "Citizen A"},
        "location": {"lat": 12.9304, "lng": 77.6784, "label": "Bellandur"},
        "reported_at": "2026-11-11T14:00:00Z"
    })
    assert res.status_code == 201
    return res.json()["id"]


def test_verify_confirm():
    report_id = _create_sample_report("Water rising near hospital")
    payload = {
        "action": "confirm",
        "note": "Confirmed by ward officer",
        "verified_by": "Duty Officer"
    }
    response = client.patch(f"/reports/{report_id}/verify", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == report_id
    assert data["status"] == "verified"
    assert data["verification"] is not None
    assert data["verification"]["action"] == "confirm"
    assert data["verification"]["note"] == "Confirmed by ward officer"
    assert data["verification"]["verified_by"] == "Duty Officer"
    assert "verified_at" in data["verification"]


def test_verify_reject():
    report_id = _create_sample_report("False alarm on Main Street")
    payload = {
        "action": "reject",
        "note": "Checked site, clear of hazard",
        "verified_by": "Patrol Unit 4"
    }
    response = client.patch(f"/reports/{report_id}/verify", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "rejected"
    assert data["verification"]["action"] == "reject"


def test_verify_request_more_info():
    report_id = _create_sample_report("Unclear smoke spotted")
    payload = {
        "action": "request_more_info",
        "note": "Need exact building number"
    }
    response = client.patch(f"/reports/{report_id}/verify", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "needs_more_info"
    assert data["verification"]["action"] == "request_more_info"


def test_verify_nonexistent_report():
    response = client.patch("/reports/rpt_nonexistent_999/verify", json={"action": "confirm"})
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "not_found"


def test_verify_invalid_action():
    report_id = _create_sample_report("Report with invalid verify action")
    response = client.patch(f"/reports/{report_id}/verify", json={"action": "invalid_action"})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"
