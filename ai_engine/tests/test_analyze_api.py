"""Tests for POST /analyze endpoint and backend AnalysisObject compatibility."""

import sys
from pathlib import Path

# Add backend directory to path so app.* imports resolve properly
backend_dir = Path(__file__).resolve().parents[2] / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from ai_engine.main import app
from ai_engine.schemas.analysis import Analysis

# Import backend AnalysisObject to verify strict cross-member compatibility
from app.schemas.analysis import AnalysisObject

client = TestClient(app)


def test_analyze_endpoint_success():
    """Verify POST /analyze produces valid Analysis matching backend AnalysisObject."""
    payload = {
        "report": {
            "id": "rpt_002",
            "text": "Water entering ground floor houses on Lake Road, families moving upstairs.",
            "source_type": "citizen",
            "source_name": "Citizen reporter B",
            "location_label": "Lake Road, Bellandur",
            "lat": 12.9304,
            "lng": 77.6784,
            "reported_at": "2026-11-11T14:13:00Z",
        },
        "context_reports": [
            {
                "id": "rpt_001",
                "text": "Water entering ground floor houses on Lake Road, people moving upstairs.",
                "source_type": "citizen",
                "source_name": "Citizen reporter A",
                "location_label": "Lake Road, Bellandur",
                "lat": 12.9304,
                "lng": 77.6784,
                "reported_at": "2026-11-11T14:00:00Z",
            }
        ],
    }

    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Verify AI Engine's own Pydantic model
    validated_ai = Analysis.model_validate(data)
    assert validated_ai.engine_version == "0.1.0"
    assert validated_ai.duplicate.is_duplicate is True
    assert validated_ai.recommendation.requires_human_decision is True
    # Non-forwarded report with unestablished provenance must have null original_report_id
    assert validated_ai.source_verification.original_report_id is None
    assert validated_ai.source_verification.independence.value == "unknown"

    # Crucial: Verify that Member 2's backend AnalysisObject schema accepts it cleanly
    validated_backend = AnalysisObject.model_validate(data)
    assert validated_backend.engine_version == "0.1.0"
    assert validated_backend.recommendation.requires_human_decision is True


def test_analyze_corroborated_with_independent_provenance():
    """Verify that reports with defensible independent provenance produce corroboration."""
    payload = {
        "report": {
            "id": "rpt_002",
            "text": "Water entering ground floor houses on Lake Road, families moving upstairs.",
            "source_type": "citizen",
            "source_name": "Witness Beta",
            "location_label": "Lake Road, Bellandur",
            "lat": 12.9304,
            "lng": 77.6784,
            "reported_at": "2026-11-11T14:13:00Z",
            "provenance": "independent",
        },
        "context_reports": [
            {
                "id": "rpt_001",
                "text": "Water entering ground floor houses on Lake Road, people moving upstairs.",
                "source_type": "citizen",
                "source_name": "Witness Alpha",
                "location_label": "Lake Road, Bellandur",
                "lat": 12.9304,
                "lng": 77.6784,
                "reported_at": "2026-11-11T14:00:00Z",
                "provenance": "independent",
            }
        ],
    }

    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["source_verification"]["independence"] == "independent"
    assert data["source_verification"]["corroboration_status"] == "corroborated"
    assert data["source_verification"]["original_report_id"] is None


def test_analyze_same_location_different_emergency_not_duplicate():
    """Verify that unrelated emergencies at the same location are NOT duplicates."""
    payload = {
        "report": {
            "id": "rpt_fire",
            "text": "Sparking transformer and electrical fire on Lake Road.",
            "source_type": "citizen",
            "location_label": "Lake Road, Bellandur",
            "lat": 12.9304,
            "lng": 77.6784,
            "reported_at": "2026-11-11T14:15:00Z",
        },
        "context_reports": [
            {
                "id": "rpt_flood",
                "text": "Water entering ground floor houses on Lake Road.",
                "source_type": "citizen",
                "location_label": "Lake Road, Bellandur",
                "lat": 12.9304,
                "lng": 77.6784,
                "reported_at": "2026-11-11T14:15:00Z",
            }
        ],
    }

    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["duplicate"]["is_duplicate"] is False
    assert len(data["duplicate"]["matches"]) == 0


def test_analyze_with_member2_exact_payload():
    """Validates compatibility with Member 2's exact sample report from test_ai_integration.py."""
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

    response = client.post("/analyze", json={"report": sample_report, "context_reports": context_reports})
    assert response.status_code == 200
    data = response.json()

    # Validate with Member 2's backend schema
    validated = AnalysisObject.model_validate(data)
    assert validated.engine_version == "0.1.0"
    assert validated.recommendation.requires_human_decision is True
    assert 0 <= validated.scores.urgency.score <= 100
    assert 0 <= validated.scores.evidence_confidence.score <= 100
    assert 0 <= validated.scores.verification_priority.score <= 100


def test_analyze_forwarded_report_low_confidence():
    """Forwarded report must have independence='forwarded', low evidence confidence, and never corroborate."""
    forwarded_report = {
        "id": "rpt_fwd_01",
        "text": "FWD: Severe flooding in basement car park, please forward to rescue teams!",
        "source_type": "social_media",
        "source_name": "Social Group",
        "location_label": "Bellandur",
        "forwarded_from": "rpt_original_01",
        "reported_at": "2026-11-11T14:25:00Z",
    }

    response = client.post("/analyze", json={"report": forwarded_report, "context_reports": []})
    assert response.status_code == 200
    data = response.json()

    assert data["source_verification"]["independence"] == "forwarded"
    assert data["source_verification"]["original_report_id"] == "rpt_original_01"
    assert data["scores"]["evidence_confidence"]["score"] < 50
    assert data["source_verification"]["corroboration_status"] == "single_source"
