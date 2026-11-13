"""
CrisisLens Evidence Relationship Graph Service
Implements GET /incidents/{id}/evidence-graph per API Contract v1.0 Section 4.8.
Node ID equals the Report ID.
Edges point from the later/derived report (source) to the earlier/reference report (target).
Delegates intelligent graph generation to Member 3 AI Engine (POST /incidents/{id}/evidence-graph)
with safe fallback to stored relational records without synthetic edges.
"""
import logging
from typing import List, Dict, Any, Set
from app.database.supabase_client import get_supabase_client
from app.schemas.evidence import EvidenceGraphResponse, GraphNode, GraphEdge
from app.schemas.common import SourceType, FreshnessStatus, RelationshipType
from app.utils.datetime_utils import calculate_freshness
from app.services.ai_client import AIClient
from app.core.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class EvidenceService:
    @staticmethod
    def get_evidence_graph(incident_id: str) -> EvidenceGraphResponse:
        supabase = get_supabase_client()

        # 1. Verify incident exists
        inc_res = supabase.table("incidents").select("*").eq("id", incident_id).limit(1).execute()
        if not inc_res.data:
            raise NotFoundException("Incident", incident_id)

        # 2. Fetch associated reports
        rep_res = supabase.table("reports").select("*").eq("incident_id", incident_id).order("reported_at", desc=False).execute()
        reports = rep_res.data or []

        # If no reports directly linked, check reports near same location or recent
        if not reports:
            inc_loc = inc_res.data[0].get("location_label", "")
            rep_res = supabase.table("reports").select("*").ilike("location_label", f"%{inc_loc[:10]}%").order("reported_at", desc=False).limit(10).execute()
            reports = rep_res.data or []

        all_report_ids: Set[str] = set(rep["id"] for rep in reports)

        # 3. Fetch explicit conflicts recorded in analysis_results for these reports
        conflicts_list: List[Dict[str, Any]] = []
        if all_report_ids:
            try:
                ar_res = supabase.table("analysis_results").select("raw_analysis").in_("report_id", list(all_report_ids)).execute()
                for row in (ar_res.data or []):
                    raw = row.get("raw_analysis") or {}
                    raw_conflicts = raw.get("conflicts") or []
                    for c in raw_conflicts:
                        if isinstance(c, dict) and c.get("id"):
                            if not any(x.get("id") == c["id"] for x in conflicts_list):
                                conflicts_list.append(c)
            except Exception as exc:
                logger.warning("Could not fetch conflict records for incident %s: %s", incident_id, exc)

        # 4. Attempt to generate evidence graph via Member 3 AI Engine endpoint:
        # POST /incidents/{incident_id}/evidence-graph
        ai_graph = AIClient.generate_evidence_graph(
            incident_id=incident_id,
            reports=reports,
            conflicts=conflicts_list,
        )
        if ai_graph is not None:
            # Defensive check: ensure every edge connects existing nodes in the graph
            valid_node_ids = {n.id for n in ai_graph.nodes}
            ai_graph.edges = [
                e for e in ai_graph.edges
                if e.source in valid_node_ids and e.target in valid_node_ids and e.source != e.target
            ]
            return ai_graph

        # 5. Deterministic Fallback: Build graph using actual stored relationships
        # Never invent evidence relationships or assume chronological order proves corroboration.
        role_map: Dict[str, RelationshipType] = {}
        raw_edges_data: List[Dict[str, Any]] = []
        if all_report_ids:
            # Fetch edges where this report is the source (later/derived)
            src_res = supabase.table("report_relationships").select("*").in_(
                "source_report_id", list(all_report_ids)
            ).execute()
            raw_edges_data.extend(src_res.data or [])

            # Fetch edges where this report is the target (earlier/reference)
            tgt_res = supabase.table("report_relationships").select("*").in_(
                "target_report_id", list(all_report_ids)
            ).execute()
            # Avoid duplicates
            seen_ids = {e["id"] for e in raw_edges_data}
            for e in (tgt_res.data or []):
                if e["id"] not in seen_ids:
                    raw_edges_data.append(e)

            # Invariant: Only consider edges where BOTH source and target exist in this incident's nodes
            valid_raw_edges = [
                e for e in raw_edges_data
                if e.get("source_report_id") in all_report_ids and e.get("target_report_id") in all_report_ids
            ]

            # Derive role from stored relationship type
            for e in valid_raw_edges:
                src_id = e["source_report_id"]
                rel_type = e["type"]
                if rel_type == "forwarded":
                    role_map[src_id] = RelationshipType.FORWARDED
                elif rel_type == "duplicate":
                    if src_id not in role_map:
                        role_map[src_id] = RelationshipType.DUPLICATE
                elif rel_type == "corroborating":
                    if src_id not in role_map:
                        role_map[src_id] = RelationshipType.CORROBORATING
                elif rel_type == "conflicting":
                    if src_id not in role_map:
                        role_map[src_id] = RelationshipType.CONFLICTING

        nodes: List[GraphNode] = []
        report_ids: Set[str] = set()

        for rep in reports:
            r_id = rep["id"]
            report_ids.add(r_id)

            # Determine role: forwarded_from field always wins
            if rep.get("forwarded_from"):
                role = RelationshipType.FORWARDED
            elif r_id in role_map:
                role = role_map[r_id]
            else:
                # Only mark as original if not classified by any stored relationship.
                role = RelationshipType.ORIGINAL

            # Freshness
            freshness = calculate_freshness(rep["reported_at"])
            fresh_status = FreshnessStatus(freshness["status"])

            # Excerpt
            txt = rep.get("text", "")
            excerpt = (txt[:60] + "...") if len(txt) > 60 else txt

            node = GraphNode(
                id=r_id,
                report_id=r_id,
                label=f"{rep['source_type'].capitalize()}: {rep['location_label']}",
                role=role,
                source_type=SourceType(rep["source_type"]),
                source_name=rep["source_name"],
                timestamp=rep["reported_at"],
                excerpt=excerpt,
                freshness_status=fresh_status,
            )
            nodes.append(node)

        # Build edges from actual stored relationships only — never invent edges
        # Invariant: An edge is strictly valid ONLY if BOTH source and target exist in this graph's nodes
        node_id_set = {n.id for n in nodes}
        report_time_map = {rep["id"]: rep.get("reported_at", "") for rep in reports}
        edges: List[GraphEdge] = []
        seen_pairs: Set[tuple] = set()

        for re in raw_edges_data:
            src_id = re["source_report_id"]
            tgt_id = re["target_report_id"]

            # Edge must connect two existing nodes in this incident graph and not be a self-loop
            if src_id not in node_id_set or tgt_id not in node_id_set or src_id == tgt_id:
                continue

            # Ensure direction: later/derived (source) -> earlier/reference (target)
            t_src = report_time_map.get(src_id, "")
            t_tgt = report_time_map.get(tgt_id, "")
            if t_src and t_tgt:
                if t_src < t_tgt:
                    src_id, tgt_id = tgt_id, src_id
                elif t_src == t_tgt and src_id < tgt_id:
                    src_id, tgt_id = tgt_id, src_id

            pair = (src_id, tgt_id)
            reciprocal = (tgt_id, src_id)
            if pair in seen_pairs or reciprocal in seen_pairs:
                continue
            seen_pairs.add(pair)

            edges.append(
                GraphEdge(
                    id=re["id"],
                    source=src_id,  # later/derived report
                    target=tgt_id,  # earlier/reference report
                    type=RelationshipType(re["type"]),
                    label=re.get("label") or f"{re['type'].capitalize()} ({re.get('confidence', 1.0):.2f})",
                    confidence=re.get("confidence", 1.0),
                )
            )
        # If no stored relationships exist, edges remains [] — this is strictly compliant.

        return EvidenceGraphResponse(
            incident_id=incident_id,
            nodes=nodes,
            edges=edges,
        )
