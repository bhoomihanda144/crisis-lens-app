"""What-if Emergency Disaster Simulation Engine (Stage 6).

Implements CrisisLens API Contract v1.0 Section 4.9.
Computes deterministic what-if emergency scenario modeling:
- Resource Demand: Scaled to affected population and disaster severity.
- Resource Shortages: Deficits between demanded and available resources.
- Response Delay: Projected operational delay factoring arterial road blockages and team deficits.
- Hypothetical Priority Changes: Re-evaluates incident urgency shifts under simulated access constraints.
- Explainability: Produces actionable, transparent summaries for responder readiness.

Strict safety invariants:
- Complete isolation: Does not alter live disaster records or live priority scores.
- `is_simulation: True` invariant on all responses.
- Advisory only: No automatic dispatch or resource allocation is executed.
- No invented incidents: Empty or missing incident context yields an empty `priority_changes` list.
"""

import uuid
from typing import List, Optional, Tuple, Union
from datetime import datetime, timezone

from ai_engine.schemas.enums import PrioritySort, IncidentSeverity, IncidentStatus
from ai_engine.schemas.simulation import (
    SimulationRequest,
    ResourceDemand,
    ResourceShortage,
    PriorityChange,
    SimulationResults,
    SimulationResponse,
)
from ai_engine.schemas.incident import TimelineEntry
from ai_engine.schemas.internal import IncidentInput, SimulationScenarioRequest
from ai_engine.modules.priority import IncidentPriorityRanker


class DisasterSimulationEngine:
    """Deterministic what-if emergency disaster simulation engine."""

    @classmethod
    def compute_resource_demand(
        cls,
        affected_population: int,
        disaster_severity: int,
    ) -> ResourceDemand:
        """Calculates required rescue teams and ambulances.

        Formulas (consistent with established backend baseline):
            rescue_teams = max(2, floor((affected_population / 1500.0) * (disaster_severity / 2.5)))
            ambulances   = max(2, floor((affected_population / 2000.0) * (disaster_severity / 2.0)))

        Assumptions:
        - Baseline minimum of 2 teams and 2 ambulances required for any declared disaster zone.
        - Demand scales linearly with population and disaster severity.
        - Population 0 yields minimum baseline demand (2 teams, 2 ambulances).
        """
        demanded_teams = max(2, int((affected_population / 1500.0) * (disaster_severity / 2.5)))
        demanded_ambulances = max(2, int((affected_population / 2000.0) * (disaster_severity / 2.0)))
        return ResourceDemand(
            rescue_teams=demanded_teams,
            ambulances=demanded_ambulances,
        )

    @classmethod
    def compute_shortages(
        cls,
        demanded: ResourceDemand,
        available_rescue_teams: int,
        available_ambulances: int,
    ) -> Tuple[List[ResourceShortage], int, int]:
        """Calculates resource deficits.

        Rule:
        - Only resources with a non-zero shortfall (required > available) are included.
        """
        shortages: List[ResourceShortage] = []

        team_shortfall = max(0, demanded.rescue_teams - available_rescue_teams)
        if team_shortfall > 0:
            shortages.append(
                ResourceShortage(
                    resource="rescue_teams",
                    required=demanded.rescue_teams,
                    available=available_rescue_teams,
                    shortfall=team_shortfall,
                )
            )

        amb_shortfall = max(0, demanded.ambulances - available_ambulances)
        if amb_shortfall > 0:
            shortages.append(
                ResourceShortage(
                    resource="ambulances",
                    required=demanded.ambulances,
                    available=available_ambulances,
                    shortfall=amb_shortfall,
                )
            )

        return shortages, team_shortfall, amb_shortfall

    @classmethod
    def compute_response_delay(
        cls,
        blocked_roads: int,
        team_shortfall: int,
    ) -> int:
        """Calculates estimated operational response delay in minutes.

        Formula (consistent with established backend baseline):
            delay_minutes = (blocked_roads * 5) + (team_shortfall * 2)

        Assumptions:
        - Each impassable arterial road adds an estimated average detour delay of 5 minutes.
        - Each missing rescue team adds an estimated 2-minute delay due to dispatch queue backlog.
        - Delay is non-negative and 0 when roads are clear and teams are fully staffed.
        """
        return max(0, (blocked_roads * 5) + (team_shortfall * 2))

    @classmethod
    def _has_medical_relevance(cls, incident: IncidentInput) -> bool:
        """Determines if an incident has explicit medical relevance or reported casualties."""
        if incident.type and incident.type.lower() == "medical":
            return True

        if incident.reports:
            medical_keywords = {
                "injured", "injury", "injuries", "casualty", "casualties",
                "unconscious", "medical", "ambulance", "drowning", "fatal", "suffocation",
            }
            for r in incident.reports:
                txt_lower = r.text.lower()
                if any(w in txt_lower for w in medical_keywords):
                    return True

        return False

    @classmethod
    def compute_priority_changes(
        cls,
        incidents: Optional[List[IncidentInput]],
        blocked_access_incident_ids: Optional[List[str]],
        team_shortfall: int,
        amb_shortfall: int,
        blocked_roads: int,
    ) -> List[PriorityChange]:
        """Calculates hypothetical priority rank changes under scenario operational stress.

        Strict Rules:
        - When incidents is missing or empty, returns an empty list (never invent fake IDs).
        - Clones incident objects; never mutates live incident inputs or database state.
        - Only applies incident-specific road-blockage effects when explicit access-impact
          information (blocked_access_incident_ids) is provided by the caller.
        - Preserves actual historical timeline data without fabricating fake historical events.
        - Returns only incidents whose priority ranks actually change.
        """
        if not incidents:
            return []

        # In-memory deep clones to strictly prevent mutating caller objects
        cloned_baseline = [inc.model_copy(deep=True) for inc in incidents]
        cloned_scenario = [inc.model_copy(deep=True) for inc in incidents]
        inc_obj_map = {inc.id: inc for inc in incidents}

        # 1. Baseline ranking using Stage 5 IncidentPriorityRanker
        baseline_resp = IncidentPriorityRanker.rank_incidents(cloned_baseline, sort=PrioritySort.URGENCY)
        baseline_map = {item.incident_id: item for item in baseline_resp.items}

        # 2. Scenario adjustments on cloned scenario incidents
        blocked_set = set(blocked_access_incident_ids or [])

        for inc in cloned_scenario:
            # Preserve latest actual timeline radius when available; fallback to 600 as scenario value
            latest_radius = inc.timeline[-1].affected_radius_m if inc.timeline else 600

            # Apply explicit road-access impact only when provided
            if inc.id in blocked_set and blocked_roads > 0:
                # Access route is blocked; simulate compressed rescue window by escalating severity and appending simulated entry
                inc.severity = IncidentSeverity.CRITICAL.value
                inc.timeline.append(
                    TimelineEntry(
                        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        severity=IncidentSeverity.CRITICAL,
                        status=IncidentStatus.ACTIVE,
                        report_count=max(1, inc.report_count or 1),
                        affected_radius_m=max(600, latest_radius),
                        summary="Access corridor blocked by simulated arterial road obstruction; urgent rescue routing required",
                    )
                )

            # Apply resource scarcity stress
            # Structural emergencies with rescue team shortfalls
            if inc.type.lower() == "structural" and team_shortfall > 0:
                inc.timeline.append(
                    TimelineEntry(
                        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        severity=IncidentSeverity.CRITICAL,
                        status=IncidentStatus.ACTIVE,
                        report_count=max(1, inc.report_count or 1),
                        affected_radius_m=max(500, latest_radius),
                        summary="Structural collapse extraction compounded by simulated rescue team deficit",
                    )
                )

            # Medical emergencies with ambulance shortfalls
            if (inc.type.lower() == "medical" or cls._has_medical_relevance(inc)) and amb_shortfall > 0:
                inc.timeline.append(
                    TimelineEntry(
                        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        severity=IncidentSeverity.CRITICAL,
                        status=IncidentStatus.ACTIVE,
                        report_count=max(1, inc.report_count or 1),
                        affected_radius_m=max(500, latest_radius),
                        summary="Emergency medical transport triage compounded by simulated ambulance deficit",
                    )
                )

        # 3. Scenario ranking
        scenario_resp = IncidentPriorityRanker.rank_incidents(cloned_scenario, sort=PrioritySort.URGENCY)
        scenario_map = {item.incident_id: item for item in scenario_resp.items}

        # 4. Identify actual rank shifts
        priority_changes: List[PriorityChange] = []

        for inc_id, b_item in baseline_map.items():
            s_item = scenario_map.get(inc_id)
            if not s_item:
                continue

            if b_item.rank != s_item.rank:
                # Formulate explainable reason
                reasons: List[str] = []
                if inc_id in blocked_set:
                    reasons.append("Access roads blocked")
                if team_shortfall > 0:
                    reasons.append("fewer teams available")

                # Attach emergency transport constraint only when incident has explicit medical relevance
                inc_ref = inc_obj_map.get(inc_id)
                if amb_shortfall > 0 and inc_ref and cls._has_medical_relevance(inc_ref):
                    reasons.append("emergency transport constrained")

                if reasons:
                    reason_str = ", ".join(reasons).capitalize()
                else:
                    reason_str = f"Operational constraints shifted queue position from #{b_item.rank} to #{s_item.rank}"

                priority_changes.append(
                    PriorityChange(
                        incident_id=inc_id,
                        title=b_item.title,
                        baseline_rank=b_item.rank,
                        scenario_rank=s_item.rank,
                        reason=reason_str,
                    )
                )

        # Sort deterministically by scenario_rank ascending
        priority_changes.sort(key=lambda x: (x.scenario_rank, x.incident_id))
        return priority_changes

    @classmethod
    def generate_summary(
        cls,
        shortages: List[ResourceShortage],
        delay_minutes: int,
        priority_changes: List[PriorityChange],
    ) -> str:
        """Generates an explainable summary of simulation projections."""
        if shortages:
            parts = [f"{s.resource.replace('_', ' ')} are short by {s.shortfall}" for s in shortages]
            summary = f"{', '.join(parts).capitalize()} under this scenario. Estimated response delay: {delay_minutes} minutes."
        else:
            summary = f"All resource demands satisfied under this scenario. Estimated response delay: {delay_minutes} minutes."

        if priority_changes:
            summary += f" {len(priority_changes)} incident priority ranking change(s) projected under simulated constraints."

        summary += " Note: Projections are hypothetical planning estimates for responder readiness and do not constitute automated dispatch actions."
        return summary

    @classmethod
    def run_simulation(
        cls,
        request: Union[SimulationRequest, SimulationScenarioRequest],
    ) -> SimulationResponse:
        """Runs what-if disaster scenario simulation adhering strictly to API Contract Section 4.9."""
        # 1. Resource demand
        demand = cls.compute_resource_demand(
            affected_population=request.affected_population,
            disaster_severity=request.disaster_severity,
        )

        # 2. Resource shortages
        shortages, team_shortfall, amb_shortfall = cls.compute_shortages(
            demanded=demand,
            available_rescue_teams=request.rescue_teams,
            available_ambulances=request.available_ambulances,
        )

        # 3. Estimated response delay
        delay_minutes = cls.compute_response_delay(
            blocked_roads=request.blocked_roads,
            team_shortfall=team_shortfall,
        )

        # 4. Priority changes
        incidents = getattr(request, "incidents", None) or []
        blocked_access_ids = getattr(request, "blocked_access_incident_ids", None) or []

        priority_changes = cls.compute_priority_changes(
            incidents=incidents,
            blocked_access_incident_ids=blocked_access_ids,
            team_shortfall=team_shortfall,
            amb_shortfall=amb_shortfall,
            blocked_roads=request.blocked_roads,
        )

        # 5. Summary
        summary = cls.generate_summary(
            shortages=shortages,
            delay_minutes=delay_minutes,
            priority_changes=priority_changes,
        )

        results = SimulationResults(
            resource_demand=demand,
            shortages=shortages,
            estimated_response_delay_minutes=delay_minutes,
            priority_changes=priority_changes,
            summary=summary,
        )

        # Ensure public request shape is echoed in inputs
        if isinstance(request, SimulationRequest):
            public_inputs = request
        else:
            public_inputs = SimulationRequest(
                scenario_name=request.scenario_name,
                affected_population=request.affected_population,
                disaster_severity=request.disaster_severity,
                rescue_teams=request.rescue_teams,
                blocked_roads=request.blocked_roads,
                available_ambulances=request.available_ambulances,
            )

        sim_id = f"sim_{uuid.uuid4().hex[:8]}"
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return SimulationResponse(
            scenario_id=sim_id,
            is_simulation=True,
            generated_at=generated_at,
            inputs=public_inputs,
            results=results,
        )
