"""
Phase 7 Tests: What-If Simulation & Contract Validation
"""
import pytest
from unittest.mock import patch, MagicMock
import httpx
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_simulation_success():
    payload = {
        "scenario_name": "Heavy rain, 3 roads blocked",
        "affected_population": 12000,
        "disaster_severity": 4,
        "rescue_teams": 6,
        "blocked_roads": 3,
        "available_ambulances": 5
    }
    response = client.post("/simulate", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Verify root fields
    assert data["scenario_id"].startswith("sim_")
    assert data["is_simulation"] is True
    assert "generated_at" in data

    # Verify echoed inputs
    assert data["inputs"]["scenario_name"] == payload["scenario_name"]
    assert data["inputs"]["affected_population"] == 12000
    assert data["inputs"]["disaster_severity"] == 4
    assert data["inputs"]["rescue_teams"] == 6

    # Verify results
    results = data["results"]
    assert "resource_demand" in results
    assert "shortages" in results
    assert "estimated_response_delay_minutes" in results
    assert "priority_changes" in results
    assert "summary" in results

    assert isinstance(results["resource_demand"]["rescue_teams"], int)
    assert isinstance(results["resource_demand"]["ambulances"], int)
    assert isinstance(results["estimated_response_delay_minutes"], int)


def test_simulation_invalid_severity():
    # Severity must be between 1 and 5
    invalid_payload = {
        "scenario_name": "Severe earthquake",
        "affected_population": 5000,
        "disaster_severity": 10,  # Invalid
        "rescue_teams": 4,
        "blocked_roads": 2,
        "available_ambulances": 3
    }
    response = client.post("/simulate", json=invalid_payload)
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "validation_error"


def test_simulation_negative_numbers():
    invalid_payload = {
        "scenario_name": "Invalid negative input",
        "affected_population": -100,  # Invalid
        "disaster_severity": 3,
        "rescue_teams": 2,
        "blocked_roads": 0,
        "available_ambulances": 1
    }
    response = client.post("/simulate", json=invalid_payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "validation_error"


def test_simulation_ai_engine_success():
    """Verifies backend calls AI Engine /simulation/run and returns validated SimulationResponse."""
    ai_mock_response = {
        "scenario_id": "sim_ai_999",
        "is_simulation": True,
        "generated_at": "2026-11-12T20:00:00Z",
        "inputs": {
            "scenario_name": "AI Simulated Flood",
            "affected_population": 15000,
            "disaster_severity": 4,
            "rescue_teams": 5,
            "blocked_roads": 4,
            "available_ambulances": 3,
        },
        "results": {
            "resource_demand": {
                "rescue_teams": 16,
                "ambulances": 15,
            },
            "shortages": [
                {"resource": "rescue_teams", "required": 16, "available": 5, "shortfall": 11},
                {"resource": "ambulances", "required": 15, "available": 3, "shortfall": 12},
            ],
            "estimated_response_delay_minutes": 42,
            "priority_changes": [],
            "summary": "Rescue teams are short by 11, ambulances are short by 12 under this scenario.",
        },
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = ai_mock_response

    mock_supabase = MagicMock()
    sim_inserts = []
    mock_supabase.table.return_value.insert.side_effect = lambda row: sim_inserts.append(row) or MagicMock()

    mock_inner_client = MagicMock()
    mock_inner_client.post.return_value = mock_resp
    mock_inner_client.__enter__.return_value = mock_inner_client

    with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
         patch("app.services.ai_client.httpx.Client", return_value=mock_inner_client), \
         patch("app.services.simulation_service.get_supabase_client", return_value=mock_supabase):
        resp = client.post("/simulate", json=ai_mock_response["inputs"])

    assert resp.status_code == 200
    data = resp.json()
    assert data["scenario_id"] == "sim_ai_999"
    assert data["is_simulation"] is True
    assert data["results"]["estimated_response_delay_minutes"] == 42
    assert len(data["results"]["shortages"]) == 2

    # Verify AI endpoint called with /simulation/run
    called_url = mock_inner_client.post.call_args[0][0]
    assert called_url.endswith("/simulation/run")
    called_json = mock_inner_client.post.call_args[1]["json"]
    assert called_json["scenario_name"] == "AI Simulated Flood"
    assert "incidents" in called_json
    assert "blocked_access_incident_ids" in called_json


def test_simulation_ai_engine_downtime_fallback():
    """Verifies backend falls back gracefully to deterministic calculation on connection failure."""
    payload = {
        "scenario_name": "Downtime Fallback Scenario",
        "affected_population": 8000,
        "disaster_severity": 3,
        "rescue_teams": 4,
        "blocked_roads": 2,
        "available_ambulances": 2,
    }

    mock_inner_client = MagicMock()
    mock_inner_client.post.side_effect = httpx.ConnectError("Connection refused")
    mock_inner_client.__enter__.return_value = mock_inner_client

    with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
         patch("app.services.ai_client.httpx.Client", return_value=mock_inner_client):
        resp = client.post("/simulate", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["scenario_id"].startswith("sim_")
    assert data["is_simulation"] is True
    assert data["inputs"]["scenario_name"] == payload["scenario_name"]
    assert "resource_demand" in data["results"]
    assert "estimated_response_delay_minutes" in data["results"]


def test_simulation_ai_engine_500_fallback():
    """Verifies backend falls back gracefully on AI Engine non-200 error."""
    mock_resp = MagicMock()
    mock_resp.status_code = 500

    payload = {
        "scenario_name": "Server Error Fallback Scenario",
        "affected_population": 5000,
        "disaster_severity": 2,
        "rescue_teams": 3,
        "blocked_roads": 1,
        "available_ambulances": 2,
    }

    mock_inner_client = MagicMock()
    mock_inner_client.post.return_value = mock_resp
    mock_inner_client.__enter__.return_value = mock_inner_client

    with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
         patch("app.services.ai_client.httpx.Client", return_value=mock_inner_client):
        resp = client.post("/simulate", json=payload)

    assert resp.status_code == 200
    data = resp.json()
    assert data["scenario_id"].startswith("sim_")
    assert data["is_simulation"] is True


def test_simulation_isolation_invariant():
    """Verifies simulation NEVER mutates live incident records or live priority scores."""
    mock_supabase = MagicMock()
    mock_tables = {
        "incidents": MagicMock(),
        "priority_scores": MagicMock(),
        "reports": MagicMock(),
        "simulations": MagicMock(),
    }
    mock_supabase.table.side_effect = lambda name: mock_tables.get(name, MagicMock())

    mock_tables["incidents"].select.return_value.execute.return_value.data = [
        {"id": "inc_001", "title": "Downtown Flood", "severity": "high", "location_label": "Downtown"}
    ]
    mock_tables["priority_scores"].select.return_value.in_.return_value.execute.return_value.data = [
        {"incident_id": "inc_001", "urgency_score": 85}
    ]

    payload = {
        "scenario_name": "Isolation Verification",
        "affected_population": 10000,
        "disaster_severity": 4,
        "rescue_teams": 2,
        "blocked_roads": 3,
        "available_ambulances": 2,
    }

    with patch("app.services.simulation_service.get_supabase_client", return_value=mock_supabase):
        resp = client.post("/simulate", json=payload)

    assert resp.status_code == 200

    # Invariant: Live incidents and priority_scores must NEVER be updated or mutated
    mock_tables["incidents"].update.assert_not_called()
    mock_tables["incidents"].delete.assert_not_called()
    mock_tables["priority_scores"].upsert.assert_not_called()
    mock_tables["priority_scores"].update.assert_not_called()
    mock_tables["reports"].update.assert_not_called()

    # Simulations table MUST have received the inserted simulation run
    mock_tables["simulations"].insert.assert_called_once()

