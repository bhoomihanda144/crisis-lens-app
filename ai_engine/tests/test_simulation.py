"""Tests for CrisisLens What-If Disaster Simulation Engine (Stage 6).

Validates:
- API Contract v1.0 Section 4.9 compliance
- Minimum severity 1 and maximum severity 5 boundary handling
- Zero affected population and zero available resources
- No resource shortages, single shortages, and multiple simultaneous shortages
- Blocked road delay and compound response delay calculations
- Validation: Negative inputs, severity out of bounds (1-5), and unknown fields rejected
- Incident context handling: empty context produces NO invented changes; supplied context produces deterministic shifts
- Safety invariants: is_simulation=True always, zero mutation of original incident state
- Explicit road-access impact requirement: no guessing which incident's access is blocked
- Schema compatibility with backend/app/schemas/simulation.py
- FastAPI endpoints: POST /simulate and POST /simulation/run
"""

import sys
from pathlib import Path
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

# Ensure backend can be imported for schema compatibility checks
backend_path = Path.cwd() / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from ai_engine.main import app
from ai_engine.schemas.simulation import (
    SimulationRequest,
    SimulationResponse,
    ResourceDemand,
    ResourceShortage,
    PriorityChange,
)
from ai_engine.schemas.internal import IncidentInput, ReportInput, SimulationScenarioRequest
from ai_engine.modules.simulation import DisasterSimulationEngine

from app.schemas.simulation import SimulationResponse as BackendSimulationResponse

client = TestClient(app)


def test_simulation_severity_boundaries():
    """Verify minimum severity (1) and maximum severity (5) produce valid demand calculations."""
    # Min severity 1
    req_min = SimulationRequest(
        scenario_name="Light rainfall",
        affected_population=3000,
        disaster_severity=1,
        rescue_teams=5,
        blocked_roads=0,
        available_ambulances=5,
    )
    res_min = DisasterSimulationEngine.run_simulation(req_min)
    assert res_min.inputs.disaster_severity == 1
    assert res_min.results.resource_demand.rescue_teams == 2  # max(2, int((3000/1500) * (1/2.5))) = max(2, 0) = 2
    assert res_min.results.resource_demand.ambulances == 2    # max(2, int((3000/2000) * (1/2.0))) = max(2, 0) = 2

    # Max severity 5
    req_max = SimulationRequest(
        scenario_name="Catastrophic cyclone",
        affected_population=15000,
        disaster_severity=5,
        rescue_teams=20,
        blocked_roads=4,
        available_ambulances=15,
    )
    res_max = DisasterSimulationEngine.run_simulation(req_max)
    assert res_max.inputs.disaster_severity == 5
    # max(2, int((15000/1500) * (5/2.5))) = max(2, int(10 * 2)) = 20
    assert res_max.results.resource_demand.rescue_teams == 20
    # max(2, int((15000/2000) * (5/2.0))) = max(2, int(7.5 * 2.5)) = 18
    assert res_max.results.resource_demand.ambulances == 18


def test_simulation_zero_affected_population():
    """Verify zero affected population defaults to minimum baseline demand (2 teams, 2 ambulances)."""
    req = SimulationRequest(
        scenario_name="Precautionary flood watch",
        affected_population=0,
        disaster_severity=3,
        rescue_teams=4,
        blocked_roads=0,
        available_ambulances=4,
    )
    res = DisasterSimulationEngine.run_simulation(req)
    assert res.results.resource_demand.rescue_teams == 2
    assert res.results.resource_demand.ambulances == 2
    assert res.results.shortages == []
    assert res.results.estimated_response_delay_minutes == 0


def test_simulation_zero_available_resources():
    """Verify that having 0 available resources yields shortfalls equal to demanded resources."""
    req = SimulationRequest(
        scenario_name="Complete resource depletion scenario",
        affected_population=6000,
        disaster_severity=4,
        rescue_teams=0,
        blocked_roads=1,
        available_ambulances=0,
    )
    res = DisasterSimulationEngine.run_simulation(req)
    demand = res.results.resource_demand

    assert len(res.results.shortages) == 2
    shortages_by_res = {s.resource: s for s in res.results.shortages}

    assert shortages_by_res["rescue_teams"].available == 0
    assert shortages_by_res["rescue_teams"].required == demand.rescue_teams
    assert shortages_by_res["rescue_teams"].shortfall == demand.rescue_teams

    assert shortages_by_res["ambulances"].available == 0
    assert shortages_by_res["ambulances"].required == demand.ambulances
    assert shortages_by_res["ambulances"].shortfall == demand.ambulances


def test_simulation_no_resource_shortage():
    """Verify that when available resources satisfy demand, shortages is empty and summary reflects it."""
    req = SimulationRequest(
        scenario_name="Well resourced zone",
        affected_population=3000,
        disaster_severity=2,
        rescue_teams=10,
        blocked_roads=1,
        available_ambulances=10,
    )
    res = DisasterSimulationEngine.run_simulation(req)

    assert res.results.shortages == []
    assert "All resource demands satisfied" in res.results.summary


def test_simulation_rescue_team_shortage_only():
    """Verify scenario where only rescue teams have a shortfall."""
    req = SimulationRequest(
        scenario_name="Rescue team deficit only",
        affected_population=6000,
        disaster_severity=3,
        rescue_teams=1,            # Demand: int(4 * 1.2) = 4 -> shortfall = 3
        blocked_roads=0,
        available_ambulances=20,   # Ample ambulances
    )
    res = DisasterSimulationEngine.run_simulation(req)

    assert len(res.results.shortages) == 1
    shortage = res.results.shortages[0]
    assert shortage.resource == "rescue_teams"
    assert shortage.shortfall == 3
    assert shortage.available == 1


def test_simulation_ambulance_shortage_only():
    """Verify scenario where only ambulances have a shortfall."""
    req = SimulationRequest(
        scenario_name="Ambulance deficit only",
        affected_population=6000,
        disaster_severity=3,
        rescue_teams=20,           # Ample rescue teams
        blocked_roads=0,
        available_ambulances=1,    # Demand: int(3 * 1.5) = 4 -> shortfall = 3
    )
    res = DisasterSimulationEngine.run_simulation(req)

    assert len(res.results.shortages) == 1
    shortage = res.results.shortages[0]
    assert shortage.resource == "ambulances"
    assert shortage.shortfall == 3
    assert shortage.available == 1


def test_simulation_multiple_simultaneous_shortages():
    """Verify scenario with simultaneous shortfalls across both rescue teams and ambulances."""
    req = SimulationRequest(
        scenario_name="Dual shortage crisis",
        affected_population=12000,
        disaster_severity=4,
        rescue_teams=6,            # Demand: int(8 * 1.6) = 12 -> shortfall = 6
        blocked_roads=3,
        available_ambulances=5,    # Demand: int(6 * 2.0) = 12 -> shortfall = 7
    )
    res = DisasterSimulationEngine.run_simulation(req)

    assert len(res.results.shortages) == 2
    shortages_by_res = {s.resource: s for s in res.results.shortages}
    assert shortages_by_res["rescue_teams"].shortfall == 6
    assert shortages_by_res["ambulances"].shortfall == 7


def test_simulation_blocked_road_delay_calculation():
    """Verify that each blocked road contributes 5 minutes to response delay."""
    # 4 blocked roads, 0 team shortfall -> 4 * 5 = 20 minutes
    delay = DisasterSimulationEngine.compute_response_delay(blocked_roads=4, team_shortfall=0)
    assert delay == 20


def test_simulation_combined_response_delay():
    """Verify compound delay calculation: (blocked_roads * 5) + (team_shortfall * 2)."""
    # 3 blocked roads (15m) + 4 team shortfall (8m) = 23m
    delay = DisasterSimulationEngine.compute_response_delay(blocked_roads=3, team_shortfall=4)
    assert delay == 23


def test_simulation_negative_input_rejection():
    """Verify negative numerical values raise ValidationError."""
    with pytest.raises(ValidationError):
        SimulationRequest(
            scenario_name="Invalid negative population",
            affected_population=-100,
            disaster_severity=3,
            rescue_teams=4,
            blocked_roads=1,
            available_ambulances=4,
        )

    with pytest.raises(ValidationError):
        SimulationRequest(
            scenario_name="Invalid negative teams",
            affected_population=1000,
            disaster_severity=3,
            rescue_teams=-2,
            blocked_roads=1,
            available_ambulances=4,
        )

    with pytest.raises(ValidationError):
        SimulationRequest(
            scenario_name="Invalid negative roads",
            affected_population=1000,
            disaster_severity=3,
            rescue_teams=2,
            blocked_roads=-1,
            available_ambulances=4,
        )


def test_simulation_severity_outside_bounds_rejection():
    """Verify disaster_severity < 1 or > 5 raises ValidationError."""
    with pytest.raises(ValidationError):
        SimulationRequest(
            scenario_name="Severity 0",
            affected_population=1000,
            disaster_severity=0,
            rescue_teams=2,
            blocked_roads=1,
            available_ambulances=2,
        )

    with pytest.raises(ValidationError):
        SimulationRequest(
            scenario_name="Severity 6",
            affected_population=1000,
            disaster_severity=6,
            rescue_teams=2,
            blocked_roads=1,
            available_ambulances=2,
        )


def test_unknown_fields_rejected_by_public_request_schema():
    """Verify that public SimulationRequest forbids unknown fields."""
    with pytest.raises(ValidationError):
        SimulationRequest.model_validate({
            "scenario_name": "Test",
            "affected_population": 1000,
            "disaster_severity": 3,
            "rescue_teams": 2,
            "blocked_roads": 1,
            "available_ambulances": 2,
            "unknown_extra_field": "disallowed",
        })


def test_empty_incident_context_no_invented_priority_changes():
    """Verify that when incidents context is omitted, priority_changes is empty and no fake incidents are invented."""
    req = SimulationRequest(
        scenario_name="Scenario without incidents",
        affected_population=8000,
        disaster_severity=4,
        rescue_teams=4,
        blocked_roads=2,
        available_ambulances=3,
    )
    res = DisasterSimulationEngine.run_simulation(req)
    assert res.results.priority_changes == []


def test_supplied_incident_context_hypothetical_priority_changes():
    """Verify supplied incidents produce explainable hypothetical priority rank shifts when justified."""
    # inc_001: Flood, critical severity (baseline rank 1)
    inc_1 = IncidentInput(
        id="inc_001",
        title="Active flood at Lake Road",
        type="flood",
        severity="critical",
        status="active",
        location_label="Lake Road",
        independent_source_count=3,
    )
    # inc_002: Structural collapse, high severity (baseline rank 2)
    inc_2 = IncidentInput(
        id="inc_002",
        title="Reported structural collapse, Koramangala",
        type="structural",
        severity="high",
        status="active",
        location_label="Koramangala",
        independent_source_count=2,
    )

    # Scenario: Koramangala has blocked access roads and rescue teams have a shortfall
    internal_req = SimulationScenarioRequest(
        scenario_name="Heavy rain, 3 roads blocked",
        affected_population=12000,
        disaster_severity=4,
        rescue_teams=6,           # shortfall = 6
        blocked_roads=3,
        available_ambulances=10,
        incidents=[inc_1, inc_2],
        blocked_access_incident_ids=["inc_002"],  # Explicit access obstruction for inc_002
    )

    res = DisasterSimulationEngine.run_simulation(internal_req)

    # Priority changes should be detected
    assert len(res.results.priority_changes) >= 1
    p_changes_by_id = {pc.incident_id: pc for pc in res.results.priority_changes}

    # inc_002 should have moved up in rank
    assert "inc_002" in p_changes_by_id
    change_002 = p_changes_by_id["inc_002"]
    assert change_002.baseline_rank == 2
    assert change_002.scenario_rank == 1
    assert "Access roads blocked" in change_002.reason or "fewer teams" in change_002.reason


def test_no_mutation_of_original_incident_data():
    """Verify that running a simulation does not mutate the original incident input objects."""
    inc_original = IncidentInput(
        id="inc_audit",
        title="Original unmutated incident",
        type="flood",
        severity="medium",
        status="active",
        location_label="Indiranagar",
        timeline=[],
    )
    original_dump = inc_original.model_dump()

    req = SimulationScenarioRequest(
        scenario_name="Mutation check scenario",
        affected_population=5000,
        disaster_severity=3,
        rescue_teams=2,
        blocked_roads=4,
        available_ambulances=2,
        incidents=[inc_original],
        blocked_access_incident_ids=["inc_audit"],
    )

    DisasterSimulationEngine.run_simulation(req)

    # Original incident data must be strictly identical
    assert inc_original.model_dump() == original_dump
    assert len(inc_original.timeline) == 0


def test_explicit_road_access_impact_required_for_road_blockage_effects():
    """Verify that general blocked_roads does not artificially shift ranks without explicit access impact."""
    inc_1 = IncidentInput(
        id="inc_001",
        title="Flood event",
        type="flood",
        severity="critical",
        status="active",
        location_label="Area A",
    )
    inc_2 = IncidentInput(
        id="inc_002",
        title="Tree branch fallen",
        type="other",
        severity="low",
        status="active",
        location_label="Area B",
    )

    # 5 blocked roads, but blocked_access_incident_ids is empty
    req = SimulationScenarioRequest(
        scenario_name="Road blockage with no specific incident impact",
        affected_population=2000,
        disaster_severity=2,
        rescue_teams=10,
        blocked_roads=5,
        available_ambulances=10,
        incidents=[inc_1, inc_2],
        blocked_access_incident_ids=[],  # No incident explicitly blocked
    )

    res = DisasterSimulationEngine.run_simulation(req)
    # Relative ranks should remain undisturbed because resources are ample and no incident access is blocked
    assert res.results.priority_changes == []


def test_is_simulation_always_true():
    """Verify that is_simulation is strictly True and rejects False."""
    req = SimulationRequest(
        scenario_name="Flag check",
        affected_population=1000,
        disaster_severity=2,
        rescue_teams=5,
        blocked_roads=0,
        available_ambulances=5,
    )
    res = DisasterSimulationEngine.run_simulation(req)
    assert res.is_simulation is True

    # Attempting to construct a SimulationResponse with is_simulation=False must fail
    res_dict = res.model_dump()
    res_dict["is_simulation"] = False
    with pytest.raises(ValidationError):
        SimulationResponse.model_validate(res_dict)


def test_backend_simulation_response_compatibility():
    """Verify that AI Engine SimulationResponse can be parsed directly by Member 2's backend schema."""
    req = SimulationRequest(
        scenario_name="Backend schema bridge test",
        affected_population=10000,
        disaster_severity=4,
        rescue_teams=5,
        blocked_roads=2,
        available_ambulances=4,
    )
    ai_response = DisasterSimulationEngine.run_simulation(req)
    payload = ai_response.model_dump(mode="json")

    backend_response = BackendSimulationResponse.model_validate(payload)
    assert backend_response.scenario_id.startswith("sim_")
    assert backend_response.is_simulation is True
    assert backend_response.inputs.scenario_name == "Backend schema bridge test"
    assert backend_response.results.resource_demand.rescue_teams == ai_response.results.resource_demand.rescue_teams


def test_fastapi_simulate_endpoint():
    """Verify POST /simulate via FastAPI TestClient."""
    payload = {
        "scenario_name": "Heavy rain, 3 roads blocked",
        "affected_population": 12000,
        "disaster_severity": 4,
        "rescue_teams": 6,
        "blocked_roads": 3,
        "available_ambulances": 5,
    }

    resp = client.post("/simulate", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["scenario_id"].startswith("sim_")
    assert data["is_simulation"] is True
    assert data["inputs"]["scenario_name"] == payload["scenario_name"]
    assert "resource_demand" in data["results"]
    assert "shortages" in data["results"]
    assert "estimated_response_delay_minutes" in data["results"]
    assert "priority_changes" in data["results"]
    assert "summary" in data["results"]


def test_fastapi_simulation_run_rpc_endpoint():
    """Verify POST /simulation/run RPC alias via FastAPI TestClient."""
    payload = {
        "scenario_name": "RPC simulation scenario",
        "affected_population": 8000,
        "disaster_severity": 3,
        "rescue_teams": 5,
        "blocked_roads": 2,
        "available_ambulances": 4,
        "incidents": [
            {
                "id": "inc_001",
                "title": "Incident 1",
                "type": "flood",
                "severity": "critical",
                "status": "active",
                "location_label": "Loc 1",
            },
            {
                "id": "inc_002",
                "title": "Incident 2",
                "type": "structural",
                "severity": "high",
                "status": "active",
                "location_label": "Loc 2",
            },
        ],
        "blocked_access_incident_ids": ["inc_002"],
    }

    resp = client.post("/simulation/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["scenario_id"].startswith("sim_")
    assert data["is_simulation"] is True
    assert data["inputs"]["scenario_name"] == "RPC simulation scenario"
    assert len(data["results"]["priority_changes"]) >= 1


def test_fastapi_simulate_validation_error_on_unknown_fields():
    """Verify POST /simulate rejects unknown payload fields with HTTP 422."""
    payload = {
        "scenario_name": "Scenario with illegal field",
        "affected_population": 5000,
        "disaster_severity": 3,
        "rescue_teams": 4,
        "blocked_roads": 1,
        "available_ambulances": 3,
        "forbidden_extra": "not_allowed",
    }
    resp = client.post("/simulate", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data
    assert any("forbidden_extra" in str(err) for err in data["detail"])


def test_simulation_empty_scenario_name_rejection():
    """Verify that an empty scenario_name is strictly rejected."""
    with pytest.raises(ValidationError):
        SimulationRequest(
            scenario_name="",
            affected_population=5000,
            disaster_severity=3,
            rescue_teams=4,
            blocked_roads=1,
            available_ambulances=3,
        )

    resp = client.post("/simulate", json={
        "scenario_name": "",
        "affected_population": 5000,
        "disaster_severity": 3,
        "rescue_teams": 4,
        "blocked_roads": 1,
        "available_ambulances": 3,
    })
    assert resp.status_code == 422


def test_simulation_negative_available_ambulances_rejection():
    """Verify that negative available_ambulances is strictly rejected."""
    with pytest.raises(ValidationError):
        SimulationRequest(
            scenario_name="Negative ambulance test",
            affected_population=5000,
            disaster_severity=3,
            rescue_teams=4,
            blocked_roads=1,
            available_ambulances=-1,
        )

    resp = client.post("/simulate", json={
        "scenario_name": "Negative ambulance test",
        "affected_population": 5000,
        "disaster_severity": 3,
        "rescue_teams": 4,
        "blocked_roads": 1,
        "available_ambulances": -1,
    })
    assert resp.status_code == 422


def test_simulation_sequential_scenario_comparison():
    """Verify Section 4.9 scenario comparison: two sequential runs produce independent IDs and different delay outputs."""
    # Scenario A: Mild disruption (2 roads blocked, ample teams)
    req_a = SimulationRequest(
        scenario_name="Scenario A: Mild disruption",
        affected_population=12000,
        disaster_severity=4,
        rescue_teams=12,  # No team shortfall (demand = 12)
        blocked_roads=2,   # Delay: 2 * 5 = 10m
        available_ambulances=12,
    )
    res_a = DisasterSimulationEngine.run_simulation(req_a)

    # Scenario B: Severe disruption (5 roads blocked, severe team shortfall)
    req_b = SimulationRequest(
        scenario_name="Scenario B: Severe disruption",
        affected_population=12000,
        disaster_severity=4,
        rescue_teams=2,   # Team shortfall: 12 - 2 = 10
        blocked_roads=5,   # Delay: (5 * 5) + (10 * 2) = 25 + 20 = 45m
        available_ambulances=12,
    )
    res_b = DisasterSimulationEngine.run_simulation(req_b)

    # Independent scenario IDs
    assert res_a.scenario_id != res_b.scenario_id
    assert res_a.scenario_id.startswith("sim_")
    assert res_b.scenario_id.startswith("sim_")

    # Differential delays
    assert res_a.results.estimated_response_delay_minutes == 10
    assert res_b.results.estimated_response_delay_minutes == 45
    assert res_a.results.estimated_response_delay_minutes < res_b.results.estimated_response_delay_minutes

    # Distinct echoed inputs
    assert res_a.inputs.scenario_name == "Scenario A: Mild disruption"
    assert res_b.inputs.scenario_name == "Scenario B: Severe disruption"


def test_fastapi_simulation_run_malformed_incident_context():
    """Verify that passing malformed incident context to /simulation/run returns HTTP 422."""
    payload = {
        "scenario_name": "Malformed incident test",
        "affected_population": 5000,
        "disaster_severity": 3,
        "rescue_teams": 4,
        "blocked_roads": 1,
        "available_ambulances": 3,
        "incidents": [
            {
                # Missing required 'id' and 'title'
                "type": "flood",
                "severity": "critical",
            }
        ],
    }
    resp = client.post("/simulation/run", json=payload)
    assert resp.status_code == 422


def test_ambulance_shortage_only_attributed_to_medically_relevant_incidents():
    """Verify ambulance shortage reason is only attributed to incidents with medical relevance or casualties."""
    # Baseline Rank 1: Critical flood with rising water (Urgency score 90)
    inc_water = IncidentInput(
        id="inc_flood",
        title="Rapidly rising water on main avenue",
        type="flood",
        severity="critical",
        status="active",
        location_label="Main Avenue",
        reports=[
            ReportInput(
                id="rpt_f_1",
                text="Water level is rising rapidly across the road.",
                source_type="citizen",
                reported_at="2026-11-12T14:00:00Z",
            )
        ],
    )
    # Baseline Rank 2: Medium severity medical clinic request with 1 injured person (Urgency score 85)
    inc_medical = IncidentInput(
        id="inc_med",
        title="Clinic emergency with injured patients",
        type="medical",
        severity="medium",
        status="active",
        location_label="City Clinic",
        reports=[
            ReportInput(
                id="rpt_med_1",
                text="One injured citizen awaiting medical care.",
                source_type="citizen",
                reported_at="2026-11-12T14:00:00Z",
            )
        ],
    )

    req = SimulationScenarioRequest(
        scenario_name="Medical triage scenario",
        affected_population=12000,
        disaster_severity=4,
        rescue_teams=20,            # No team shortfall
        blocked_roads=3,
        available_ambulances=0,     # Severe ambulance shortfall (shortfall = 12)
        incidents=[inc_water, inc_medical],
        blocked_access_incident_ids=["inc_med"],
    )

    res = DisasterSimulationEngine.run_simulation(req)
    assert len(res.results.priority_changes) >= 1
    changes = {pc.incident_id: pc for pc in res.results.priority_changes}

    # inc_med is medically relevant -> reason MUST include emergency transport constraint
    assert "inc_med" in changes
    assert "emergency transport constrained" in changes["inc_med"].reason

    # inc_flood is purely flood with no casualties -> reason must NOT falsely claim emergency transport constraint
    if "inc_flood" in changes:
        assert "emergency transport constrained" not in changes["inc_flood"].reason
