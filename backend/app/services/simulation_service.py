"""
CrisisLens What-If Emergency Simulation Service
Implements POST /simulate per API Contract v1.0 Section 4.9.
Strictly isolated from live emergency records.
Delegates scenario simulation to Member 3 AI Engine (POST /simulation/run)
with resilient fallback to deterministic scenario calculation.
"""
import logging
from typing import List, Dict, Any
from app.database.supabase_client import get_supabase_client
from app.schemas.simulation import (
    SimulationRequest,
    SimulationResponse,
    SimulationResults,
    ResourceDemand,
    ResourceShortage,
    PriorityChange,
)
from app.services.ai_client import AIClient
from app.utils.id_generator import generate_simulation_id
from app.utils.datetime_utils import now_utc_iso

logger = logging.getLogger(__name__)


class SimulationService:
    @staticmethod
    def run_simulation(payload: SimulationRequest) -> SimulationResponse:
        supabase = get_supabase_client()

        # 1. Gather active incidents context for simulation
        live_incidents: List[Dict[str, Any]] = []
        try:
            incidents_res = supabase.table("incidents").select("*").execute()
            live_incidents = incidents_res.data or []
        except Exception as exc:
            logger.warning("Could not fetch incidents for simulation context: %s", exc)

        # 2. Build incident context payload for Member 3 AI Engine
        batch_incidents: List[Dict[str, Any]] = []
        if live_incidents:
            inc_ids = [inc["id"] for inc in live_incidents]
            reports_by_inc: Dict[str, List[Dict[str, Any]]] = {}
            try:
                reps_res = supabase.table("reports").select("*").in_("incident_id", inc_ids).execute()
                for r in (reps_res.data or []):
                    reports_by_inc.setdefault(r.get("incident_id"), []).append(r)
            except Exception:
                pass

            for inc in live_incidents:
                loc = inc.get("location")
                if isinstance(loc, dict):
                    lat = loc.get("lat", inc.get("lat", 0.0))
                    lng = loc.get("lng", inc.get("lng", 0.0))
                    label = loc.get("label", inc.get("location_label", "Unknown"))
                else:
                    lat = inc.get("lat") or inc.get("location_lat") or 0.0
                    lng = inc.get("lng") or inc.get("location_lng") or 0.0
                    label = inc.get("location_label", "Unknown")

                inc_reps = reports_by_inc.get(inc["id"], [])
                batch_incidents.append({
                    "id": inc["id"],
                    "title": inc["title"],
                    "type": inc.get("type", "other"),
                    "severity": inc.get("severity", "medium"),
                    "status": inc.get("status", "active"),
                    "location_label": label,
                    "lat": lat,
                    "lng": lng,
                    "report_count": inc.get("report_count") or len(inc_reps),
                    "first_reported_at": inc.get("first_reported_at"),
                    "last_updated_at": inc.get("last_updated_at"),
                    "timeline": inc.get("timeline") or [],
                    "reports": inc_reps,
                })

        # 3. Try to run simulation via Member 3's AI Engine
        # Pass blocked_access_incident_ids only when actual road-access impact is explicitly known
        ai_response = AIClient.run_simulation(
            payload=payload,
            incidents=batch_incidents,
            blocked_access_incident_ids=[],
        )

        if ai_response is not None:
            # Persist to simulations table (Strictly isolated storage)
            sim_row = {
                "id": ai_response.scenario_id,
                "scenario_name": payload.scenario_name,
                "is_simulation": True,
                "generated_at": ai_response.generated_at,
                "inputs": payload.model_dump(mode="json"),
                "results": ai_response.results.model_dump(mode="json"),
            }
            try:
                supabase.table("simulations").insert(sim_row).execute()
            except Exception as exc:
                logger.warning("Could not persist AI simulation results to DB: %s", exc)

            return ai_response

        # 4. Resilient Fallback: Deterministic simulation calculation
        logger.info("Using deterministic fallback simulation calculation.")
        sim_id = generate_simulation_id()
        generated_at = now_utc_iso()

        # Compute resource demand based on parameters
        demanded_teams = max(2, int((payload.affected_population / 1500.0) * (payload.disaster_severity / 2.5)))
        demanded_ambulances = max(2, int((payload.affected_population / 2000.0) * (payload.disaster_severity / 2.0)))

        # Compute shortages
        shortages: List[ResourceShortage] = []
        team_shortfall = max(0, demanded_teams - payload.rescue_teams)
        if team_shortfall > 0:
            shortages.append(
                ResourceShortage(
                    resource="rescue_teams",
                    required=demanded_teams,
                    available=payload.rescue_teams,
                    shortfall=team_shortfall,
                )
            )

        amb_shortfall = max(0, demanded_ambulances - payload.available_ambulances)
        if amb_shortfall > 0:
            shortages.append(
                ResourceShortage(
                    resource="ambulances",
                    required=demanded_ambulances,
                    available=payload.available_ambulances,
                    shortfall=amb_shortfall,
                )
            )

        # Estimated response delay
        delay_minutes = (payload.blocked_roads * 5) + (team_shortfall * 2)

        # Fallback priority changes under this scenario
        priority_changes: List[PriorityChange] = []
        try:
            if live_incidents and (payload.blocked_roads > 0 or team_shortfall > 0):
                inc_ids = [i["id"] for i in live_incidents]
                scores_res = supabase.table("priority_scores").select("incident_id, urgency_score").in_(
                    "incident_id", inc_ids
                ).execute()
                scores_map = {s["incident_id"]: s["urgency_score"] for s in (scores_res.data or [])}

                severity_fallback = {"critical": 90, "high": 70, "medium": 50, "low": 25}
                ranked = sorted(
                    live_incidents,
                    key=lambda i: scores_map.get(i["id"], severity_fallback.get(i.get("severity", "medium"), 50)),
                    reverse=True,
                )

                for baseline_rank, inc in enumerate(ranked, start=1):
                    base_score = scores_map.get(inc["id"], severity_fallback.get(inc.get("severity", "medium"), 50))
                    road_penalty = payload.blocked_roads * 5
                    team_penalty = team_shortfall * 3

                    if road_penalty > 0 or team_penalty > 0:
                        scenario_scores = {
                            i["id"]: max(0, scores_map.get(i["id"], severity_fallback.get(i.get("severity", "medium"), 50))
                                         - payload.blocked_roads * 5 - team_shortfall * 3)
                            for i in ranked
                        }
                        scenario_ranked = sorted(ranked, key=lambda i: scenario_scores[i["id"]], reverse=True)
                        scenario_rank = next(
                            (idx + 1 for idx, si in enumerate(scenario_ranked) if si["id"] == inc["id"]), baseline_rank
                        )
                        if scenario_rank != baseline_rank:
                            reasons = []
                            if payload.blocked_roads > 0:
                                reasons.append(f"{payload.blocked_roads} road(s) blocked, slowing access")
                            if team_shortfall > 0:
                                reasons.append(f"Rescue team shortfall of {team_shortfall}")
                            priority_changes.append(
                                PriorityChange(
                                    incident_id=inc["id"],
                                    title=inc["title"],
                                    baseline_rank=baseline_rank,
                                    scenario_rank=scenario_rank,
                                    reason="; ".join(reasons),
                                )
                            )
        except Exception:
            priority_changes = []

        if shortages:
            parts = [f"{s.resource.replace('_', ' ')} are short by {s.shortfall}" for s in shortages]
            summary = f"{', '.join(parts).capitalize()} under this scenario. Estimated response delay: {delay_minutes} minutes."
        else:
            summary = f"All resource demands satisfied under this scenario. Estimated response delay: {delay_minutes} minutes."

        results = SimulationResults(
            resource_demand=ResourceDemand(
                rescue_teams=demanded_teams,
                ambulances=demanded_ambulances,
            ),
            shortages=shortages,
            estimated_response_delay_minutes=delay_minutes,
            priority_changes=priority_changes,
            summary=summary,
        )

        response_obj = SimulationResponse(
            scenario_id=sim_id,
            is_simulation=True,
            generated_at=generated_at,
            inputs=payload,
            results=results,
        )

        # Persist to simulations table (Isolated storage)
        sim_row = {
            "id": sim_id,
            "scenario_name": payload.scenario_name,
            "is_simulation": True,
            "generated_at": generated_at,
            "inputs": payload.model_dump(mode="json"),
            "results": results.model_dump(mode="json"),
        }
        try:
            supabase.table("simulations").insert(sim_row).execute()
        except Exception:
            pass

        return response_obj
