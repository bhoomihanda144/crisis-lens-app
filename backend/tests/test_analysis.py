"""
Phase 5 Tests: AI Analysis & Intelligence Verification
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_analyze_report_flow():
    # 1. Create a fresh report
    create_payload = {
        "text": "Water entering ground floor houses on Lake Road. About 40 people on first floors.",
        "source": {
            "type": "citizen",
            "name": "Citizen reporter A"
        },
        "location": {
            "lat": 12.9304,
            "lng": 77.6784,
            "label": "Lake Road, Bellandur"
        },
        "reported_at": "2026-11-11T14:13:00Z",
        "forwarded_from": None
    }
    create_res = client.post("/reports", json=create_payload)
    assert create_res.status_code == 201
    report = create_res.json()
    report_id = report["id"]
    assert report["status"] == "pending_analysis"
    assert report["analysis"] is None

    # 2. Trigger AI Analysis
    analyze_res = client.post(f"/analyze/{report_id}")
    assert analyze_res.status_code == 200
    analyzed_report = analyze_res.json()

    assert analyzed_report["id"] == report_id
    assert analyzed_report["status"] == "analyzed"
    assert analyzed_report["analysis"] is not None

    anl = analyzed_report["analysis"]

    # Verify duplicate structure
    assert "duplicate" in anl
    assert isinstance(anl["duplicate"]["is_duplicate"], bool)
    assert isinstance(anl["duplicate"]["matches"], list)

    # Verify source verification structure
    assert "source_verification" in anl
    assert anl["source_verification"]["independence"] in ["independent", "forwarded", "unknown"]
    assert anl["source_verification"]["corroboration_status"] in ["corroborated", "single_source", "disputed"]

    # Verify freshness structure
    assert "freshness" in anl
    assert anl["freshness"]["status"] in ["recent", "aging", "stale"]
    assert isinstance(anl["freshness"]["age_minutes"], int)

    # Verify separate scores (No combined score!)
    scores = anl["scores"]
    assert "urgency" in scores
    assert "evidence_confidence" in scores
    assert "verification_priority" in scores

    assert 0 <= scores["urgency"]["score"] <= 100
    assert 0 <= scores["evidence_confidence"]["score"] <= 100
    assert 0 <= scores["verification_priority"]["score"] <= 100

    assert scores["urgency"]["level"] in ["low", "medium", "high", "critical"]
    assert scores["evidence_confidence"]["level"] in ["low", "medium", "high"]
    assert scores["verification_priority"]["level"] in ["low", "medium", "high"]

    # Verify recommendation structure & human-in-the-loop guarantee
    assert "recommendation" in anl
    assert anl["recommendation"]["type"] in ["verify_first", "monitor", "escalate_for_human_review"]
    assert anl["recommendation"]["requires_human_decision"] is True

    # 3. Verify GET /reports/{id} now returns the stored analysis
    get_res = client.get(f"/reports/{report_id}")
    assert get_res.status_code == 200
    fetched = get_res.json()
    assert fetched["status"] == "analyzed"
    assert fetched["analysis"] is not None
    assert fetched["analysis"]["scores"]["urgency"]["score"] == scores["urgency"]["score"]


def test_analyze_nonexistent_report():
    response = client.post("/analyze/rpt_nonexistent_999")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "not_found"
