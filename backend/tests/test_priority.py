"""
Phase 6 Tests: Smart Rescue Priority & Contract Validation
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_priority_default_urgency():
    response = client.get("/incidents/priority")
    assert response.status_code == 200
    data = response.json()

    assert data["sort"] == "urgency"
    assert "items" in data
    assert isinstance(data["items"], list)

    if data["items"]:
        first = data["items"][0]
        assert first["rank"] == 1
        assert "incident_id" in first
        assert "title" in first
        assert "location" in first

        # Check separate scores (no blended/combined score)
        assert 0 <= first["urgency"]["score"] <= 100
        assert 0 <= first["evidence_confidence"]["score"] <= 100
        assert 0 <= first["verification_priority"]["score"] <= 100

        # Check human decision requirements
        assert first["requires_human_decision"] is True
        assert first["human_decision"]["status"] == "not_decided"
        assert first["human_decision"]["decided_by"] is None

        # Verify sorted descending by urgency
        for i in range(len(data["items"]) - 1):
            assert data["items"][i]["urgency"]["score"] >= data["items"][i + 1]["urgency"]["score"]


def test_get_priority_sort_verification():
    response = client.get("/incidents/priority?sort=verification")
    assert response.status_code == 200
    data = response.json()

    assert data["sort"] == "verification"
    assert "items" in data

    if len(data["items"]) >= 2:
        # Verify sorted descending by verification priority
        for i in range(len(data["items"]) - 1):
            assert data["items"][i]["verification_priority"]["score"] >= data["items"][i + 1]["verification_priority"]["score"]


def test_get_priority_invalid_sort():
    response = client.get("/incidents/priority?sort=invalid_sort")
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# Stage 5: AI Engine Priority Ranking Integration Tests
# ---------------------------------------------------------------------------

from unittest.mock import patch, MagicMock
import httpx
from app.services.priority_service import PriorityService


def test_ai_engine_priority_ranking_success():
    """When AI Engine returns 200 with valid PriorityResponse, backend serves it directly."""
    mock_ai_resp = {
        "sort": "urgency",
        "items": [
            {
                "rank": 1,
                "incident_id": "inc_001",
                "title": "Flooding near Bellandur lake road",
                "location": {"lat": 12.9304, "lng": 77.6784, "label": "Lake Road, Bellandur"},
                "urgency": {"score": 96, "level": "critical", "reasons": ["Water level rapid increase"]},
                "evidence_confidence": {"score": 85, "level": "high", "reasons": ["Multiple official confirmations"]},
                "verification_priority": {"score": 20, "level": "low", "reasons": ["Fully corroborated"]},
                "explanation": ["Active flood emergency"],
                "recommended_next_steps": ["Deploy swift rescue team"],
                "requires_human_decision": True,
                "human_decision": {"status": "not_decided", "decided_by": None, "decided_at": None},
            }
        ],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_ai_resp

    recorded_calls = []

    def mock_post(url, json=None, params=None, **kwargs):
        recorded_calls.append({"url": url, "json": json, "params": params})
        return mock_resp

    with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
         patch("httpx.Client.post", side_effect=mock_post):
        response = client.get("/incidents/priority?sort=urgency")

    assert response.status_code == 200
    data = response.json()
    assert data["sort"] == "urgency"
    assert len(data["items"]) == 1
    assert data["items"][0]["incident_id"] == "inc_001"
    assert data["items"][0]["urgency"]["score"] == 96

    assert len(recorded_calls) == 1
    call = recorded_calls[0]
    assert call["url"] == "http://ai-engine:8001/incidents/priority"
    assert call["params"]["sort"] == "urgency"
    assert call["json"]["sort"] == "urgency"
    assert "incidents" in call["json"]
    assert isinstance(call["json"]["incidents"], list)


def test_ai_engine_priority_ranking_sort_verification():
    """Verify sort='verification' parameter is passed to AI Engine."""
    mock_ai_resp = {
        "sort": "verification",
        "items": [
            {
                "rank": 1,
                "incident_id": "inc_002",
                "title": "Unconfirmed collapse report",
                "location": {"lat": 12.94, "lng": 77.62, "label": "Koramangala"},
                "urgency": {"score": 75, "level": "high", "reasons": ["Possible entrapment"]},
                "evidence_confidence": {"score": 35, "level": "low", "reasons": ["Single witness account"]},
                "verification_priority": {"score": 90, "level": "high", "reasons": ["High urgency unverified citizen report"]},
                "explanation": ["Needs urgent ground check"],
                "recommended_next_steps": ["Dispatch reconnaissance unit"],
                "requires_human_decision": True,
                "human_decision": {"status": "not_decided", "decided_by": None, "decided_at": None},
            }
        ],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_ai_resp

    recorded_calls = []

    def mock_post(url, json=None, params=None, **kwargs):
        recorded_calls.append({"url": url, "json": json, "params": params})
        return mock_resp

    with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
         patch("httpx.Client.post", side_effect=mock_post):
        response = client.get("/incidents/priority?sort=verification")

    assert response.status_code == 200
    data = response.json()
    assert data["sort"] == "verification"
    assert data["items"][0]["verification_priority"]["score"] == 90

    assert len(recorded_calls) == 1
    assert recorded_calls[0]["params"]["sort"] == "verification"
    assert recorded_calls[0]["json"]["sort"] == "verification"


def test_ai_engine_priority_ranking_timeout_fallback():
    """When AI Engine priority ranking times out, backend falls back gracefully."""
    with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
         patch("httpx.Client.post", side_effect=httpx.TimeoutException("Priority timed out")):
        response = client.get("/incidents/priority")

    assert response.status_code == 200
    data = response.json()
    assert data["sort"] == "urgency"
    assert isinstance(data["items"], list)


def test_ai_engine_priority_ranking_500_fallback():
    """When AI Engine returns HTTP 500, backend falls back gracefully."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
         patch("httpx.Client.post", return_value=mock_resp):
        response = client.get("/incidents/priority")

    assert response.status_code == 200
    data = response.json()
    assert data["sort"] == "urgency"
    assert isinstance(data["items"], list)


def test_ai_engine_priority_ranking_invalid_schema_fallback():
    """When AI Engine returns corrupt or incomplete JSON, backend falls back safely."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"corrupt": "data"}

    with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
         patch("httpx.Client.post", return_value=mock_resp):
        response = client.get("/incidents/priority")

    assert response.status_code == 200
    data = response.json()
    assert data["sort"] == "urgency"
    assert isinstance(data["items"], list)

