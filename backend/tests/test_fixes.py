"""
CrisisLens Targeted Fix Tests
Tests for the four targeted fixes:
  1. Priority score persistence
  2. Evidence graph — no invented edges, correct role classification
  3. Simulation isolation — no hardcoded incident IDs
  4. AI fallback transparency — engine_version distinguishable
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_report(overrides=None):
    """Return a minimal report dict for deterministic analysis tests."""
    base = {
        "id": "rpt_test_001",
        "incident_id": "inc_test_001",
        "text": "Building on fire at test location with trapped residents",
        "source_type": "citizen",
        "source_name": "Test Citizen",
        "location_label": "Test Location",
        "reported_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending_analysis",
        "forwarded_from": None,
    }
    if overrides:
        base.update(overrides)
    return base


def _make_analysis_data():
    """Return a minimal valid analysis data dict (matches AnalysisObject)."""
    return {
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "engine_version": "deterministic-fallback-0.1.0",
        "duplicate": {"is_duplicate": False, "matches": []},
        "source_verification": {
            "independence": "independent",
            "original_report_id": None,
            "related": [],
            "corroboration_status": "single_source",
        },
        "freshness": {"status": "recent", "age_minutes": 5, "last_updated": datetime.now(timezone.utc).isoformat()},
        "conflicts": [],
        "scores": {
            "urgency": {"score": 65, "level": "medium", "reasons": ["Moderate hazard"]},
            "evidence_confidence": {"score": 50, "level": "medium", "reasons": ["Citizen report"]},
            "verification_priority": {"score": 55, "level": "medium", "reasons": ["Single source"]},
        },
        "recommendation": {
            "type": "monitor",
            "summary": "Monitor situation",
            "next_steps": ["Maintain surveillance"],
            "requires_human_decision": True,
        },
    }


# ---------------------------------------------------------------------------
# 1. Priority score persistence
# ---------------------------------------------------------------------------

class TestPriorityScorePersistence:
    """Priority scores must be written to priority_scores table after analysis."""

    def test_priority_row_upserted_after_analysis(self):
        """After analyze_report runs, priority_scores.upsert must be called with correct scores."""
        from app.services.analysis_service import AnalysisService
        import asyncio

        mock_supabase = MagicMock()
        analysis_data = _make_analysis_data()
        target_report = _make_report()

        # Stub DB calls
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [target_report]
        mock_supabase.table.return_value.select.return_value.neq.return_value.limit.return_value.execute.return_value.data = []
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        # Capture upsert calls
        upsert_calls = []
        def capture_upsert(row, on_conflict=None):
            upsert_calls.append((row, on_conflict))
            return mock_supabase.table.return_value

        mock_supabase.table.return_value.upsert = capture_upsert
        mock_supabase.table.return_value.execute.return_value = MagicMock()

        with patch("app.services.analysis_service.get_supabase_client", return_value=mock_supabase), \
             patch("app.services.analysis_service.AIClient.analyze_report", new=AsyncMock(return_value=analysis_data)), \
             patch("app.services.analysis_service.ReportService.get_report_by_id", return_value=MagicMock()):
            asyncio.run(AnalysisService.analyze_report("rpt_test_001"))

        # At least one upsert to priority_scores must have happened
        assert len(upsert_calls) >= 1, "priority_scores.upsert was never called"
        priority_row, conflict_col = upsert_calls[0]
        assert conflict_col == "incident_id", f"Expected on_conflict='incident_id', got {conflict_col!r}"
        assert priority_row["incident_id"] == "inc_test_001"
        assert priority_row["urgency_score"] == 65
        assert priority_row["evidence_confidence_score"] == 50
        assert priority_row["verification_priority_score"] == 55
        assert priority_row["urgency_level"] == "medium"
        assert priority_row["requires_human_decision"] is True
        assert priority_row["human_decision_status"] == "not_decided"

    def test_no_upsert_when_incident_id_missing(self):
        """If the report has no incident_id, no priority_scores upsert must occur."""
        from app.services.analysis_service import AnalysisService
        import asyncio

        report_no_inc = _make_report({"incident_id": None})
        mock_supabase = MagicMock()
        analysis_data = _make_analysis_data()

        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [report_no_inc]
        mock_supabase.table.return_value.select.return_value.neq.return_value.limit.return_value.execute.return_value.data = []
        mock_supabase.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()

        upsert_calls = []
        mock_supabase.table.return_value.upsert = lambda row, **kw: upsert_calls.append(row) or mock_supabase.table.return_value

        with patch("app.services.analysis_service.get_supabase_client", return_value=mock_supabase), \
             patch("app.services.analysis_service.AIClient.analyze_report", new=AsyncMock(return_value=analysis_data)), \
             patch("app.services.analysis_service.ReportService.get_report_by_id", return_value=MagicMock()):
            asyncio.run(AnalysisService.analyze_report("rpt_test_001"))

        assert len(upsert_calls) == 0, "upsert should not be called when incident_id is None"


# ---------------------------------------------------------------------------
# 2. Evidence graph — no invented edges
# ---------------------------------------------------------------------------

class TestEvidenceGraphNoInventedEdges:
    """Evidence graph must only return stored edges, never synthetic ones."""

    def test_no_edges_when_no_relationships_stored(self):
        """Two reports with no stored relationships → edges must be []."""
        from app.services.evidence_service import EvidenceService

        mock_supabase = MagicMock()
        reports = [
            _make_report({"id": "rpt_A", "incident_id": "inc_X", "reported_at": "2026-01-01T10:00:00+00:00"}),
            _make_report({"id": "rpt_B", "incident_id": "inc_X", "reported_at": "2026-01-01T10:05:00+00:00"}),
        ]

        # incidents → found
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "inc_X", "location_label": "Test", "status": "active"}
        ]
        # reports → both reports
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = reports
        # relationships → empty (none stored)
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []

        with patch("app.services.evidence_service.get_supabase_client", return_value=mock_supabase):
            result = EvidenceService.get_evidence_graph("inc_X")

        assert result.edges == [], f"Expected no edges, got {result.edges}"
        assert len(result.nodes) == 2

    def test_node_id_equals_report_id(self):
        """Node IDs must equal the report IDs."""
        from app.services.evidence_service import EvidenceService

        mock_supabase = MagicMock()
        reports = [
            _make_report({"id": "rpt_A", "incident_id": "inc_X", "reported_at": "2026-01-01T10:00:00+00:00"}),
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "inc_X", "location_label": "Test"}
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = reports
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []

        with patch("app.services.evidence_service.get_supabase_client", return_value=mock_supabase):
            result = EvidenceService.get_evidence_graph("inc_X")

        assert result.nodes[0].id == "rpt_A"
        assert result.nodes[0].report_id == "rpt_A"

    def test_forwarded_report_role(self):
        """A report with forwarded_from set must have role='forwarded'."""
        from app.services.evidence_service import EvidenceService
        from app.schemas.common import RelationshipType

        mock_supabase = MagicMock()
        reports = [
            _make_report({"id": "rpt_A", "incident_id": "inc_X", "forwarded_from": "rpt_orig",
                          "reported_at": "2026-01-01T10:00:00+00:00"}),
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "inc_X", "location_label": "Test"}
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = reports
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []

        with patch("app.services.evidence_service.get_supabase_client", return_value=mock_supabase):
            result = EvidenceService.get_evidence_graph("inc_X")

        assert result.nodes[0].role == RelationshipType.FORWARDED

    def test_stored_edge_direction(self):
        """Stored edge direction: source=later report, target=earlier report."""
        from app.services.evidence_service import EvidenceService

        mock_supabase = MagicMock()
        reports = [
            _make_report({"id": "rpt_A", "incident_id": "inc_X", "reported_at": "2026-01-01T10:00:00+00:00"}),
            _make_report({"id": "rpt_B", "incident_id": "inc_X", "reported_at": "2026-01-01T10:05:00+00:00"}),
        ]
        stored_edge = {
            "id": "edge_001",
            "source_report_id": "rpt_B",   # later (derived)
            "target_report_id": "rpt_A",   # earlier (reference)
            "type": "corroborating",
            "confidence": 0.8,
            "label": "Corroborating (0.80)",
        }
        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "inc_X", "location_label": "Test"}
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = reports
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.data = [stored_edge]

        with patch("app.services.evidence_service.get_supabase_client", return_value=mock_supabase):
            result = EvidenceService.get_evidence_graph("inc_X")

        assert len(result.edges) == 1
        assert result.edges[0].source == "rpt_B"
        assert result.edges[0].target == "rpt_A"


# ---------------------------------------------------------------------------
# 3. Simulation isolation — no hardcoded incident IDs
# ---------------------------------------------------------------------------

class TestSimulationIsolation:

    def _run_simulation(self, payload_overrides=None):
        from app.services.simulation_service import SimulationService
        from app.schemas.simulation import SimulationRequest

        payload = SimulationRequest(
            scenario_name="Test scenario",
            affected_population=5000,
            disaster_severity=5.0,
            rescue_teams=3,
            available_ambulances=2,
            blocked_roads=3,
            **(payload_overrides or {}),
        )
        mock_supabase = MagicMock()
        # Return empty incidents so priority_changes must be []
        mock_supabase.table.return_value.select.return_value.execute.return_value.data = []
        mock_supabase.table.return_value.insert.return_value.execute.return_value = MagicMock()

        with patch("app.services.simulation_service.get_supabase_client", return_value=mock_supabase):
            return SimulationService.run_simulation(payload)

    def test_is_simulation_always_true(self):
        result = self._run_simulation()
        assert result.is_simulation is True

    def test_no_real_incident_mutation(self):
        """Running a simulation must not write to incidents or reports tables."""
        from app.services.simulation_service import SimulationService
        from app.schemas.simulation import SimulationRequest

        payload = SimulationRequest(
            scenario_name="Isolation test",
            affected_population=1000,
            disaster_severity=3.0,
            rescue_teams=2,
            available_ambulances=2,
            blocked_roads=1,
        )
        mock_supabase = MagicMock()
        tables_written = []

        original_table = mock_supabase.table

        def spy_table(name):
            tbl = MagicMock()
            if name in ("incidents", "reports"):
                tbl.insert.side_effect = lambda *a, **kw: tables_written.append(name)
                tbl.update.side_effect = lambda *a, **kw: tables_written.append(name)
                tbl.delete.side_effect = lambda *a, **kw: tables_written.append(name)
            tbl.select.return_value.execute.return_value.data = []
            tbl.insert.return_value.execute.return_value = MagicMock()
            return tbl

        mock_supabase.table = spy_table

        with patch("app.services.simulation_service.get_supabase_client", return_value=mock_supabase):
            SimulationService.run_simulation(payload)

        assert tables_written == [], f"Simulation wrote to protected tables: {tables_written}"

    def test_no_hardcoded_inc_002(self):
        """Priority changes must never contain the hardcoded 'inc_002' ID."""
        result = self._run_simulation()
        hardcoded_ids = [pc.incident_id for pc in result.results.priority_changes if pc.incident_id == "inc_002"]
        assert hardcoded_ids == [], f"Hardcoded inc_002 found in priority_changes: {hardcoded_ids}"

    def test_empty_priority_changes_when_no_incidents(self):
        """When DB has no incidents, priority_changes must be empty."""
        result = self._run_simulation()
        assert result.results.priority_changes == []

    def test_scenario_id_present(self):
        result = self._run_simulation()
        assert result.scenario_id.startswith("sim_")


# ---------------------------------------------------------------------------
# 4. AI fallback transparency
# ---------------------------------------------------------------------------

class TestAIFallbackTransparency:

    def test_fallback_engine_version_prefix(self):
        """When AI engine is unreachable, engine_version must start with 'deterministic-fallback'."""
        from app.services.ai_client import AIClient
        import asyncio

        report = _make_report()

        with patch("app.services.ai_client.settings") as mock_settings:
            mock_settings.AI_ENGINE_URL = "http://nonexistent-engine:9999"
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client_cls.return_value.__aenter__.side_effect = Exception("Connection refused")
                result = asyncio.run(AIClient.analyze_report(report, []))

        assert result["engine_version"].startswith("deterministic-fallback"), \
            f"Expected 'deterministic-fallback-*', got: {result['engine_version']!r}"

    def test_fallback_result_validates_analysis_object(self):
        """Fallback result must pass full AnalysisObject Pydantic validation."""
        from app.services.ai_client import AIClient
        from app.schemas.analysis import AnalysisObject
        import asyncio

        report = _make_report()

        with patch("app.services.ai_client.settings") as mock_settings:
            mock_settings.AI_ENGINE_URL = None  # No engine configured
            result = asyncio.run(AIClient.analyze_report(report, []))

        # Must not raise
        validated = AnalysisObject.model_validate(result)
        assert validated.engine_version.startswith("deterministic-fallback")

    def test_real_ai_response_returned_when_available(self):
        """When AI engine returns 200, its response (not fallback) is returned."""
        from app.services.ai_client import AIClient
        from app.schemas.analysis import AnalysisObject
        import asyncio

        report = _make_report()
        # Build a fully valid AnalysisObject payload so Pydantic validation passes
        ai_response = _make_analysis_data()
        ai_response["engine_version"] = "ai-engine-1.0.0"  # Real engine version

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = ai_response

        # Build a proper async context manager mock for httpx.AsyncClient
        async def mock_post(*args, **kwargs):
            return mock_response

        class MockAsyncClient:
            async def __aenter__(self):
                self.post = mock_post
                return self
            async def __aexit__(self, *args):
                return None

        with patch("app.services.ai_client.settings") as mock_settings:
            mock_settings.AI_ENGINE_URL = "http://ai-engine:8001"
            with patch("app.services.ai_client.httpx.AsyncClient", return_value=MockAsyncClient()):
                result = asyncio.run(AIClient.analyze_report(report, []))

        assert result["engine_version"] == "ai-engine-1.0.0", \
            f"Expected real engine version, got: {result['engine_version']!r}"

    def test_fallback_still_valid_on_timeout(self):
        """On timeout, fallback result is returned and passes Pydantic validation."""
        import httpx
        from app.services.ai_client import AIClient
        from app.schemas.analysis import AnalysisObject
        import asyncio

        report = _make_report()

        with patch("app.services.ai_client.settings") as mock_settings:
            mock_settings.AI_ENGINE_URL = "http://ai-engine:8001"
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_instance = AsyncMock()
                mock_instance.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)
                result = asyncio.run(AIClient.analyze_report(report, []))

        validated = AnalysisObject.model_validate(result)
        assert validated.engine_version.startswith("deterministic-fallback")


# ---------------------------------------------------------------------------
# 5. Freshness thresholds
# ---------------------------------------------------------------------------

class TestFreshnessThresholds:

    def _freshness(self, minutes_ago: int) -> dict:
        from app.utils.datetime_utils import calculate_freshness
        ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
        return calculate_freshness(ts)

    def test_recent_at_60_minutes(self):
        result = self._freshness(60)
        assert result["status"] == "recent", f"Expected 'recent', got {result['status']!r}"

    def test_aging_at_61_minutes(self):
        result = self._freshness(61)
        assert result["status"] in ("aging", "stale"), f"Expected 'aging' or 'stale', got {result['status']!r}"

    def test_stale_at_241_minutes(self):
        result = self._freshness(241)
        assert result["status"] == "stale", f"Expected 'stale', got {result['status']!r}"


# ---------------------------------------------------------------------------
# 6. Priority retrieval & missing scores
# ---------------------------------------------------------------------------

class TestPriorityRetrieval:

    def test_priority_retrieval_with_stored_scores(self):
        """Priority dashboard retrieves actual stored scores from priority_scores."""
        from app.services.priority_service import PriorityService

        mock_supabase = MagicMock()
        mock_incidents = [
            {
                "id": "inc_001",
                "title": "Bellandur Flood",
                "type": "flood",
                "severity": "critical",
                "status": "active",
                "lat": 12.93,
                "lng": 77.67,
                "location_label": "Bellandur",
                "independent_source_count": 3,
            }
        ]
        mock_stored_scores = [
            {
                "id": "pri_001",
                "incident_id": "inc_001",
                "urgency_score": 95,
                "urgency_level": "critical",
                "urgency_reasons": ["Water level reached 2m"],
                "evidence_confidence_score": 88,
                "evidence_confidence_level": "high",
                "evidence_confidence_reasons": ["Multiple official confirmations"],
                "verification_priority_score": 20,
                "verification_priority_level": "low",
                "verification_priority_reasons": ["Already corroborated"],
                "explanation": ["Critical water level"],
                "recommended_next_steps": ["Deploy rescue boat"],
                "human_decision_status": "not_decided",
            }
        ]

        mock_supabase.table.return_value.select.return_value.execute.return_value.data = mock_incidents
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.data = mock_stored_scores

        with patch("app.services.priority_service.get_supabase_client", return_value=mock_supabase):
            resp = PriorityService.get_priority_ranking(sort="urgency")

        assert len(resp.items) == 1
        item = resp.items[0]
        assert item.urgency.score == 95
        assert item.urgency.level == "critical"
        assert item.urgency.reasons == ["Water level reached 2m"]
        assert item.evidence_confidence.score == 88
        assert item.verification_priority.score == 20
        assert item.recommended_next_steps == ["Deploy rescue boat"]

    def test_missing_priority_scores_handled_transparently(self):
        """When priority_scores table has no entry, computes graceful baseline scores."""
        from app.services.priority_service import PriorityService

        mock_supabase = MagicMock()
        mock_incidents = [
            {
                "id": "inc_new",
                "title": "New Incident",
                "type": "fire",
                "severity": "high",
                "status": "active",
                "lat": 12.95,
                "lng": 77.65,
                "location_label": "Indiranagar",
                "independent_source_count": 1,
            }
        ]
        mock_supabase.table.return_value.select.return_value.execute.return_value.data = mock_incidents
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.data = []

        with patch("app.services.priority_service.get_supabase_client", return_value=mock_supabase):
            resp = PriorityService.get_priority_ranking(sort="urgency")

        assert len(resp.items) == 1
        item = resp.items[0]
        assert 0 <= item.urgency.score <= 100
        assert 0 <= item.evidence_confidence.score <= 100
        assert 0 <= item.verification_priority.score <= 100
        assert item.human_decision.status == "not_decided"
        assert item.requires_human_decision is True


# ---------------------------------------------------------------------------
# 7. Duplicate vs corroborating relationships & forwarded independence
# ---------------------------------------------------------------------------

class TestRelationshipsAndIndependence:

    def test_duplicate_versus_corroborating_role_assignment(self):
        """Reports are classified as DUPLICATE or CORROBORATING based on stored relationships."""
        from app.services.evidence_service import EvidenceService
        from app.schemas.common import RelationshipType

        mock_supabase = MagicMock()
        reports = [
            _make_report({"id": "rpt_1", "incident_id": "inc_Y", "reported_at": "2026-01-01T10:00:00+00:00"}),
            _make_report({"id": "rpt_2", "incident_id": "inc_Y", "reported_at": "2026-01-01T10:05:00+00:00"}),
            _make_report({"id": "rpt_3", "incident_id": "inc_Y", "reported_at": "2026-01-01T10:10:00+00:00"}),
        ]
        edges = [
            {
                "id": "edge_dup",
                "source_report_id": "rpt_2",
                "target_report_id": "rpt_1",
                "type": "duplicate",
                "confidence": 0.95,
                "label": "Duplicate (0.95)",
            },
            {
                "id": "edge_corrob",
                "source_report_id": "rpt_3",
                "target_report_id": "rpt_1",
                "type": "corroborating",
                "confidence": 0.85,
                "label": "Corroborating (0.85)",
            },
        ]

        mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "inc_Y", "location_label": "Yelahanka"}
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = reports
        mock_supabase.table.return_value.select.return_value.in_.return_value.execute.return_value.data = edges

        with patch("app.services.evidence_service.get_supabase_client", return_value=mock_supabase):
            res = EvidenceService.get_evidence_graph("inc_Y")

        node_map = {n.id: n for n in res.nodes}
        assert node_map["rpt_1"].role == RelationshipType.ORIGINAL
        assert node_map["rpt_2"].role == RelationshipType.DUPLICATE
        assert node_map["rpt_3"].role == RelationshipType.CORROBORATING
        assert len(res.edges) == 2

    def test_forwarded_report_not_independent(self):
        """Forwarded copy reduces confidence score and sets independence to forwarded."""
        from app.services.ai_client import AIClient

        rpt_forwarded = _make_report({
            "id": "rpt_fwd",
            "text": "FWD: Water entering houses on Lake Road, urgent!",
            "forwarded_from": "rpt_orig",
        })
        existing = [_make_report({"id": "rpt_orig", "text": "Water entering houses on Lake Road, urgent!"})]

        analysis = AIClient._compute_deterministic_analysis(rpt_forwarded, existing)

        assert analysis["source_verification"]["independence"] == "forwarded"
        assert analysis["source_verification"]["corroboration_status"] != "corroborated"
        # Forwarded deduction is -30, ensuring confidence reflects non-independent copy
        reasons = analysis["scores"]["evidence_confidence"]["reasons"]
        assert any("Forwarded" in r for r in reasons)

    def test_conflicting_reports_detection(self):
        """Contradictory witness statements generate conflict items and increase verification priority."""
        from app.services.ai_client import AIClient

        rpt_collapse = _make_report({
            "id": "rpt_col",
            "text": "Severe building collapse on 5th main, 10 people trapped inside",
        })
        existing = [
            _make_report({
                "id": "rpt_wall",
                "text": "Only compound wall fell at 5th main, no collapse and nobody trapped",
            })
        ]

        analysis = AIClient._compute_deterministic_analysis(rpt_collapse, existing)

        assert len(analysis["conflicts"]) >= 1
        conflict = analysis["conflicts"][0]
        assert "rpt_col" in conflict["report_ids"]
        assert "rpt_wall" in conflict["report_ids"]
        assert analysis["recommendation"]["type"] == "verify_first"
        assert any("contradiction" in r.lower() for r in analysis["scores"]["verification_priority"]["reasons"])

