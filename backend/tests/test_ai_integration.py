"""
Phase 9 Tests: AI Integration, Resilience, Timeout & Contract Strictness
Covers Member 3 interface validation, error handling, and timeout resilience.
"""
import pytest
import httpx
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.ai_client import AIClient
from app.schemas.analysis import AnalysisObject

client = TestClient(app)


@pytest.mark.asyncio
async def test_ai_client_payload_structure():
    """Verify report input and context reports format sent to Member 3 AI engine."""
    sample_report = {
        "id": "rpt_test_ai_01",
        "text": "Water flooding residential homes near Lake Road",
        "source_type": "citizen",
        "source_name": "Citizen Observer",
        "reported_at": "2026-11-11T14:15:00Z",
        "received_at": "2026-11-11T14:16:00Z",
        "forwarded_from": None,
        "location_label": "Lake Road, Bellandur",
    }
    context_reports = [
        {
            "id": "rpt_test_ai_00",
            "text": "Earlier report of rising water",
            "source_type": "citizen",
            "source_name": "Prior Witness",
            "reported_at": "2026-11-11T13:50:00Z",
            "location_label": "Lake Road, Bellandur",
        }
    ]

    analysis = await AIClient.analyze_report(sample_report, context_reports)

    # Must be valid according to Pydantic schema
    validated = AnalysisObject.model_validate(analysis)
    assert validated.engine_version.startswith("deterministic-fallback")
    assert validated.recommendation.requires_human_decision is True
    assert 0 <= validated.scores.urgency.score <= 100
    assert 0 <= validated.scores.evidence_confidence.score <= 100
    assert 0 <= validated.scores.verification_priority.score <= 100


@pytest.mark.asyncio
async def test_ai_client_timeout_handling():
    """Verify that if Member 3's AI engine times out, backend gracefully falls back without crashing."""
    sample_report = {
        "id": "rpt_timeout_test",
        "text": "Report during AI timeout test",
        "source_type": "citizen",
        "source_name": "Tester",
        "reported_at": "2026-11-11T14:20:00Z",
        "received_at": "2026-11-11T14:21:00Z",
        "location_label": "Koramangala",
    }

    # Simulate httpx.TimeoutException
    with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("AI Engine timed out")):
        analysis = await AIClient.analyze_report(sample_report, [])
        assert analysis is not None
        assert "scores" in analysis
        assert analysis["recommendation"]["requires_human_decision"] is True


@pytest.mark.asyncio
async def test_ai_client_server_error_handling():
    """Verify that if Member 3's AI engine returns a 500 error, backend gracefully falls back."""
    sample_report = {
        "id": "rpt_500_test",
        "text": "Report during AI 500 test",
        "source_type": "official",
        "source_name": "Official Ward Officer",
        "reported_at": "2026-11-11T14:20:00Z",
        "received_at": "2026-11-11T14:21:00Z",
        "location_label": "Whitefield",
    }

    mock_resp = httpx.Response(500, request=httpx.Request("POST", "http://ai-engine/analyze"))
    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        analysis = await AIClient.analyze_report(sample_report, [])
        assert analysis is not None
        # Official source should have high confidence even in fallback
        assert analysis["scores"]["evidence_confidence"]["score"] >= 75


@pytest.mark.asyncio
async def test_ai_client_invalid_ai_response_handling():
    """Verify that malformed or non-contract AI output is safely handled and does not corrupt state."""
    sample_report = {
        "id": "rpt_malformed_test",
        "text": "Report during malformed AI test",
        "source_type": "sensor",
        "source_name": "Water Level Sensor",
        "reported_at": "2026-11-11T14:20:00Z",
        "received_at": "2026-11-11T14:21:00Z",
        "location_label": "Bellandur",
    }

    # Malformed response missing required fields
    malformed_json = {"invalid_key": "some_value"}
    mock_resp = httpx.Response(200, json=malformed_json, request=httpx.Request("POST", "http://ai-engine/analyze"))

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        # Validation error caught, falls back to deterministic analysis
        analysis = await AIClient.analyze_report(sample_report, [])
        assert analysis is not None
        assert "scores" in analysis
        assert "duplicate" in analysis


def test_ai_end_to_end_via_api():
    """End-to-end API test: submits a report with FWD marker, verifies AI marks it forwarded."""
    create_res = client.post("/reports", json={
        "text": "FWD: Severe flooding in basement car park, please forward to rescue teams!",
        "source": {"type": "social_media", "name": "Social Group"},
        "location": {"lat": 12.9304, "lng": 77.6784, "label": "Bellandur"},
        "reported_at": "2026-11-11T14:25:00Z"
    })
    assert create_res.status_code == 201
    rep_id = create_res.json()["id"]

    analyze_res = client.post(f"/analyze/{rep_id}")
    assert analyze_res.status_code == 200
    data = analyze_res.json()

    # Verify AI classified as forwarded copy
    assert data["analysis"]["source_verification"]["independence"] == "forwarded"
    # Forwarded copy must NOT receive high evidence confidence
    assert data["analysis"]["scores"]["evidence_confidence"]["score"] < 50
