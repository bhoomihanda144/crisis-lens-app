"""
CrisisLens Semantic ID Generator
Generates public IDs strictly adhering to API Contract v1.0:
- Reports: rpt_001, rpt_002...
- Incidents: inc_001, inc_002...
- Simulations: sim_001, sim_002...
- Conflicts: cfl_001, cfl_002...
- Edges: edge_001, edge_002...
"""
import uuid
from typing import Optional
from app.database.supabase_client import get_supabase_client


def generate_semantic_id(prefix: str, table_name: Optional[str] = None) -> str:
    """
    Generates a contract-compliant semantic ID.
    If table_name is given, counts existing records to produce a clean sequential ID (e.g. rpt_001),
    falling back to a short random hash if needed to avoid conflicts.
    """
    if table_name:
        try:
            supabase = get_supabase_client()
            res = supabase.table(table_name).select("id", count="exact").execute()
            next_num = (res.count or 0) + 1
            proposed_id = f"{prefix}_{next_num:03d}"
            # Check if this ID already exists
            existing = supabase.table(table_name).select("id").eq("id", proposed_id).limit(1).execute()
            if not existing.data:
                return proposed_id
        except Exception:
            pass

    # Unique random fallback maintaining contract prefix
    short_uuid = uuid.uuid4().hex[:6]
    return f"{prefix}_{short_uuid}"


def generate_report_id() -> str:
    return generate_semantic_id("rpt", "reports")


def generate_incident_id() -> str:
    return generate_semantic_id("inc", "incidents")


def generate_simulation_id() -> str:
    return generate_semantic_id("sim", "simulations")


def generate_conflict_id() -> str:
    return generate_semantic_id("cfl")


def generate_edge_id() -> str:
    return generate_semantic_id("edge", "report_relationships")
