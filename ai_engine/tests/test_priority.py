"""Tests for CrisisLens Priority Ranking Engine (Stage 5).

Validates:
- API Contract v1.0 Section 4.7 compliance
- Three separate scores: Urgency, Evidence Confidence, Verification Priority
- Deterministic ranking: urgency sort vs. verification sort
- Deterministic tie-breaking: primary score -> secondary score -> incident_id
- Human-in-the-loop: requires_human_decision=True, status="not_decided"
- Threat preservation: severe active threats not diluted by simple averaging
- Provenance & conflict integrity: forwarded copies not counted as independent; conflicts increase verification priority
- Missing optional report data handling
- Response schema compatibility with backend/app/schemas/priority.py
- FastAPI endpoints: POST /incidents/priority, POST /priority/rank, query override precedence, and error handling
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend can be imported for schema compatibility checks
backend_path = Path.cwd() / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from ai_engine.main import app
from ai_engine.schemas.enums import (
    PrioritySort,
    ScoreLevelUrgency,
    ScoreLevelThree,
    IncidentSeverity,
    IncidentStatus,
    FreshnessStatus,
    Independence,
    CorroborationStatus,
    RecommendationType,
    SourceType,
)
from ai_engine.schemas.internal import IncidentInput, ReportInput, PriorityRankRequest
from ai_engine.schemas.analysis import (
    ConflictItem,
    ConflictStatement,
    Analysis,
    DuplicateInfo,
    SourceVerification,
    FreshnessInfo,
    Recommendation,
)
from ai_engine.schemas.common import Scores, UrgencyScore, EvidenceConfidenceScore, VerificationPriorityScore
from ai_engine.schemas.incident import TimelineEntry, PriorityResponse
from ai_engine.modules.priority import IncidentPriorityRanker

from app.schemas.priority import PriorityResponse as BackendPriorityResponse

client = TestClient(app)


def test_empty_incident_batch():
    """Verify that an empty list of incidents returns an empty items list without error."""
    response = IncidentPriorityRanker.rank_incidents(
        incidents=[],
        sort=PrioritySort.URGENCY,
    )
    assert response.sort == PrioritySort.URGENCY
    assert response.items == []


def test_single_incident_ranking():
    """Verify that a single incident is ranked at rank 1 with all three separate scores."""
    incident = IncidentInput(
        id="inc_001",
        title="Flooding on Lake Road",
        type="flood",
        severity="high",
        status="active",
        location_label="Lake Road, Bellandur",
        lat=12.9304,
        lng=77.6784,
        independent_source_count=2,
    )

    response = IncidentPriorityRanker.rank_incidents(
        incidents=[incident],
        sort=PrioritySort.URGENCY,
    )

    assert len(response.items) == 1
    item = response.items[0]
    assert item.rank == 1
    assert item.incident_id == "inc_001"
    assert item.title == "Flooding on Lake Road"
    assert item.location.label == "Lake Road, Bellandur"

    # Verify scores are valid and bounded
    assert 0 <= item.urgency.score <= 100
    assert 0 <= item.evidence_confidence.score <= 100
    assert 0 <= item.verification_priority.score <= 100

    # Verify human supervision invariant
    assert item.requires_human_decision is True
    assert item.human_decision.status == "not_decided"
    assert item.human_decision.decided_by is None

    # Verify explanations and next steps
    assert len(item.explanation) >= 2
    assert len(item.recommended_next_steps) >= 1


def test_multiple_incidents_urgency_sorting():
    """Verify that sort='urgency' sorts descending by urgency score."""
    inc_low = IncidentInput(
        id="inc_low",
        title="Minor waterlogging",
        type="flood",
        severity="low",
        status="active",
        location_label="Indiranagar",
        independent_source_count=1,
    )
    inc_critical = IncidentInput(
        id="inc_crit",
        title="Building structural collapse",
        type="structural",
        severity="critical",
        status="active",
        location_label="Bellandur",
        independent_source_count=3,
    )
    inc_medium = IncidentInput(
        id="inc_med",
        title="Tree branch on road",
        type="other",
        severity="medium",
        status="active",
        location_label="Koramangala",
        independent_source_count=1,
    )

    response = IncidentPriorityRanker.rank_incidents(
        incidents=[inc_low, inc_critical, inc_medium],
        sort=PrioritySort.URGENCY,
    )

    assert len(response.items) == 3
    assert response.items[0].incident_id == "inc_crit"
    assert response.items[0].rank == 1
    assert response.items[1].incident_id == "inc_med"
    assert response.items[1].rank == 2
    assert response.items[2].incident_id == "inc_low"
    assert response.items[2].rank == 3

    # Invariant: monotonic descending urgency scores
    for i in range(len(response.items) - 1):
        assert response.items[i].urgency.score >= response.items[i + 1].urgency.score


def test_multiple_incidents_verification_sorting():
    """Verify that sort='verification' sorts descending by verification priority score."""
    # Incident A: High urgency, high confidence -> low verification priority
    inc_a = IncidentInput(
        id="inc_a",
        title="Corroborated flooding",
        type="flood",
        severity="high",
        status="active",
        location_label="HSR Layout",
        independent_source_count=3,
    )

    # Incident B: Critical urgency, 0 independent sources -> high verification priority
    inc_b = IncidentInput(
        id="inc_b",
        title="Rumored hospital flooding with trapped patients",
        type="flood",
        severity="critical",
        status="active",
        location_label="Bellandur",
        independent_source_count=0,
    )

    response = IncidentPriorityRanker.rank_incidents(
        incidents=[inc_a, inc_b],
        sort=PrioritySort.VERIFICATION,
    )

    assert response.sort == PrioritySort.VERIFICATION
    assert response.items[0].incident_id == "inc_b"
    assert response.items[0].rank == 1
    assert response.items[1].incident_id == "inc_a"
    assert response.items[1].rank == 2

    assert response.items[0].verification_priority.score >= response.items[1].verification_priority.score


def test_deterministic_tie_breaking():
    """Verify deterministic tie-breaking: identical primary scores sort by secondary, then incident_id."""
    # Two incidents with identical severity and identical independent source counts
    inc_2 = IncidentInput(
        id="inc_002",
        title="Incident 2",
        type="flood",
        severity="high",
        status="active",
        location_label="Area 2",
        independent_source_count=2,
    )
    inc_1 = IncidentInput(
        id="inc_001",
        title="Incident 1",
        type="flood",
        severity="high",
        status="active",
        location_label="Area 1",
        independent_source_count=2,
    )

    # Pass in reverse order [inc_2, inc_1]
    res_1 = IncidentPriorityRanker.rank_incidents(
        incidents=[inc_2, inc_1],
        sort=PrioritySort.URGENCY,
    )
    # Pass in forward order [inc_1, inc_2]
    res_2 = IncidentPriorityRanker.rank_incidents(
        incidents=[inc_1, inc_2],
        sort=PrioritySort.URGENCY,
    )

    # Both must produce identical tie-broken ranking with inc_001 first
    assert res_1.items[0].incident_id == "inc_001"
    assert res_1.items[1].incident_id == "inc_002"
    assert res_2.items[0].incident_id == "inc_001"
    assert res_2.items[1].incident_id == "inc_002"


def test_rank_numbering_one_based():
    """Verify that rank numbering is strictly 1-based and contiguous (1, 2, 3, ...)."""
    incidents = [
        IncidentInput(id=f"inc_{i}", title=f"Inc {i}", type="flood", severity="medium", status="active", location_label=f"Loc {i}")
        for i in range(5)
    ]
    response = IncidentPriorityRanker.rank_incidents(incidents=incidents)
    ranks = [item.rank for item in response.items]
    assert ranks == [1, 2, 3, 4, 5]


def test_high_urgency_low_confidence_elevates_verification_priority():
    """Verify that a high urgency combined with low evidence confidence elevates verification priority."""
    # Incident with life threat but unverified single citizen report
    rep = ReportInput(
        id="rpt_001",
        text="People trapped in basement with rapidly rising flood water! Send rescue!",
        source_type="citizen",
        source_name="Anonymous Citizen",
        location_label="Lake Road",
        reported_at="2026-11-12T14:00:00Z",
    )
    incident = IncidentInput(
        id="inc_unverified_trap",
        title="Basement trapped individuals",
        type="flood",
        severity="critical",
        status="active",
        location_label="Lake Road",
        reports=[rep],
        independent_source_count=0,
    )

    urgency, confidence, verification, _, _ = IncidentPriorityRanker.compute_incident_scores(incident)

    # Urgency must be high or critical
    assert urgency.score >= 85
    assert urgency.level == ScoreLevelUrgency.CRITICAL

    # Confidence must be low or moderate
    assert confidence.score <= 50

    # Verification priority must spike due to the discrepancy (Verify-First signal)
    assert verification.score >= 70
    assert verification.level == ScoreLevelThree.HIGH
    assert any("High urgency situation lacking robust verification" in r for r in verification.reasons)


def test_explicit_conflicts_increase_verification_priority():
    """Verify that explicit conflicts increase verification priority and penalize confidence."""
    conflict = ConflictItem(
        id="cfl_001",
        topic="Extent of structural damage",
        report_ids=["rpt_001", "rpt_002"],
        statements=[
            ConflictStatement(report_id="rpt_001", text="Entire building collapsed"),
            ConflictStatement(report_id="rpt_002", text="Only compound wall fell"),
        ],
        detected_at="2026-11-12T14:10:00Z",
    )

    incident_clean = IncidentInput(
        id="inc_clean",
        title="Building incident without conflict",
        type="structural",
        severity="high",
        status="active",
        location_label="Lake Road",
        independent_source_count=2,
    )
    incident_conflicted = IncidentInput(
        id="inc_conflict",
        title="Building incident with contradictory damage reports",
        type="structural",
        severity="high",
        status="active",
        location_label="Lake Road",
        independent_source_count=2,
        conflicts=[conflict],
    )

    _, conf_clean, ver_clean, _, _ = IncidentPriorityRanker.compute_incident_scores(incident_clean)
    _, conf_cfl, ver_cfl, _, _ = IncidentPriorityRanker.compute_incident_scores(incident_conflicted)

    # Conflicted incident must have lower evidence confidence and higher verification priority
    assert conf_cfl.score < conf_clean.score
    assert ver_cfl.score > ver_clean.score
    assert any("Contradictory witness statements" in r for r in ver_cfl.reasons)


def test_forwarded_reports_not_counted_as_independent():
    """Verify forwarded reports are not treated as independent corroboration and penalize confidence."""
    rep_fwd_1 = ReportInput(
        id="rpt_fwd_1",
        text="FWD: Water rising rapidly on Lake Road",
        source_type="social_media",
        source_name="User 1",
        location_label="Lake Road",
        reported_at="2026-11-12T14:00:00Z",
    )
    rep_fwd_2 = ReportInput(
        id="rpt_fwd_2",
        text="FWD: Water rising rapidly on Lake Road",
        source_type="social_media",
        source_name="User 2",
        location_label="Lake Road",
        reported_at="2026-11-12T14:05:00Z",
        forwarded_from="rpt_fwd_1",
    )

    incident_fwd = IncidentInput(
        id="inc_fwd",
        title="Forwarded rumor thread",
        type="flood",
        severity="medium",
        status="active",
        location_label="Lake Road",
        reports=[rep_fwd_1, rep_fwd_2],
    )

    _, confidence, _, _, _ = IncidentPriorityRanker.compute_incident_scores(incident_fwd)
    assert any("forwarded" in r.lower() for r in confidence.reasons)
    assert confidence.score < 50


def test_unknown_provenance_not_treated_as_verified():
    """Verify that reports with unknown provenance do not receive official verification boost."""
    rep_unknown = ReportInput(
        id="rpt_001",
        text="Heard there is water rising near lake road.",
        source_type="citizen",
        source_name="Unknown citizen",
        location_label="Lake Road",
        reported_at="2026-11-12T14:00:00Z",
        provenance="unknown",
    )
    incident = IncidentInput(
        id="inc_unk",
        title="Unconfirmed citizen claim",
        type="flood",
        severity="medium",
        status="active",
        location_label="Lake Road",
        reports=[rep_unknown],
    )

    _, confidence, _, _, _ = IncidentPriorityRanker.compute_incident_scores(incident)
    assert confidence.score <= 45
    assert not any("verified emergency responder" in r.lower() for r in confidence.reasons)


def test_missing_optional_report_data_fallback():
    """Verify that incidents without attached reports compute valid deterministic scores from metadata."""
    incident = IncidentInput(
        id="inc_meta_only",
        title="Incident with metadata only",
        type="landslide",
        severity="high",
        status="active",
        location_label="Western Ghats Road",
        independent_source_count=2,
        reports=None,
        report_analyses=None,
        conflicts=None,
    )

    urgency, confidence, verification, explanation, next_steps = IncidentPriorityRanker.compute_incident_scores(incident)

    assert 0 <= urgency.score <= 100
    assert 0 <= confidence.score <= 100
    assert 0 <= verification.score <= 100
    assert len(explanation) >= 2
    assert len(next_steps) >= 1


def test_resolved_incident_handling():
    """Verify that an incident with status='resolved' drops urgency and verification priority."""
    inc_resolved = IncidentInput(
        id="inc_res",
        title="Resolved flooding",
        type="flood",
        severity="critical",
        status="resolved",
        location_label="Lake Road",
        independent_source_count=3,
    )

    urgency, _, verification, _, next_steps = IncidentPriorityRanker.compute_incident_scores(inc_resolved)

    assert urgency.score <= 20
    assert verification.score <= 30
    assert any("resolved" in r.lower() for r in urgency.reasons)
    assert any("Archive" in s or "debrief" in s for s in next_steps)


def test_active_incident_with_old_report_does_not_assume_resolved():
    """Verify that an active incident is not assumed resolved merely because its report is old."""
    rep_old = ReportInput(
        id="rpt_old",
        text="Severe fire in chemical warehouse with toxic fumes.",
        source_type="responder",
        source_name="Station Chief",
        location_label="Industrial Area",
        reported_at="2026-11-10T10:00:00Z",  # 2 days old
    )
    incident_active = IncidentInput(
        id="inc_active_old",
        title="Toxic warehouse fire",
        type="fire",
        severity="critical",
        status="active",  # Explicitly active
        location_label="Industrial Area",
        reports=[rep_old],
        independent_source_count=1,
    )

    urgency, _, _, _, _ = IncidentPriorityRanker.compute_incident_scores(incident_active)
    # Must maintain critical/high urgency because hazard is critical and status is active
    assert urgency.score >= 85


def test_threat_preservation_not_diluted_by_averaging():
    """Verify that severe threat in one report is not diluted when other reports are mild."""
    rep_mild = ReportInput(
        id="rpt_1",
        text="Light rain puddles forming on street.",
        source_type="citizen",
        source_name="User 1",
        location_label="Lake Road",
        reported_at="2026-11-12T13:00:00Z",
    )
    rep_severe = ReportInput(
        id="rpt_2",
        text="URGENT: Flood waters trapped 6 elderly residents inside ground floor! Water rising!",
        source_type="citizen",
        source_name="User 2",
        location_label="Lake Road",
        reported_at="2026-11-12T13:10:00Z",
    )

    incident = IncidentInput(
        id="inc_mixed",
        title="Mixed reports on Lake Road",
        type="flood",
        severity="medium",
        status="active",
        location_label="Lake Road",
        reports=[rep_mild, rep_severe],
    )

    urgency, _, _, _, _ = IncidentPriorityRanker.compute_incident_scores(incident)
    # Must preserve the severe threat level (>= 85 critical)
    assert urgency.score >= 85
    assert urgency.level == ScoreLevelUrgency.CRITICAL


def test_scores_separate_no_blended_score():
    """Verify that urgency, confidence, and verification priority remain strictly distinct."""
    inc = IncidentInput(
        id="inc_001",
        title="Test incident",
        type="flood",
        severity="critical",
        status="active",
        location_label="Test City",
        independent_source_count=1,
    )
    urgency, confidence, verification, _, _ = IncidentPriorityRanker.compute_incident_scores(inc)

    # Different values reflecting different dimensions
    assert urgency.score != confidence.score or urgency.score != verification.score
    assert isinstance(urgency.level, ScoreLevelUrgency)
    assert isinstance(confidence.level, ScoreLevelThree)
    assert isinstance(verification.level, ScoreLevelThree)


def test_backend_schema_compatibility():
    """Verify AI Engine PriorityResponse can be parsed directly by Member 2's backend PriorityResponse."""
    incidents = [
        IncidentInput(
            id="inc_001",
            title="Flooding near Lake Road",
            type="flood",
            severity="critical",
            status="active",
            location_label="Lake Road, Bellandur",
            lat=12.9304,
            lng=77.6784,
            independent_source_count=2,
        ),
        IncidentInput(
            id="inc_002",
            title="Fire on Main Road",
            type="fire",
            severity="medium",
            status="active",
            location_label="Main Road",
            lat=12.9400,
            lng=77.6800,
            independent_source_count=1,
        ),
    ]

    ai_response = IncidentPriorityRanker.rank_incidents(
        incidents=incidents,
        sort=PrioritySort.URGENCY,
    )

    payload = ai_response.model_dump(mode="json")
    backend_response = BackendPriorityResponse.model_validate(payload)

    assert backend_response.sort == "urgency"
    assert len(backend_response.items) == 2
    assert backend_response.items[0].rank == 1
    assert backend_response.items[0].incident_id == "inc_001"
    assert backend_response.items[0].requires_human_decision is True
    assert backend_response.items[0].human_decision.status == "not_decided"


def test_fastapi_priority_endpoints():
    """Verify POST /incidents/priority and POST /priority/rank via FastAPI."""
    payload = {
        "sort": "urgency",
        "incidents": [
            {
                "id": "inc_001",
                "title": "Flooding near Lake Road",
                "type": "flood",
                "severity": "critical",
                "status": "active",
                "location": {
                    "lat": 12.9304,
                    "lng": 77.6784,
                    "label": "Lake Road, Bellandur",
                },
                "independent_source_count": 2,
            }
        ],
    }

    # Test main endpoint
    resp1 = client.post("/incidents/priority", json=payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["sort"] == "urgency"
    assert len(data1["items"]) == 1
    assert data1["items"][0]["rank"] == 1

    # Test RPC alias endpoint
    resp2 = client.post("/priority/rank", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["sort"] == "urgency"
    assert len(data2["items"]) == 1


def test_fastapi_query_parameter_precedence():
    """Verify that query parameter ?sort=... overrides body sort."""
    payload = {
        "sort": "urgency",
        "incidents": [
            {
                "id": "inc_001",
                "title": "Incident 1",
                "type": "flood",
                "severity": "critical",
                "status": "active",
                "location_label": "Loc 1",
            }
        ],
    }

    # Query param sort=verification should override body sort=urgency
    resp = client.post("/incidents/priority?sort=verification", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["sort"] == "verification"


def test_fastapi_invalid_sort_query_parameter():
    """Verify that invalid query parameter sort returns 422 validation_error."""
    payload = {
        "sort": "urgency",
        "incidents": [],
    }
    resp = client.post("/incidents/priority?sort=invalid_mode", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    assert "error" in data["detail"] or "error" in data
    err_obj = data.get("detail", {}).get("error", data.get("error", {}))
    assert err_obj.get("code") == "validation_error"


def test_reconcile_metadata_conflict_forwarded_reports():
    """Verify metadata claiming 3 independent sources reconciles to 0 when all reports are forwarded copies."""
    reports = [
        ReportInput(
            id="rpt_001",
            text="FWD: Urgent water rising rapidly on Lake Road near the junction",
            source_type="social_media",
            source_name="ForwardBot1",
            location_label="Lake Road",
            reported_at="2026-11-12T14:00:00Z",
            forwarded_from="rpt_orig",
        ),
        ReportInput(
            id="rpt_002",
            text="FWD: Urgent water rising rapidly on Lake Road near the junction",
            source_type="social_media",
            source_name="ForwardBot2",
            location_label="Lake Road",
            reported_at="2026-11-12T14:02:00Z",
            forwarded_from="rpt_orig",
        ),
        ReportInput(
            id="rpt_003",
            text="FWD: Urgent water rising rapidly on Lake Road near the junction",
            source_type="social_media",
            source_name="ForwardBot3",
            location_label="Lake Road",
            reported_at="2026-11-12T14:05:00Z",
            forwarded_from="rpt_orig",
        ),
    ]

    incident = IncidentInput(
        id="inc_fwd_conflict",
        title="Forwarded rumor storm",
        type="flood",
        severity="medium",
        status="active",
        location_label="Lake Road",
        independent_source_count=3,  # Metadata claims 3
        reports=reports,
    )

    _, confidence, _, _, _ = IncidentPriorityRanker.compute_incident_scores(incident)

    # Effective independent count must drop to 0
    assert confidence.score <= 35
    assert any("Metadata claimed 3 independent sources" in r for r in confidence.reasons)
    assert any("unconfirmed, forwarded, or duplicates" in r for r in confidence.reasons)
    assert any("High proportion of forwarded copies" in r for r in confidence.reasons)


def test_duplicate_reports_do_not_inflate_independent_evidence():
    """Verify duplicate reports from different handles do not count as multiple independent sources."""
    reports = [
        ReportInput(
            id="rpt_dup_1",
            text="Severe flooding at Bellandur Lake Road basement apartments with ground floor water intrusion.",
            source_type="citizen",
            source_name="Citizen A",
            location_label="Lake Road, Bellandur",
            lat=12.9304,
            lng=77.6784,
            reported_at="2026-11-12T14:00:00Z",
        ),
        ReportInput(
            id="rpt_dup_2",
            text="Severe flooding at Bellandur Lake Road basement apartments with ground floor water intrusion.",
            source_type="citizen",
            source_name="Citizen B",
            location_label="Lake Road, Bellandur",
            lat=12.9304,
            lng=77.6784,
            reported_at="2026-11-12T14:03:00Z",
        ),
    ]

    incident = IncidentInput(
        id="inc_dup_test",
        title="Duplicated flood warning",
        type="flood",
        severity="high",
        status="active",
        location_label="Lake Road, Bellandur",
        independent_source_count=2,  # Metadata claims 2
        reports=reports,
    )

    _, confidence, _, _, _ = IncidentPriorityRanker.compute_incident_scores(incident)

    # Reconciles to 1 defensible source because rpt_dup_2 is a duplicate of rpt_dup_1
    assert any("Metadata claimed 2 independent sources, but report evidence confirms only 1" in r for r in confidence.reasons)
    assert any("Single-source report; awaiting independent field corroboration" in r for r in confidence.reasons)


def test_multiple_reports_same_source_not_independent():
    """Verify multiple reports from the same source name are not counted as multiple independent sources."""
    reports = [
        ReportInput(
            id="rpt_s1",
            text="Water starting to overflow from the main storm drain.",
            source_type="citizen",
            source_name="Resident Sharma",
            location_label="Lake Road",
            reported_at="2026-11-12T13:30:00Z",
        ),
        ReportInput(
            id="rpt_s2",
            text="The water has reached my front gate now.",
            source_type="citizen",
            source_name="Resident Sharma",
            location_label="Lake Road",
            reported_at="2026-11-12T13:50:00Z",
        ),
        ReportInput(
            id="rpt_s3",
            text="Power just went out across the lane.",
            source_type="citizen",
            source_name="Resident Sharma",
            location_label="Lake Road",
            reported_at="2026-11-12T14:10:00Z",
        ),
    ]

    incident = IncidentInput(
        id="inc_same_source",
        title="Single resident update sequence",
        type="flood",
        severity="medium",
        status="active",
        location_label="Lake Road",
        independent_source_count=3,  # Metadata erroneously counts 3
        reports=reports,
    )

    _, confidence, _, _, _ = IncidentPriorityRanker.compute_incident_scores(incident)

    # Only 1 unique known source
    assert any("Metadata claimed 3 independent sources, but report evidence confirms only 1" in r for r in confidence.reasons)
    assert any("Single-source report; awaiting independent field corroboration" in r for r in confidence.reasons)


def test_resolved_incident_preserves_historical_reasons():
    """Verify resolved incidents lower urgency but preserve historical threat reasons and append resolution."""
    report = ReportInput(
        id="rpt_life_threat",
        text="Elderly resident trapped on ground floor as water level is rising rapidly.",
        source_type="citizen",
        source_name="Resident A",
        location_label="Lake Road",
        reported_at="2026-11-12T13:50:00Z",
    )

    incident = IncidentInput(
        id="inc_resolved_severe",
        title="Rescued basement flooding",
        type="flood",
        severity="critical",
        status="resolved",
        location_label="Lake Road",
        reports=[report],
    )

    urgency, _, verification, _, next_steps = IncidentPriorityRanker.compute_incident_scores(incident)

    # Score lowered
    assert urgency.score <= 20
    assert urgency.level == ScoreLevelUrgency.LOW
    assert verification.score <= 30

    # Historical reasons preserved
    assert any("Incident severity evaluated as Critical" in r for r in urgency.reasons)
    assert any("Potential threat to human life or reported trapped individuals" in r for r in urgency.reasons)
    assert any("Vulnerable population mentioned in field reports" in r for r in urgency.reasons)

    # Resolution status appended
    assert urgency.reasons[-1] == "Incident has been officially marked as resolved; priority lowered accordingly"

    # Next steps reflect resolution
    assert any("Recommend logging final responder debrief" in s for s in next_steps)
    assert any("Suggest archiving incident documentation" in s for s in next_steps)


def test_advisory_next_steps_phrasing():
    """Verify that all recommended next steps are explicitly phrased as advisory recommendations."""
    incidents = [
        # Critical active
        IncidentInput(
            id="inc_crit_act",
            title="Critical flood",
            type="flood",
            severity="critical",
            status="active",
            location_label="Loc 1",
            reports=[
                ReportInput(
                    id="r1",
                    text="Emergency responder confirms water level rising.",
                    source_type="responder",
                    provenance="verified",
                    reported_at="2026-11-12T14:00:00Z",
                )
            ],
            independent_source_count=2,
        ),
        # Conflicted
        IncidentInput(
            id="inc_conf",
            title="Conflicted fire",
            type="fire",
            severity="high",
            status="active",
            location_label="Loc 2",
            conflicts=[
                ConflictItem(
                    id="c1",
                    topic="Casualties",
                    report_ids=["r2", "r3"],
                    statements=[
                        ConflictStatement(report_id="r2", text="2 injured"),
                        ConflictStatement(report_id="r3", text="No injuries"),
                    ],
                    detected_at="2026-11-12T14:00:00Z",
                )
            ],
        ),
        # Resolved
        IncidentInput(
            id="inc_res",
            title="Resolved event",
            type="flood",
            severity="low",
            status="resolved",
            location_label="Loc 3",
        ),
        # Normal monitoring
        IncidentInput(
            id="inc_mon",
            title="Routine event",
            type="other",
            severity="low",
            status="monitoring",
            location_label="Loc 4",
            independent_source_count=1,
        ),
    ]

    response = IncidentPriorityRanker.rank_incidents(incidents)
    for item in response.items:
        assert len(item.recommended_next_steps) >= 1
        for step in item.recommended_next_steps:
            # Must start with advisory verbs
            assert step.startswith(("Recommend ", "Advise ", "Suggest ")), f"Step not advisory: {step}"


def test_report_analyses_input_path():
    """Verify that report_analyses inputs preserve maximum report urgency without dilution."""
    # Pre-computed mild analysis
    mild_analysis = Analysis(
        analyzed_at="2026-11-12T13:00:00Z",
        engine_version="0.1.0",
        duplicate=DuplicateInfo(is_duplicate=False),
        source_verification=SourceVerification(
            independence=Independence.INDEPENDENT,
            corroboration_status=CorroborationStatus.SINGLE_SOURCE,
        ),
        freshness=FreshnessInfo(
            status=FreshnessStatus.RECENT,
            age_minutes=15,
            last_updated="2026-11-12T13:00:00Z",
        ),
        scores=Scores(
            urgency=UrgencyScore(
                score=35,
                level=ScoreLevelUrgency.LOW,
                reasons=["Puddles on pedestrian walkway"],
            ),
            evidence_confidence=EvidenceConfidenceScore(
                score=50,
                level=ScoreLevelThree.MEDIUM,
                reasons=["Single citizen observation"],
            ),
            verification_priority=VerificationPriorityScore(
                score=30,
                level=ScoreLevelThree.LOW,
                reasons=["Low urgency"],
            ),
        ),
        recommendation=Recommendation(
            type=RecommendationType.MONITOR,
            summary="Routine street monitoring",
            next_steps=["Monitor periodically"],
            requires_human_decision=True,
        ),
    )

    # Pre-computed critical analysis
    critical_analysis = Analysis(
        analyzed_at="2026-11-12T13:10:00Z",
        engine_version="0.1.0",
        duplicate=DuplicateInfo(is_duplicate=False),
        source_verification=SourceVerification(
            independence=Independence.INDEPENDENT,
            corroboration_status=CorroborationStatus.CORROBORATED,
        ),
        freshness=FreshnessInfo(
            status=FreshnessStatus.RECENT,
            age_minutes=5,
            last_updated="2026-11-12T13:10:00Z",
        ),
        scores=Scores(
            urgency=UrgencyScore(
                score=95,
                level=ScoreLevelUrgency.CRITICAL,
                reasons=["Rapid water inundation trapping residents in basement"],
            ),
            evidence_confidence=EvidenceConfidenceScore(
                score=80,
                level=ScoreLevelThree.HIGH,
                reasons=["Multiple corroborated reports"],
            ),
            verification_priority=VerificationPriorityScore(
                score=25,
                level=ScoreLevelThree.LOW,
                reasons=["Corroborated"],
            ),
        ),
        recommendation=Recommendation(
            type=RecommendationType.ESCALATE_FOR_HUMAN_REVIEW,
            summary="Immediate life safety hazard",
            next_steps=["Alert rescue operations"],
            requires_human_decision=True,
        ),
    )

    incident = IncidentInput(
        id="inc_with_analyses",
        title="Incident with pre-analyzed reports",
        type="flood",
        severity="medium",  # Base urgency would be 50
        status="active",
        location_label="Lake Road",
        report_analyses=[mild_analysis, critical_analysis],
    )

    urgency, _, _, _, _ = IncidentPriorityRanker.compute_incident_scores(incident)

    # Must preserve the maximum report urgency (95) rather than averaging (which would be ~65)
    assert urgency.score == 95
    assert urgency.level == ScoreLevelUrgency.CRITICAL
    assert any("Rapid water inundation trapping residents in basement" in r for r in urgency.reasons)


def test_timeline_escalation_and_radius_scoring():
    """Verify that escalating timeline trends and large affected radius increase urgency score."""
    entry_1 = TimelineEntry(
        timestamp="2026-11-12T12:00:00Z",
        severity=IncidentSeverity.LOW,
        status=IncidentStatus.ACTIVE,
        report_count=1,
        affected_radius_m=100,
        summary="Initial small leak observed",
    )
    entry_2 = TimelineEntry(
        timestamp="2026-11-12T13:00:00Z",
        severity=IncidentSeverity.CRITICAL,
        status=IncidentStatus.ACTIVE,
        report_count=6,
        affected_radius_m=750,  # >= 500m threshold
        summary="Water main ruptured, widespread inundation across neighbourhood",
    )

    incident = IncidentInput(
        id="inc_escalating",
        title="Escalating pipeline rupture",
        type="flood",
        severity="medium",  # Base 50
        status="active",
        location_label="Central Boulevard",
        timeline=[entry_1, entry_2],
    )

    urgency, _, _, _, _ = IncidentPriorityRanker.compute_incident_scores(incident)

    # Base (50) + Escalation (+5) + Radius >= 500m (+5) = 60
    assert urgency.score == 60
    assert any("Escalating severity trend observed in incident timeline" in r for r in urgency.reasons)
    assert any("Significant geographical hazard radius reported (>= 500m)" in r for r in urgency.reasons)


def test_readme_example_consistency():
    """Verify that the exact example documented in README.md produces the documented output scores."""
    req = PriorityRankRequest(
        sort=PrioritySort.URGENCY,
        incidents=[
            IncidentInput(
                id="inc_001",
                title="Flooding near Bellandur lake road",
                type="flood",
                severity="critical",
                status="active",
                location={"lat": 12.9304, "lng": 77.6784, "label": "Lake Road, Bellandur"},
                report_count=2,
                independent_source_count=2,
                first_reported_at="2026-11-12T13:50:00Z",
                last_updated_at="2026-11-12T14:25:00Z",
                timeline=[],
                reports=[
                    ReportInput(
                        id="rpt_001",
                        text="Elderly resident trapped on ground floor as water level is rising rapidly.",
                        source_type="citizen",
                        source_name="Resident A",
                        location_label="Lake Road, Bellandur",
                        lat=12.9304,
                        lng=77.6784,
                        reported_at="2026-11-12T13:50:00Z",
                        provenance="firsthand",
                    ),
                    ReportInput(
                        id="rpt_002",
                        text="Emergency responder on scene confirms 1.2m water level on main road.",
                        source_type="responder",
                        source_name="Officer Patil",
                        location_label="Lake Road, Bellandur",
                        lat=12.9304,
                        lng=77.6784,
                        reported_at="2026-11-12T14:10:00Z",
                        provenance="verified",
                    ),
                ],
                conflicts=[],
            )
        ],
    )

    response = IncidentPriorityRanker.rank_incidents(req.incidents, sort=req.sort)
    assert response.sort == PrioritySort.URGENCY
    assert len(response.items) == 1

    item = response.items[0]
    assert item.rank == 1
    assert item.incident_id == "inc_001"
    assert item.urgency.score == 100
    assert item.urgency.level == ScoreLevelUrgency.CRITICAL
    assert item.evidence_confidence.score == 85
    assert item.evidence_confidence.level == ScoreLevelThree.HIGH
    assert item.verification_priority.score == 5
    assert item.verification_priority.level == ScoreLevelThree.LOW

    # Verify advisory next steps
    assert item.recommended_next_steps == [
        "Recommend alerting duty officer for immediate tactical dispatch review",
        "Advise staging emergency rescue and medical standby units for responder review",
    ]

    # Verify human supervision invariant
    assert item.requires_human_decision is True
    assert item.human_decision.status == "not_decided"
