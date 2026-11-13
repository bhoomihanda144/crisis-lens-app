"""Tests for CrisisLens Evidence Relationship Graph Generation (Stage 4).

Validates:
- API Contract v1.0 Section 4.8 compliance
- Provenance integrity: unverified reports retain uncertainty
- Relationship generation: forwarding, duplicates, corroboration, conflicts
- Zero invented edges for unrelated reports
- NetworkX topology validation: strictly DAG, edge directions (later -> earlier), no self-loops
- Schema compatibility with backend.app.schemas.evidence.EvidenceGraphResponse
- FastAPI endpoints: POST /incidents/{id}/evidence-graph and POST /graph/generate
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

# Ensure backend can be imported for schema compatibility checks
backend_path = Path.cwd() / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from ai_engine.main import app
from ai_engine.schemas.enums import RelationshipType, SourceType, FreshnessStatus
from ai_engine.schemas.internal import ReportInput, GenerateGraphRequest
from ai_engine.schemas.analysis import ConflictItem, ConflictStatement
from ai_engine.schemas.graph import EvidenceNode, EvidenceEdge, EvidenceGraphResponse
from ai_engine.modules.graph import EvidenceGraphBuilder, GraphValidationError

from app.schemas.evidence import EvidenceGraphResponse as BackendEvidenceGraphResponse

client = TestClient(app)


def test_single_report_no_relationships():
    """Verify single isolated report yields 1 node and 0 edges without invented relationships."""
    report = ReportInput(
        id="rpt_001",
        text="Water entering houses near Bellandur lake road.",
        source_type="citizen",
        source_name="Local resident",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-12T14:00:00Z",
    )

    graph = EvidenceGraphBuilder.build_graph(
        incident_id="inc_001",
        reports=[report],
        conflicts=[],
    )

    assert graph.incident_id == "inc_001"
    assert len(graph.nodes) == 1
    assert len(graph.edges) == 0

    node = graph.nodes[0]
    assert node.id == "rpt_001"
    assert node.report_id == "rpt_001"
    assert node.role == RelationshipType.ORIGINAL
    assert node.source_type == SourceType.CITIZEN
    assert node.freshness_status in [FreshnessStatus.RECENT, FreshnessStatus.AGING, FreshnessStatus.STALE]
    assert "Water entering houses" in node.excerpt


def test_explicit_original_provenance():
    """Verify that explicit original provenance is honored without unverified marker."""
    report = ReportInput(
        id="rpt_001",
        text="Official flood warning issued for Bellandur area.",
        source_type="official",
        source_name="Disaster Management Cell",
        location_label="Bellandur",
        reported_at="2026-11-12T13:00:00Z",
        provenance="verified_original",
    )

    graph = EvidenceGraphBuilder.build_graph(
        incident_id="inc_001",
        reports=[report],
    )

    node = graph.nodes[0]
    assert node.role == RelationshipType.ORIGINAL
    assert "(Unverified)" not in node.label
    assert node.label == "Official: Bellandur"


def test_unknown_provenance_preserves_uncertainty():
    """Verify that unknown provenance preserves uncertainty in the node label."""
    report = ReportInput(
        id="rpt_002",
        text="Heard water is rising somewhere near the lake.",
        source_type="citizen",
        source_name="Anonymous citizen",
        location_label="Bellandur Lake",
        reported_at="2026-11-12T13:30:00Z",
        provenance="unknown",
    )

    graph = EvidenceGraphBuilder.build_graph(
        incident_id="inc_001",
        reports=[report],
    )

    node = graph.nodes[0]
    assert node.role == RelationshipType.ORIGINAL
    assert "(Unverified)" in node.label
    assert node.label == "Citizen (Unverified): Bellandur Lake"
    assert len(graph.edges) == 0


def test_duplicate_relationship():
    """Verify duplicate report produces directed edge (later -> earlier) with duplicate type."""
    rpt_earlier = ReportInput(
        id="rpt_001",
        text="Severe waterlogging on Lake Road near Bellandur lake with water level at 1 meter.",
        source_type="citizen",
        source_name="Resident A",
        location_label="Lake Road, Bellandur",
        lat=12.9304,
        lng=77.6784,
        reported_at="2026-11-12T13:00:00Z",
        provenance="verified_original",
    )
    rpt_later = ReportInput(
        id="rpt_002",
        text="Severe waterlogging on Lake Road near Bellandur lake, water level reaching 1 meter high.",
        source_type="citizen",
        source_name="Resident B",
        location_label="Lake Road, Bellandur",
        lat=12.9305,
        lng=77.6785,
        reported_at="2026-11-12T13:15:00Z",
    )

    graph = EvidenceGraphBuilder.build_graph(
        incident_id="inc_001",
        reports=[rpt_earlier, rpt_later],
    )

    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1

    edge = graph.edges[0]
    assert edge.source == "rpt_002"  # Later report
    assert edge.target == "rpt_001"  # Earlier report
    assert edge.type == RelationshipType.DUPLICATE
    assert edge.confidence >= 0.55
    assert "Duplicate" in edge.label

    # Node roles
    nodes_by_id = {n.id: n for n in graph.nodes}
    assert nodes_by_id["rpt_001"].role == RelationshipType.ORIGINAL
    assert nodes_by_id["rpt_002"].role == RelationshipType.DUPLICATE


def test_forwarded_relationship_explicit_and_marker():
    """Verify forwarded reports produce directed edges with forwarded type."""
    rpt_parent = ReportInput(
        id="rpt_001",
        text="Emergency rescue needed on 4th cross Lake Road. Two families trapped by flood waters.",
        source_type="citizen",
        source_name="Resident A",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-12T12:00:00Z",
    )
    rpt_fwd = ReportInput(
        id="rpt_002",
        text="Emergency rescue needed on 4th cross Lake Road. Two families trapped by flood waters.",
        source_type="social_media",
        source_name="Twitter User",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-12T12:20:00Z",
        forwarded_from="rpt_001",
    )

    graph = EvidenceGraphBuilder.build_graph(
        incident_id="inc_001",
        reports=[rpt_parent, rpt_fwd],
    )

    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.source == "rpt_002"
    assert edge.target == "rpt_001"
    assert edge.type == RelationshipType.FORWARDED
    assert edge.confidence == 1.0

    nodes_by_id = {n.id: n for n in graph.nodes}
    assert nodes_by_id["rpt_001"].role == RelationshipType.ORIGINAL
    assert nodes_by_id["rpt_002"].role == RelationshipType.FORWARDED


def test_forwarded_text_pattern():
    """Verify text starting with FWD: matches parent text and creates forwarded edge."""
    rpt_parent = ReportInput(
        id="rpt_001",
        text="Water entering ground floor apartments on Lake Road.",
        source_type="citizen",
        source_name="Resident A",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-12T12:00:00Z",
    )
    rpt_fwd_text = ReportInput(
        id="rpt_002",
        text="FWD: Water entering ground floor apartments on Lake Road.",
        source_type="social_media",
        source_name="User B",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-12T12:15:00Z",
    )

    graph = EvidenceGraphBuilder.build_graph(
        incident_id="inc_001",
        reports=[rpt_parent, rpt_fwd_text],
    )

    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.source == "rpt_002"
    assert edge.target == "rpt_001"
    assert edge.type == RelationshipType.FORWARDED


def test_defensible_corroboration():
    """Verify independent reports corroborating the same event produce corroborating edge."""
    rpt_citizen = ReportInput(
        id="rpt_001",
        text="Water level rising rapidly on Lake Road, electricity transformer submerged.",
        source_type="citizen",
        source_name="Resident A",
        location_label="Lake Road, Bellandur",
        lat=12.9304,
        lng=77.6784,
        reported_at="2026-11-12T13:00:00Z",
        provenance="firsthand",
    )
    rpt_official = ReportInput(
        id="rpt_002",
        text="Official inspection confirms transformer submerged and high water on Lake Road. Power cut initiated.",
        source_type="official",
        source_name="BESCOM Duty Officer",
        location_label="Lake Road, Bellandur",
        lat=12.9304,
        lng=77.6784,
        reported_at="2026-11-12T13:40:00Z",
        provenance="verified",
    )

    graph = EvidenceGraphBuilder.build_graph(
        incident_id="inc_001",
        reports=[rpt_citizen, rpt_official],
    )

    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.source == "rpt_002"  # Official report later
    assert edge.target == "rpt_001"  # Citizen report earlier
    assert edge.type == RelationshipType.CORROBORATING
    assert edge.confidence >= 0.70

    nodes_by_id = {n.id: n for n in graph.nodes}
    assert nodes_by_id["rpt_001"].role == RelationshipType.ORIGINAL
    assert nodes_by_id["rpt_002"].role == RelationshipType.CORROBORATING


def test_conflicting_evidence():
    """Verify explicitly supplied conflict items generate conflicting edges between reports."""
    rpt_1 = ReportInput(
        id="rpt_001",
        text="Only the outer compound wall collapsed due to rain. Main house is safe.",
        source_type="citizen",
        source_name="Owner",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-12T13:00:00Z",
    )
    rpt_2 = ReportInput(
        id="rpt_002",
        text="Entire 2-story building collapsed on Lake Road. Multiple people feared trapped.",
        source_type="citizen",
        source_name="Passerby",
        location_label="Lake Road, Bellandur",
        reported_at="2026-11-12T13:20:00Z",
    )

    conflict = ConflictItem(
        id="cfl_001",
        topic="Extent of structural damage",
        report_ids=["rpt_001", "rpt_002"],
        statements=[
            ConflictStatement(report_id="rpt_001", text=rpt_1.text),
            ConflictStatement(report_id="rpt_002", text=rpt_2.text),
        ],
        detected_at="2026-11-12T13:25:00Z",
    )

    graph = EvidenceGraphBuilder.build_graph(
        incident_id="inc_001",
        reports=[rpt_1, rpt_2],
        conflicts=[conflict],
    )

    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.source == "rpt_002"  # Later report
    assert edge.target == "rpt_001"  # Earlier report
    assert edge.type == RelationshipType.CONFLICTING
    assert "Extent of structural damage" in edge.label

    nodes_by_id = {n.id: n for n in graph.nodes}
    assert nodes_by_id["rpt_002"].role == RelationshipType.CONFLICTING


def test_no_invented_relationships_unrelated_reports():
    """Verify unrelated reports in different locations do not have invented edges."""
    rpt_flood = ReportInput(
        id="rpt_001",
        text="Severe lake flooding submerging vehicles on Bellandur Lake Road.",
        source_type="citizen",
        source_name="Resident A",
        location_label="Lake Road, Bellandur",
        lat=12.9304,
        lng=77.6784,
        reported_at="2026-11-12T12:00:00Z",
    )
    rpt_fire = ReportInput(
        id="rpt_002",
        text="Commercial restaurant kitchen fire reported with heavy black smoke billowing.",
        source_type="citizen",
        source_name="Shopkeeper B",
        location_label="Whitefield Main Road",
        lat=12.9698,
        lng=77.7499,
        reported_at="2026-11-12T12:45:00Z",
    )

    graph = EvidenceGraphBuilder.build_graph(
        incident_id="inc_001",
        reports=[rpt_flood, rpt_fire],
    )

    assert len(graph.nodes) == 2
    # Unrelated reports must NEVER have invented connections
    assert len(graph.edges) == 0


def test_correct_edge_direction_invariant():
    """Verify that every edge points from later or derived report (source) to earlier or reference report (target)."""
    reports = [
        ReportInput(
            id="rpt_001",
            text="Original report of basement flooding on Lake Road.",
            source_type="citizen",
            source_name="Tenant",
            location_label="Lake Road",
            reported_at="2026-11-12T10:00:00Z",
            provenance="verified_original",
        ),
        ReportInput(
            id="rpt_002",
            text="Original report of basement flooding on Lake Road.",
            source_type="citizen",
            source_name="Neighbor",
            location_label="Lake Road",
            reported_at="2026-11-12T10:15:00Z",
            forwarded_from="rpt_001",
        ),
        ReportInput(
            id="rpt_003",
            text="Severe flooding confirmed in basements on Lake Road with water pumping needed.",
            source_type="responder",
            source_name="Fire Chief",
            location_label="Lake Road",
            reported_at="2026-11-12T10:45:00Z",
            provenance="verified",
        ),
    ]

    graph = EvidenceGraphBuilder.build_graph(
        incident_id="inc_001",
        reports=reports,
    )

    reports_map = {r.id: datetime.fromisoformat(r.reported_at.replace("Z", "+00:00")) for r in reports}

    assert len(graph.edges) >= 2
    for edge in graph.edges:
        source_dt = reports_map[edge.source]
        target_dt = reports_map[edge.target]
        assert source_dt >= target_dt, f"Edge {edge.id} has source ({source_dt}) earlier than target ({target_dt})"


def test_no_self_loops_validation():
    """Verify that any self-loop raises GraphValidationError."""
    report = ReportInput(
        id="rpt_001",
        text="Test report text",
        source_type="citizen",
        source_name="Tester",
        location_label="Test City",
        reported_at="2026-11-12T12:00:00Z",
    )

    node = EvidenceNode(
        id="rpt_001",
        report_id="rpt_001",
        label="Citizen: Test City",
        role=RelationshipType.ORIGINAL,
        source_type=SourceType.CITIZEN,
        source_name="Tester",
        timestamp="2026-11-12T12:00:00Z",
        excerpt="Test report text",
        freshness_status=FreshnessStatus.RECENT,
    )
    self_loop_edge = EvidenceEdge(
        id="edge_bad",
        source="rpt_001",
        target="rpt_001",
        type=RelationshipType.DUPLICATE,
        label="Self loop",
        confidence=1.0,
    )

    with pytest.raises(GraphValidationError, match="Self-loop detected"):
        EvidenceGraphBuilder.validate_topology(
            nodes=[node],
            edges=[self_loop_edge],
            reports_by_id={"rpt_001": report},
        )


def test_cycle_validation_with_networkx():
    """Verify that cycle detection using NetworkX raises GraphValidationError."""
    rpt_a = ReportInput(
        id="rpt_a",
        text="Report A",
        source_type="citizen",
        source_name="User A",
        location_label="City",
        reported_at="2026-11-12T12:00:00Z",
    )
    rpt_b = ReportInput(
        id="rpt_b",
        text="Report B",
        source_type="citizen",
        source_name="User B",
        location_label="City",
        reported_at="2026-11-12T12:00:00Z",
    )

    node_a = EvidenceNode(
        id="rpt_a",
        report_id="rpt_a",
        label="User A",
        role=RelationshipType.ORIGINAL,
        source_type=SourceType.CITIZEN,
        source_name="User A",
        timestamp="2026-11-12T12:00:00Z",
        excerpt="Report A",
        freshness_status=FreshnessStatus.RECENT,
    )
    node_b = EvidenceNode(
        id="rpt_b",
        report_id="rpt_b",
        label="User B",
        role=RelationshipType.CORROBORATING,
        source_type=SourceType.CITIZEN,
        source_name="User B",
        timestamp="2026-11-12T12:00:00Z",
        excerpt="Report B",
        freshness_status=FreshnessStatus.RECENT,
    )

    edge_1 = EvidenceEdge(
        id="edge_1",
        source="rpt_b",
        target="rpt_a",
        type=RelationshipType.CORROBORATING,
        label="Corrob",
        confidence=0.8,
    )
    edge_2 = EvidenceEdge(
        id="edge_2",
        source="rpt_a",
        target="rpt_b",
        type=RelationshipType.CORROBORATING,
        label="Corrob reverse",
        confidence=0.8,
    )

    with pytest.raises(GraphValidationError, match="Cycle detected"):
        EvidenceGraphBuilder.validate_topology(
            nodes=[node_a, node_b],
            edges=[edge_1, edge_2],
            reports_by_id={"rpt_a": rpt_a, "rpt_b": rpt_b},
        )


def test_backend_schema_compatibility():
    """Verify AI Engine response can be validated against Member 2's backend schema without error."""
    rpt_1 = ReportInput(
        id="rpt_001",
        text="Flooding reported on Lake Road.",
        source_type="citizen",
        source_name="Citizen 1",
        location_label="Lake Road",
        reported_at="2026-11-12T12:00:00Z",
        provenance="verified_original",
    )
    rpt_2 = ReportInput(
        id="rpt_002",
        text="Flooding confirmed on Lake Road with water entering basements.",
        source_type="official",
        source_name="Officer 2",
        location_label="Lake Road",
        reported_at="2026-11-12T12:30:00Z",
        provenance="verified",
    )

    ai_graph = EvidenceGraphBuilder.build_graph(
        incident_id="inc_001",
        reports=[rpt_1, rpt_2],
    )

    # Dump to dict and validate with backend Pydantic model
    payload = ai_graph.model_dump(mode="json")
    backend_graph = BackendEvidenceGraphResponse.model_validate(payload)

    assert backend_graph.incident_id == "inc_001"
    assert len(backend_graph.nodes) == 2
    assert len(backend_graph.edges) == 1
    assert backend_graph.nodes[0].id == "rpt_001"
    assert backend_graph.edges[0].source == "rpt_002"
    assert backend_graph.edges[0].target == "rpt_001"


def test_fastapi_incident_evidence_graph_endpoint():
    """Verify POST /incidents/{incident_id}/evidence-graph endpoint via FastAPI."""
    payload = {
        "incident_id": "inc_001",
        "reports": [
            {
                "id": "rpt_001",
                "text": "Water rising fast on Lake Road.",
                "source_type": "citizen",
                "source_name": "Citizen A",
                "location_label": "Lake Road, Bellandur",
                "reported_at": "2026-11-12T14:00:00Z",
                "provenance": "verified_original",
            },
            {
                "id": "rpt_002",
                "text": "Water rising fast on Lake Road.",
                "source_type": "citizen",
                "source_name": "Citizen B",
                "location_label": "Lake Road, Bellandur",
                "reported_at": "2026-11-12T14:10:00Z",
                "forwarded_from": "rpt_001",
            },
        ],
    }

    response = client.post("/incidents/inc_001/evidence-graph", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == "inc_001"
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
    assert data["edges"][0]["source"] == "rpt_002"
    assert data["edges"][0]["target"] == "rpt_001"
    assert data["edges"][0]["type"] == "forwarded"


def test_fastapi_graph_generate_rpc_endpoint():
    """Verify POST /graph/generate endpoint via FastAPI."""
    payload = {
        "incident_id": "inc_002",
        "reports": [
            {
                "id": "rpt_101",
                "text": "Landslide warning issued for highway sector 4.",
                "source_type": "official",
                "source_name": "Highway Authority",
                "location_label": "Sector 4 Highway",
                "reported_at": "2026-11-12T11:00:00Z",
                "provenance": "verified_original",
            }
        ],
    }

    response = client.post("/graph/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == "inc_002"
    assert len(data["nodes"]) == 1
    assert len(data["edges"]) == 0
