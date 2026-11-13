"""Contract compliance tests for Pydantic schemas.

Validates that schemas strictly adhere to docs/api-contract.md specifications.
"""

import pytest
from pydantic import ValidationError

from ai_engine.schemas import (
    Location,
    UrgencyScore,
    EvidenceConfidenceScore,
    VerificationPriorityScore,
    Scores,
    Analysis,
    Report,
    Incident,
    PriorityResponse,
    EvidenceGraphResponse,
    SimulationRequest,
    SimulationResponse,
    SourceType,
    ReportStatus,
    FreshnessStatus,
    IncidentSeverity,
    ScoreLevelUrgency,
    ScoreLevelThree,
    RecommendationType,
    RelationshipType,
    Independence,
    CorroborationStatus,
    PrioritySort,
)


def test_location_schema():
    loc = Location(lat=12.9304, lng=77.6784, label="Lake Road, Bellandur")
    assert loc.lat == 12.9304
    assert loc.lng == 77.6784
    assert loc.label == "Lake Road, Bellandur"

    # Latitude out of bounds
    with pytest.raises(ValidationError):
        Location(lat=95.0, lng=77.0, label="Invalid")


def test_scores_separate_and_bounded():
    scores = Scores(
        urgency=UrgencyScore(score=90, level=ScoreLevelUrgency.CRITICAL, reasons=["People trapped"]),
        evidence_confidence=EvidenceConfidenceScore(score=80, level=ScoreLevelThree.HIGH, reasons=["Two sources"]),
        verification_priority=VerificationPriorityScore(score=25, level=ScoreLevelThree.LOW, reasons=["Corroborated"]),
    )
    assert scores.urgency.score == 90
    assert scores.urgency.level == "critical"
    assert scores.evidence_confidence.level == "high"
    assert scores.verification_priority.level == "low"

    # Score out of bounds (> 100)
    with pytest.raises(ValidationError):
        UrgencyScore(score=105, level=ScoreLevelUrgency.CRITICAL, reasons=[])


def test_analysis_contract_example():
    payload = {
        "analyzed_at": "2026-11-11T14:31:00Z",
        "engine_version": "0.1.0",
        "duplicate": {
            "is_duplicate": True,
            "matches": [
                {
                    "report_id": "rpt_001",
                    "similarity": 0.91,
                    "reasons": ["Same location", "Similar wording", "Within 10 minutes"],
                }
            ],
        },
        "source_verification": {
            "independence": "independent",
            "original_report_id": "rpt_001",
            "related": [{"report_id": "rpt_001", "relation": "duplicate"}],
            "corroboration_status": "corroborated",
        },
        "freshness": {
            "status": "recent",
            "age_minutes": 18,
            "last_updated": "2026-11-11T14:13:00Z",
        },
        "conflicts": [
            {
                "id": "cfl_001",
                "topic": "Extent of damage",
                "report_ids": ["rpt_005", "rpt_006"],
                "statements": [
                    {"report_id": "rpt_005", "text": "Building collapsed, people trapped"},
                    {"report_id": "rpt_006", "text": "Only the compound wall fell, nobody trapped"},
                ],
                "detected_at": "2026-11-11T14:20:00Z",
            }
        ],
        "scores": {
            "urgency": {"score": 90, "level": "critical", "reasons": ["People reported trapped"]},
            "evidence_confidence": {"score": 80, "level": "high", "reasons": ["Two independent sources"]},
            "verification_priority": {"score": 25, "level": "low", "reasons": ["Already corroborated"]},
        },
        "recommendation": {
            "type": "monitor",
            "summary": "Evidence is strong. Pass to a human responder for a decision.",
            "next_steps": ["Notify duty officer", "Re-check in 30 minutes"],
            "requires_human_decision": True,
        },
    }

    analysis = Analysis.model_validate(payload)
    assert analysis.engine_version == "0.1.0"
    assert analysis.recommendation.requires_human_decision is True
    assert analysis.duplicate.matches[0].similarity == 0.91
    assert analysis.source_verification.corroboration_status == CorroborationStatus.CORROBORATED


def test_human_decision_must_be_true():
    """Validates that requires_human_decision cannot be set to False."""
    payload = {
        "analyzed_at": "2026-11-11T14:31:00Z",
        "engine_version": "0.1.0",
        "duplicate": {"is_duplicate": False, "matches": []},
        "source_verification": {
            "independence": "unknown",
            "original_report_id": None,
            "related": [],
            "corroboration_status": "single_source",
        },
        "freshness": {"status": "recent", "age_minutes": 5, "last_updated": "2026-11-11T14:13:00Z"},
        "conflicts": [],
        "scores": {
            "urgency": {"score": 50, "level": "medium", "reasons": []},
            "evidence_confidence": {"score": 50, "level": "medium", "reasons": []},
            "verification_priority": {"score": 50, "level": "medium", "reasons": []},
        },
        "recommendation": {
            "type": "monitor",
            "summary": "Summary",
            "next_steps": [],
            "requires_human_decision": False,  # Should fail
        },
    }
    with pytest.raises(ValidationError):
        Analysis.model_validate(payload)


def test_evidence_graph_contract_example():
    payload = {
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
            }
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
    graph = EvidenceGraphResponse.model_validate(payload)
    assert graph.incident_id == "inc_001"
    assert len(graph.nodes) == 1
    assert graph.edges[0].source == "rpt_002"
    assert graph.edges[0].target == "rpt_001"


def test_priority_response_contract_example():
    payload = {
        "sort": "urgency",
        "items": [
            {
                "rank": 1,
                "incident_id": "inc_001",
                "title": "Flooding near Bellandur lake road",
                "location": {"lat": 12.9304, "lng": 77.6784, "label": "Lake Road, Bellandur"},
                "urgency": {"score": 92, "level": "critical", "reasons": ["Elderly residents reported on upper floors"]},
                "evidence_confidence": {"score": 84, "level": "high", "reasons": ["Three independent sources"]},
                "verification_priority": {"score": 25, "level": "low", "reasons": ["Well corroborated"]},
                "explanation": ["Water level reported at 1.2 m", "Official source confirms"],
                "recommended_next_steps": ["Alert duty officer for dispatch review"],
                "requires_human_decision": True,
                "human_decision": {"status": "not_decided", "decided_by": None, "decided_at": None},
            }
        ],
    }
    res = PriorityResponse.model_validate(payload)
    assert res.sort == PrioritySort.URGENCY
    assert res.items[0].human_decision.status == "not_decided"


def test_simulation_contract_example():
    req_payload = {
        "scenario_name": "Heavy rain, 3 roads blocked",
        "affected_population": 12000,
        "disaster_severity": 4,
        "rescue_teams": 6,
        "blocked_roads": 3,
        "available_ambulances": 5,
    }
    req = SimulationRequest.model_validate(req_payload)
    assert req.disaster_severity == 4

    res_payload = {
        "scenario_id": "sim_001",
        "is_simulation": True,
        "generated_at": "2026-11-11T14:45:00Z",
        "inputs": req_payload,
        "results": {
            "resource_demand": {"rescue_teams": 10, "ambulances": 8},
            "shortages": [{"resource": "rescue_teams", "required": 10, "available": 6, "shortfall": 4}],
            "estimated_response_delay_minutes": 15,
            "priority_changes": [
                {
                    "incident_id": "inc_002",
                    "title": "Reported structural collapse, Koramangala",
                    "baseline_rank": 2,
                    "scenario_rank": 1,
                    "reason": "Access roads blocked, fewer teams available",
                }
            ],
            "summary": "Rescue teams are short by 4 under this scenario.",
        },
    }
    sim = SimulationResponse.model_validate(res_payload)
    assert sim.is_simulation is True
    assert sim.results.resource_demand.rescue_teams == 10
