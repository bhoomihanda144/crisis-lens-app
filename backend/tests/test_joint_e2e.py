"""
Joint End-to-End Integration Tests: Backend + Member 3 AI Engine (Stages 4 & 5).
Verifies:
1. Backend calls AI Engine Evidence Graph endpoint (POST /incidents/{id}/evidence-graph)
2. Backend calls AI Engine Priority Ranking endpoint (POST /incidents/priority) in urgency & verification modes
3. Frontend receives correct evidence graph and all 3 separate priority scores
4. Stored priority scores update correctly in Supabase
5. Safe fallback handling during AI Engine downtime
"""
import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import httpx
from fastapi.testclient import TestClient

# Add scratch AI Engine path to sys.path so we test Member 3's real AI Engine code
AI_ENGINE_PATH = r"C:\Users\dell\.gemini\antigravity\brain\dc623c62-f1e9-4a05-b7bd-17bac159c8c1\scratch\ai_engine_test"
if AI_ENGINE_PATH not in sys.path:
    sys.path.insert(0, AI_ENGINE_PATH)

from ai_engine.main import app as ai_engine_app
from app.main import app as backend_app
from app.services.evidence_service import EvidenceService
from app.services.priority_service import PriorityService

backend_client = TestClient(backend_app)
ai_client = TestClient(ai_engine_app)


class TestJointEndToEndIntegration:

    @pytest.fixture(autouse=True)
    def setup_transport(self):
        """Routes backend AIClient HTTP calls directly into Member 3's real AI Engine FastAPI application."""
        ai_engine_test_client = TestClient(ai_engine_app)

        def mock_client_factory(*args, **kwargs):
            # Create a client that redirects AI_ENGINE_URL requests to Member 3's TestClient
            c = MagicMock()

            def mock_post(url, *call_args, **call_kwargs):
                # Extract path from URL
                if ":8001/" in url:
                    path = "/" + url.split(":8001/", 1)[-1]
                else:
                    path = url
                # Call Member 3's real FastAPI endpoint
                resp = ai_engine_test_client.post(path, *call_args, **call_kwargs)
                return resp

            c.post = mock_post
            c.__enter__ = lambda s: c
            c.__exit__ = lambda *args: None
            return c

        self.mock_client_factory = mock_client_factory

    # -----------------------------------------------------------------------
    # 1. Evidence Graph Generation via AI Engine
    # -----------------------------------------------------------------------
    def test_e2e_evidence_graph_with_real_ai_engine(self):
        """Backend calls Member 3 AI Engine endpoint and receives DAG evidence graph."""
        with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
             patch("httpx.Client", side_effect=self.mock_client_factory):
            response = backend_client.get("/incidents/inc_001/evidence-graph")

        assert response.status_code == 200
        data = response.json()

        # Contract Shape Verifications
        assert data["incident_id"] == "inc_001"
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

        # Node contract rules
        for node in data["nodes"]:
            assert node["id"] == node["report_id"]
            assert node["role"] in ["original", "duplicate", "forwarded", "corroborating", "conflicting"]
            assert node["source_type"] in ["citizen", "social_media", "news", "official", "sensor", "responder"]
            assert node["freshness_status"] in ["recent", "aging", "stale"]
            assert "excerpt" in node
            assert "timestamp" in node

        # Edge contract rules (pointing from later/derived -> earlier/reference)
        for edge in data["edges"]:
            assert "id" in edge
            assert "source" in edge
            assert "target" in edge
            assert edge["type"] in ["duplicate", "forwarded", "corroborating", "conflicting"]
            assert 0.0 <= edge["confidence"] <= 1.0

    # -----------------------------------------------------------------------
    # 2. Priority Ranking in Urgency & Verification Modes
    # -----------------------------------------------------------------------
    def test_e2e_priority_ranking_urgency_mode(self):
        """Backend calls AI Engine in urgency mode; items sorted descending by urgency score."""
        with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
             patch("httpx.Client", side_effect=self.mock_client_factory):
            response = backend_client.get("/incidents/priority?sort=urgency")

        assert response.status_code == 200
        data = response.json()

        assert data["sort"] == "urgency"
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 1

        first = data["items"][0]
        assert first["rank"] == 1
        assert "incident_id" in first
        assert "title" in first
        assert "location" in first

        # Check all 3 separate scores exist and are integers 0-100
        assert 0 <= first["urgency"]["score"] <= 100
        assert first["urgency"]["level"] in ["critical", "high", "medium", "low"]
        assert 0 <= first["evidence_confidence"]["score"] <= 100
        assert first["evidence_confidence"]["level"] in ["high", "medium", "low"]
        assert 0 <= first["verification_priority"]["score"] <= 100
        assert first["verification_priority"]["level"] in ["high", "medium", "low"]

        # Human authority invariants
        assert first["requires_human_decision"] is True
        assert first["human_decision"]["status"] == "not_decided"

        # Verify sorted descending by urgency score
        for i in range(len(data["items"]) - 1):
            assert data["items"][i]["urgency"]["score"] >= data["items"][i + 1]["urgency"]["score"]

    def test_e2e_priority_ranking_verification_mode(self):
        """Backend calls AI Engine in verification mode; items sorted descending by verification priority."""
        with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
             patch("httpx.Client", side_effect=self.mock_client_factory):
            response = backend_client.get("/incidents/priority?sort=verification")

        assert response.status_code == 200
        data = response.json()

        assert data["sort"] == "verification"
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 1

        # Verify sorted descending by verification_priority score
        for i in range(len(data["items"]) - 1):
            assert data["items"][i]["verification_priority"]["score"] >= data["items"][i + 1]["verification_priority"]["score"]

    # -----------------------------------------------------------------------
    # 3. Database Score Persistence on Live AI Calculation
    # -----------------------------------------------------------------------
    def test_e2e_priority_scores_upsert_on_ai_calculation(self):
        """When AI Engine calculates priorities, backend upserts the results into priority_scores."""
        mock_supabase = MagicMock()
        mock_incidents = [
            {
                "id": "inc_001",
                "title": "Bellandur Flooding",
                "type": "flood",
                "severity": "critical",
                "status": "active",
                "lat": 12.93,
                "lng": 77.67,
                "location_label": "Bellandur",
                "independent_source_count": 2,
            }
        ]

        # Use an explicit table lookup dictionary so no unwanted MagicMocks are iterated
        mock_tables = {
            "incidents": MagicMock(),
            "reports": MagicMock(),
            "analysis_results": MagicMock(),
            "priority_scores": MagicMock(),
        }
        mock_tables["incidents"].select.return_value.execute.return_value.data = mock_incidents
        mock_tables["reports"].select.return_value.in_.return_value.execute.return_value.data = []
        mock_tables["analysis_results"].select.return_value.in_.return_value.execute.return_value.data = []
        mock_tables["priority_scores"].select.return_value.in_.return_value.execute.return_value.data = []

        upsert_rows = []

        def capture_upsert(row, on_conflict=None):
            upsert_rows.append(row)
            m = MagicMock()
            m.execute.return_value = MagicMock()
            return m

        mock_tables["priority_scores"].upsert.side_effect = capture_upsert
        mock_supabase.table.side_effect = lambda name: mock_tables.get(name, MagicMock())

        with patch("app.services.priority_service.get_supabase_client", return_value=mock_supabase), \
             patch("app.utils.id_generator.get_supabase_client", return_value=mock_supabase), \
             patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
             patch("httpx.Client", side_effect=self.mock_client_factory):
            resp = PriorityService.get_priority_ranking(sort="urgency")

        assert len(resp.items) == 1
        assert len(upsert_rows) == 1
        synced_row = upsert_rows[0]
        assert synced_row["incident_id"] == "inc_001"
        assert synced_row["urgency_score"] == resp.items[0].urgency.score
        assert synced_row["evidence_confidence_score"] == resp.items[0].evidence_confidence.score
        assert synced_row["verification_priority_score"] == resp.items[0].verification_priority.score
        assert synced_row["requires_human_decision"] is True
        assert synced_row["human_decision_status"] == "not_decided"

    # -----------------------------------------------------------------------
    # 4. Safe Handling During AI Engine Downtime
    # -----------------------------------------------------------------------
    def test_e2e_downtime_safety_evidence_graph(self):
        """When AI Engine is offline, evidence-graph endpoint falls back to stored relationships without 500."""
        with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
             patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
            response = backend_client.get("/incidents/inc_001/evidence-graph")

        assert response.status_code == 200
        data = response.json()
        assert data["incident_id"] == "inc_001"
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)

    def test_e2e_downtime_safety_priority_ranking(self):
        """When AI Engine is offline, priority endpoint falls back to stored priority scores without 500."""
        with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
             patch("httpx.Client.post", side_effect=httpx.ConnectError("Connection refused")):
            response = backend_client.get("/incidents/priority?sort=urgency")

        assert response.status_code == 200
        data = response.json()
        assert data["sort"] == "urgency"
        assert isinstance(data["items"], list)

    # -----------------------------------------------------------------------
    # 5. Stage 6: Disaster Simulation via AI Engine & Downtime Safety
    # -----------------------------------------------------------------------
    def test_e2e_simulation_with_real_ai_engine(self):
        """Backend calls Member 3's AI Engine /simulation/run and receives contract-compliant SimulationResponse."""
        payload = {
            "scenario_name": "Stage 6 Joint E2E Simulation",
            "affected_population": 15000,
            "disaster_severity": 4,
            "rescue_teams": 5,
            "blocked_roads": 3,
            "available_ambulances": 4,
        }

        with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
             patch("httpx.Client", side_effect=self.mock_client_factory):
            response = backend_client.post("/simulate", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Contract Shape Verifications
        assert data["scenario_id"].startswith("sim_")
        assert data["is_simulation"] is True
        assert "generated_at" in data
        assert data["inputs"]["scenario_name"] == payload["scenario_name"]
        assert data["inputs"]["affected_population"] == 15000
        assert data["inputs"]["disaster_severity"] == 4

        results = data["results"]
        # AI Engine formulas check
        # demanded_teams = max(2, int((15000/1500)*(4/2.5))) = max(2, 16) = 16
        # demanded_ambulances = max(2, int((15000/2000)*(4/2.0))) = max(2, 15) = 15
        assert results["resource_demand"]["rescue_teams"] == 16
        assert results["resource_demand"]["ambulances"] == 15

        # Shortages: teams shortfall 16 - 5 = 11; amb shortfall 15 - 4 = 11
        assert len(results["shortages"]) == 2
        shortage_map = {s["resource"]: s["shortfall"] for s in results["shortages"]}
        assert shortage_map["rescue_teams"] == 11
        assert shortage_map["ambulances"] == 11

        # Delay: (blocked_roads * 5) + (team_shortfall * 2) = (3 * 5) + (11 * 2) = 15 + 22 = 37
        assert results["estimated_response_delay_minutes"] == 37
        assert isinstance(results["summary"], str)
        assert "37 minutes" in results["summary"]
        assert isinstance(results["priority_changes"], list)

    def test_e2e_simulation_with_real_ai_engine_and_incidents(self):
        """Backend passes active incident context to AI Engine /simulation/run and returns simulated rank changes."""
        mock_supabase = MagicMock()
        mock_tables = {
            "incidents": MagicMock(),
            "reports": MagicMock(),
            "simulations": MagicMock(),
        }
        mock_supabase.table.side_effect = lambda name: mock_tables.get(name, MagicMock())

        mock_tables["incidents"].select.return_value.execute.return_value.data = [
            {
                "id": "inc_alpha",
                "title": "Hospital Evacuation",
                "type": "medical",
                "severity": "critical",
                "status": "active",
                "lat": 12.9716,
                "lng": 77.5946,
                "location_label": "City Hospital",
                "report_count": 5,
                "first_reported_at": "2026-11-12T10:00:00Z",
                "last_updated_at": "2026-11-12T10:30:00Z",
                "timeline": [],
            },
            {
                "id": "inc_beta",
                "title": "Flooded Residential Block",
                "type": "flood",
                "severity": "high",
                "status": "active",
                "lat": 12.9750,
                "lng": 77.6000,
                "location_label": "East Block",
                "report_count": 2,
                "first_reported_at": "2026-11-12T10:15:00Z",
                "last_updated_at": "2026-11-12T10:45:00Z",
                "timeline": [],
            },
        ]
        mock_tables["reports"].select.return_value.in_.return_value.execute.return_value.data = []

        payload = {
            "scenario_name": "Active Incident Stress Test",
            "affected_population": 20000,
            "disaster_severity": 5,
            "rescue_teams": 3,
            "blocked_roads": 5,
            "available_ambulances": 2,
        }

        with patch("app.services.simulation_service.get_supabase_client", return_value=mock_supabase), \
             patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
             patch("httpx.Client", side_effect=self.mock_client_factory):
            response = backend_client.post("/simulate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["is_simulation"] is True
        assert "results" in data
        # Check simulation table was written
        mock_tables["simulations"].insert.assert_called_once()
        # Check real incidents table was NOT updated
        mock_tables["incidents"].update.assert_not_called()

    def test_e2e_downtime_safety_simulation(self):
        """When AI Engine is offline, backend simulation falls back to deterministic calculation without error."""
        payload = {
            "scenario_name": "Offline Engine Simulation",
            "affected_population": 6000,
            "disaster_severity": 3,
            "rescue_teams": 4,
            "blocked_roads": 2,
            "available_ambulances": 3,
        }

        mock_inner_client = MagicMock()
        mock_inner_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_inner_client.__enter__.return_value = mock_inner_client

        with patch("app.core.config.settings.AI_ENGINE_URL", "http://ai-engine:8001"), \
             patch("app.services.ai_client.httpx.Client", return_value=mock_inner_client):
            response = backend_client.post("/simulate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["is_simulation"] is True
        assert data["scenario_id"].startswith("sim_")
        assert "resource_demand" in data["results"]
        assert "shortages" in data["results"]
        assert "estimated_response_delay_minutes" in data["results"]
