"""
Phase 6 Tests: Evidence Relationship Graph & Contract Validation
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_evidence_graph_success():
    response = client.get("/incidents/inc_001/evidence-graph")
    assert response.status_code == 200
    data = response.json()

    assert data["incident_id"] == "inc_001"
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)

    for node in data["nodes"]:
        # Strict contract rule: Node id must equal the report id
        assert node["id"] == node["report_id"]
        assert node["role"] in ["original", "duplicate", "forwarded", "corroborating", "conflicting"]
        assert node["source_type"] in ["citizen", "social_media", "news", "official", "sensor", "responder"]
        assert node["freshness_status"] in ["recent", "aging", "stale"]
        assert "excerpt" in node
        assert "timestamp" in node

    for edge in data["edges"]:
        assert "id" in edge
        assert "source" in edge
        assert "target" in edge
        assert edge["type"] in ["original", "duplicate", "forwarded", "corroborating", "conflicting"]
        assert 0.0 <= edge["confidence"] <= 1.0


def test_get_evidence_graph_not_found():
    response = client.get("/incidents/inc_nonexistent_999/evidence-graph")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "not_found"
    assert "inc_nonexistent_999" in data["error"]["message"]


# ---------------------------------------------------------------------------
# Stage 4: AI Engine Evidence Graph Integration Tests
# ---------------------------------------------------------------------------

from unittest.mock import patch, MagicMock
import httpx
from app.services.evidence_service import EvidenceService
from app.schemas.evidence import EvidenceGraphResponse


def test_ai_engine_evidence_graph_success():
    """When AI Engine returns 200 with valid graph, backend serves it directly."""
    mock_ai_graph = {
        "incident_id": "inc_001",
        "nodes": [
            {
                "id": "rpt_001",
                "report_id": "rpt_001",
                "label": "Citizen: Lake Road flooding",
                "role": "original",
                "source_type": "citizen",
                "source_name": "Citizen reporter",
                "timestamp": "2026-11-11T13:50:00Z",
                "excerpt": "Water entering ground floor houses...",
                "freshness_status": "recent",
            },
            {
                "id": "rpt_002",
                "report_id": "rpt_002",
                "label": "Citizen: Lake Road flooding",
                "role": "duplicate",
                "source_type": "citizen",
                "source_name": "Citizen reporter",
                "timestamp": "2026-11-11T14:13:00Z",
                "excerpt": "Water entering houses on Lake Road...",
                "freshness_status": "recent",
            },
        ],
        "edges": [
            {
                "id": "edge_001",
                "source": "rpt_002",
                "target": "rpt_001",
                "type": "duplicate",
                "label": "Duplicate (0.91)",
                "confidence": 0.91,
            }
        ],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_ai_graph

    recorded_calls = []

    def mock_post(url, json=None, **kwargs):
        recorded_calls.append({"url": url, "json": json})
        return mock_resp

    with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
         patch("httpx.Client.post", side_effect=mock_post):
        response = client.get("/incidents/inc_001/evidence-graph")

    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == "inc_001"
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
    assert data["edges"][0]["source"] == "rpt_002"
    assert data["edges"][0]["target"] == "rpt_001"

    # Verify expected endpoint and payload format sent to AI engine
    assert len(recorded_calls) == 1
    call = recorded_calls[0]
    assert call["url"] == "http://ai-engine:8001/incidents/inc_001/evidence-graph"
    assert call["json"]["incident_id"] == "inc_001"
    assert "reports" in call["json"]
    assert "conflicts" in call["json"]


def test_ai_engine_evidence_graph_timeout_fallback():
    """When AI Engine times out, backend gracefully falls back without 500 error."""
    with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
         patch("httpx.Client.post", side_effect=httpx.TimeoutException("Connection timed out")):
        response = client.get("/incidents/inc_001/evidence-graph")

    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == "inc_001"
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_ai_engine_evidence_graph_500_server_error_fallback():
    """When AI Engine returns HTTP 500, backend falls back to stored relationships."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
         patch("httpx.Client.post", return_value=mock_resp):
        response = client.get("/incidents/inc_001/evidence-graph")

    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == "inc_001"
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_ai_engine_evidence_graph_invalid_schema_fallback():
    """When AI Engine returns invalid or corrupt schema, backend falls back safely."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"corrupt": "data", "missing_required_fields": True}

    with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
         patch("httpx.Client.post", return_value=mock_resp):
        response = client.get("/incidents/inc_001/evidence-graph")

    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == "inc_001"
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_ai_engine_evidence_graph_passes_conflicts():
    """Backend extracts explicitly identified conflicts from analysis_results and sends them to AI Engine."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "incident_id": "inc_001",
        "nodes": [],
        "edges": [],
    }

    recorded_payloads = []

    def mock_post(url, json=None, **kwargs):
        recorded_payloads.append(json)
        return mock_resp

    with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
         patch("httpx.Client.post", side_effect=mock_post):
        EvidenceService.get_evidence_graph("inc_001")

    assert len(recorded_payloads) == 1
    payload = recorded_payloads[0]
    assert payload["incident_id"] == "inc_001"
    assert isinstance(payload["conflicts"], list)
    assert isinstance(payload["reports"], list)

