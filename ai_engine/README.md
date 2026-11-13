# CrisisLens AI Engine

Trust-Aware Emergency Intelligence System
**Member 3 – AI/ML Developer Component**

## Architecture Overview

The CrisisLens AI Engine is designed with a **dual invocation architecture**:
1. **Reusable Python Library:** Direct importable modules for Member 2's backend (`from ai_engine.modules import ReportAnalyzer`).
2. **Thin FastAPI Microservice:** An independent HTTP service running on `http://127.0.0.1:8001` (`POST /analyze`, `GET /health`) for decoupled testing, development, and standalone container deployment.

All schemas strictly enforce `docs/api-contract.md` v1.0.

## Directory Structure

```text
ai_engine/
├── __init__.py           # Package version and export definitions
├── README.md             # This documentation
├── requirements.txt      # Engine dependency specifications
├── main.py               # FastAPI application entrypoint (Port 8001)
├── api/
│   ├── __init__.py
│   └── routes.py         # Route handlers (/health, /analyze, etc.)
├── schemas/              # Pydantic v2 schemas reflecting API Contract v1.0
│   ├── __init__.py
│   ├── enums.py          # Fixed contract enums
│   ├── common.py         # Location, 3-score models, error response
│   ├── analysis.py       # Analysis, duplicate, source, freshness, conflict schemas
│   ├── report.py         # Report, ReportSource, Verification schemas
│   ├── incident.py       # Incident, TimelineEntry, Priority schemas
│   ├── graph.py          # EvidenceNode, EvidenceEdge, EvidenceGraphResponse
│   ├── simulation.py     # SimulationRequest, ResourceDemand, SimulationResponse
│   └── internal.py       # Internal exchange schemas (ReportInput, AnalyzeRequest)
├── modules/              # Deterministic, explainable intelligence modules
│   ├── __init__.py
│   ├── freshness.py      # FreshnessAnalyzer (recent <=60m, aging 61-240m, stale >240m)
│   ├── duplicate.py      # DuplicateDetector (disciplined multi-modal matching)
│   ├── source.py         # SourceIndependenceAnalyzer (provenance & non-corroboration)
│   ├── graph.py          # EvidenceGraphBuilder (DAG topology, relationships & NetworkX validation)
│   ├── priority.py       # IncidentPriorityRanker (3-score multi-dimensional ranking & explainability)
│   ├── simulation.py     # DisasterSimulationEngine (what-if resource demand, delay & priority modeling)
│   └── analyzer.py       # ReportAnalyzer (multi-dimensional scores & orchestrator)
└── tests/
    ├── __init__.py
    ├── test_health.py    # Microservice health check test suite
    ├── test_schemas.py   # Schema validation and contract compliance tests
    ├── test_freshness.py # Freshness decay boundary tests
    ├── test_duplicate.py # Duplicate false-positive regression tests
    ├── test_source.py    # Source independence & original ID regression tests
    ├── test_analyze_api.py # POST /analyze & backend AnalysisObject compatibility tests
    ├── test_graph.py     # Evidence graph generation & NetworkX validation tests
    ├── test_priority.py  # Priority ranking & deterministic sorting tests
    └── test_simulation.py # What-if disaster simulation tests
```

## Getting Started

### 1. Environment Setup
Activate the Python virtual environment:
```powershell
.\.venv\Scripts\Activate.ps1
```

Install requirements:
```powershell
pip install -r ai_engine/requirements.txt
```

### 2. Running Tests
Run all unit, contract, and intelligence regression tests:
```powershell
python -m pytest ai_engine/tests -v
```

### 3. Launching the AI Microservice
Start the development server on `http://127.0.0.1:8001`:
```powershell
uvicorn ai_engine.main:app --host 127.0.0.1 --port 8001 --reload
```
Interactive API documentation will be available at:
- Swagger UI: `http://127.0.0.1:8001/docs`
- ReDoc: `http://127.0.0.1:8001/redoc`
- Health check: `http://127.0.0.1:8001/health`
- Analysis endpoint: `POST http://127.0.0.1:8001/analyze`
- Graph endpoint (RESTful): `POST http://127.0.0.1:8001/incidents/{incident_id}/evidence-graph`
- Graph endpoint (RPC): `POST http://127.0.0.1:8001/graph/generate`
- Priority endpoint (RESTful): `POST http://127.0.0.1:8001/incidents/priority`
- Priority endpoint (RPC): `POST http://127.0.0.1:8001/priority/rank`
- Simulation endpoint (RESTful): `POST http://127.0.0.1:8001/simulate`
- Simulation endpoint (RPC): `POST http://127.0.0.1:8001/simulation/run`

## Core Intelligence Guardrails

### 1. Disciplined Duplicate Detection
- **No Location-Only Matches:** Same location alone NEVER establishes a duplicate.
- **No Time-Only Matches:** Temporal proximity alone NEVER establishes a duplicate.
- **No Generic-Only Matches:** Generic emergency words ("water", "flood", "building", "road", "incident") alone are NEVER sufficient evidence.
- **Mandatory Content Overlap:** Two reports must share distinctive, informative tokens before location or temporal proximity can strengthen a duplicate match.
- **Explicit Forwarding:** Explicit `forwarded_from` links or forwarding language establish high-confidence duplicate linkage with reason `"Direct forwarded marker or reference"`.

### 2. Source Independence & Provenance Limitations
- **Current Schema Boundary:** Under CrisisLens API Contract v1.0, incoming reports provide `source.type` and `source.name`, but lack cryptographic authentication, origin IP, or verifiable identity credentials.
- **Strict Adherence (No Invented Provenance):** The AI engine NEVER assumes that a citizen, news, official, responder, or sensor report is independent solely because of its `source_type`.
- **Default to Unknown:** If explicit, verifiable provenance is absent, `independence` is strictly set to `"unknown"`.
- **Forwarded Detection:** Reports containing forwarding markers or `forwarded_from` references are classified as `independence = "forwarded"`.
- **Corroboration Integrity:** Forwarded reports NEVER increase independent corroboration counts. Independent corroboration (`corroboration_status = "corroborated"`) strictly requires defensible evidence that multiple reports originated from verified independent sources.

### 3. Original Report Identification
- `original_report_id` is ONLY populated when an explicit forwarding reference (`forwarded_from` or explicit parent reference in text) identifies the source.
- Similar non-forwarded reports are NEVER assumed to be the original. In the absence of an explicit forwarding reference, `original_report_id` is set to `null` (`None`).

### 4. Contract Guarantees
- **Separation of Scores:** Urgency (4 levels), Evidence Confidence (3 levels), and Verification Priority (3 levels) are strictly separate. No single combined score exists.
- **Fixed Freshness Decay:**
  - `recent`: $\le 60$ minutes
  - `aging`: $61$ to $240$ minutes
  - `stale`: $> 240$ minutes
- **Human Decision Mandate:** `requires_human_decision` is invariant (`true`).
- **Graph Direction:** Edges originate from the later/derived report (`source`) and point to the earlier/reference report (`target`).

### 5. Evidence Graph Generation (Stage 4)
- **Structural vs. Provenance Semantics for `original`:** The `role="original"` represents the **structural root of the directed evidence graph**, NOT proof of verified real-world provenance.
- **Preservation of Uncertainty:** When a root node's provenance is unestablished (`provenance="unknown"` or unverified), its display label is explicitly formatted as `Citizen (Unverified): <Location>` to prevent responders and frontend users from interpreting an unverified rumor as verified ground truth.
- **NetworkX Topology Validation:** Validates the evidence graph as a strict Directed Acyclic Graph (DAG):
  - Zero self-loops permitted (`source != target`).
  - Invariant edge direction: `source` (later/derived report) $\rightarrow$ `target` (earlier/reference report).
  - Cycle detection: Any cycle detected via `nx.simple_cycles()` raises an explicit `GraphValidationError` rather than silently dropping or modifying evidence.
- **Zero Invented Relationships:** Reports that describe different emergency events or unrelated locations remain completely disconnected nodes. Relationships are only generated for explicit forwarding, verified duplicates ($\ge 0.55$), defensible corroboration, or explicitly supplied conflict evidence.

### 6. Incident Priority Ranking (Stage 5)
- **Three Independent Dimensions:** Urgency (life safety, vulnerable groups, progression), Evidence Confidence (verified independent count, official telemetry, conflict penalties), and Verification Priority (urgency/confidence gap, contradictions).
- **No Blended Scores:** Ranking mode (`sort="urgency"` or `sort="verification"`) determines sorting order only. Scores remain completely separate.
- **Threat Preservation:** Severe active threats in constituent reports are never diluted by simple averaging.
- **Deterministic Tie-Breaking:**
  - When `sort="urgency"`: Primary sort by `urgency.score` descending, secondary by `verification_priority.score` descending, tertiary by `incident_id` ascending.
  - When `sort="verification"`: Primary sort by `verification_priority.score` descending, secondary by `urgency.score` descending, tertiary by `incident_id` ascending.
- **Human Decision Authority:** Invariant `requires_human_decision=True` and `human_decision.status="not_decided"`. The AI Engine never executes autonomous dispatch.

### 7. What-If Disaster Simulation Engine (Stage 6)
- **Baseline Resource Demand Formulas:**
  - Demanded rescue teams: $\max(2, \lfloor (\text{affected\_population} / 1500) \times (\text{disaster\_severity} / 2.5) \rfloor)$
  - Demanded ambulances: $\max(2, \lfloor (\text{affected\_population} / 2000) \times (\text{disaster\_severity} / 2.0) \rfloor)$
- **Resource Shortages:**
  - $\text{shortfall} = \max(0, \text{required} - \text{available})$. Only positive shortfalls are included in the results.
- **Compound Response Delay Formula:**
  - $\text{delay\_minutes} = (\text{blocked\_roads} \times 5) + (\text{rescue\_team\_shortfall} \times 2)$
- **Assumptions & Model Boundaries:**
  - Baseline minimum of 2 rescue teams and 2 ambulances required for any declared disaster zone regardless of population.
  - Road blockage penalty assumes an average 5-minute detour/rerouting delay per impassable arterial route.
  - Team deficit penalty assumes an average 2-minute dispatch queuing backlog per missing rescue team.
  - The public simulation request specifies the count of blocked roads, not their geographic locations. Incident-specific access obstruction is only applied when explicit access-impact context (`blocked_access_incident_ids`) is provided by the caller.
  - When incident context is omitted or empty, `priority_changes` is strictly empty. Synthetic or invented incident records are never generated.
- **Strict Isolation & Simulation Invariants:**
  - Invariant `is_simulation: True` on all outputs to guarantee simulated projections are clearly distinguished from live disaster records.
  - Projections are advisory planning estimates and do not execute automated dispatch or mutate live incident priority scores.

## Backend Integration Guide for Member 2

To generate evidence relationship graphs, Member 2's backend service (`backend/app/services/evidence_service.py` or `ai_client.py`) can invoke the AI Engine microservice:

### Endpoint
- **URL:** `POST http://127.0.0.1:8001/incidents/{incident_id}/evidence-graph` (or `POST http://127.0.0.1:8001/graph/generate`)
- **Headers:** `Content-Type: application/json`

### Request Payload (`GenerateGraphRequest`)
```json
{
  "incident_id": "inc_001",
  "reports": [
    {
      "id": "rpt_001",
      "text": "Water entering basement apartments on Lake Road.",
      "source_type": "citizen",
      "source_name": "Resident A",
      "location_label": "Lake Road, Bellandur",
      "lat": 12.9304,
      "lng": 77.6784,
      "reported_at": "2026-11-12T13:00:00Z",
      "forwarded_from": null,
      "provenance": "verified_original"
    },
    {
      "id": "rpt_002",
      "text": "Water entering basement apartments on Lake Road.",
      "source_type": "citizen",
      "source_name": "Resident B",
      "location_label": "Lake Road, Bellandur",
      "lat": 12.9304,
      "lng": 77.6784,
      "reported_at": "2026-11-12T13:15:00Z",
      "forwarded_from": "rpt_001"
    }
  ],
  "conflicts": []
}
```

### Response Payload (`EvidenceGraphResponse`)
```json
{
  "incident_id": "inc_001",
  "nodes": [
    {
      "id": "rpt_001",
      "report_id": "rpt_001",
      "label": "Citizen: Lake Road, Bellandur",
      "role": "original",
      "source_type": "citizen",
      "source_name": "Resident A",
      "timestamp": "2026-11-12T13:00:00Z",
      "excerpt": "Water entering basement apartments on Lake Road.",
      "freshness_status": "recent"
    },
    {
      "id": "rpt_002",
      "report_id": "rpt_002",
      "label": "Citizen (Forwarded): Lake Road, Bellandur",
      "role": "forwarded",
      "source_type": "citizen",
      "source_name": "Resident B",
      "timestamp": "2026-11-12T13:15:00Z",
      "excerpt": "Water entering basement apartments on Lake Road.",
      "freshness_status": "recent"
    }
  ],
  "edges": [
    {
      "id": "edge_rpt_002_rpt_001_forwarded",
      "source": "rpt_002",
      "target": "rpt_001",
      "type": "forwarded",
      "label": "Forwarded from rpt_001",
      "confidence": 1.0
    }
  ]
}
```

### Priority Ranking Engine Integration

To rank emergency rescue queues, Member 2's backend service invokes:

#### Endpoint
- **URL:** `POST http://127.0.0.1:8001/incidents/priority` (or `POST http://127.0.0.1:8001/priority/rank`)
- **Query Parameter (Optional override):** `?sort=urgency` or `?sort=verification`
- **Headers:** `Content-Type: application/json`

#### Request Payload (`PriorityRankRequest`)
```json
{
  "sort": "urgency",
  "incidents": [
    {
      "id": "inc_001",
      "title": "Flooding near Bellandur lake road",
      "type": "flood",
      "severity": "critical",
      "status": "active",
      "location": {
        "lat": 12.9304,
        "lng": 77.6784,
        "label": "Lake Road, Bellandur"
      },
      "report_count": 2,
      "independent_source_count": 2,
      "first_reported_at": "2026-11-12T13:50:00Z",
      "last_updated_at": "2026-11-12T14:25:00Z",
      "timeline": [],
      "reports": [
        {
          "id": "rpt_001",
          "text": "Elderly resident trapped on ground floor as water level is rising rapidly.",
          "source_type": "citizen",
          "source_name": "Resident A",
          "location_label": "Lake Road, Bellandur",
          "lat": 12.9304,
          "lng": 77.6784,
          "reported_at": "2026-11-12T13:50:00Z",
          "provenance": "firsthand"
        },
        {
          "id": "rpt_002",
          "text": "Emergency responder on scene confirms 1.2m water level on main road.",
          "source_type": "responder",
          "source_name": "Officer Patil",
          "location_label": "Lake Road, Bellandur",
          "lat": 12.9304,
          "lng": 77.6784,
          "reported_at": "2026-11-12T14:10:00Z",
          "provenance": "verified"
        }
      ],
      "conflicts": []
    }
  ]
}
```

#### Response Payload (`PriorityResponse`)
```json
{
  "sort": "urgency",
  "items": [
    {
      "rank": 1,
      "incident_id": "inc_001",
      "title": "Flooding near Bellandur lake road",
      "location": {
        "lat": 12.9304,
        "lng": 77.6784,
        "label": "Lake Road, Bellandur"
      },
      "urgency": {
        "score": 100,
        "level": "critical",
        "reasons": [
          "Incident severity evaluated as Critical",
          "Potential threat to human life or reported trapped individuals",
          "Vulnerable population mentioned in field reports",
          "Active progressing environmental hazard reported"
        ]
      },
      "evidence_confidence": {
        "score": 85,
        "level": "high",
        "reasons": [
          "Two independent sources corroborate incident",
          "Confirmed by verified emergency responder or automated sensor telemetry"
        ]
      },
      "verification_priority": {
        "score": 5,
        "level": "low",
        "reasons": [
          "Well corroborated by multiple reliable sources; lower verification urgency"
        ]
      },
      "explanation": [
        "Active Flood incident at Lake Road, Bellandur",
        "Status: Active (Severity: Critical)",
        "Urgency driver: Incident severity evaluated as Critical",
        "Evidence is well-corroborated by independent field accounts"
      ],
      "recommended_next_steps": [
        "Recommend alerting duty officer for immediate tactical dispatch review",
        "Advise staging emergency rescue and medical standby units for responder review"
      ],
      "requires_human_decision": true,
      "human_decision": {
        "status": "not_decided",
        "decided_by": null,
        "decided_at": null
      }
    }
  ]
}
```

### Disaster Simulation Engine Integration

To simulate what-if emergency scenarios and evaluate resource bottlenecks, Member 2's backend service invokes:

#### Endpoints
- **Public RESTful Endpoint:** `POST http://127.0.0.1:8001/simulate` (Accepts `SimulationRequest`)
- **Internal RPC Endpoint:** `POST http://127.0.0.1:8001/simulation/run` (Accepts `SimulationScenarioRequest` with optional active incident context)
- **Headers:** `Content-Type: application/json`

#### Public Request Payload (`SimulationRequest`)
```json
{
  "scenario_name": "Heavy rain, 3 roads blocked",
  "affected_population": 12000,
  "disaster_severity": 4,
  "rescue_teams": 6,
  "blocked_roads": 3,
  "available_ambulances": 5
}
```

#### Response Payload (`SimulationResponse`)
```json
{
  "scenario_id": "sim_4949bdc5",
  "is_simulation": true,
  "generated_at": "2026-11-12T14:45:00Z",
  "inputs": {
    "scenario_name": "Heavy rain, 3 roads blocked",
    "affected_population": 12000,
    "disaster_severity": 4,
    "rescue_teams": 6,
    "blocked_roads": 3,
    "available_ambulances": 5
  },
  "results": {
    "resource_demand": {
      "rescue_teams": 12,
      "ambulances": 12
    },
    "shortages": [
      {
        "resource": "rescue_teams",
        "required": 12,
        "available": 6,
        "shortfall": 6
      },
      {
        "resource": "ambulances",
        "required": 12,
        "available": 5,
        "shortfall": 7
      }
    ],
    "estimated_response_delay_minutes": 27,
    "priority_changes": [],
    "summary": "Rescue teams are short by 6, ambulances are short by 7 under this scenario. Estimated response delay: 27 minutes. Note: Projections are hypothetical planning estimates for responder readiness and do not constitute automated dispatch actions."
  }
}
```

#### Internal RPC Request with Incident Re-ranking (`SimulationScenarioRequest`)
When Member 2 passes active incidents and explicit road blockage information to `POST /simulation/run`:
```json
{
  "scenario_name": "Heavy rain, 3 roads blocked",
  "affected_population": 12000,
  "disaster_severity": 4,
  "rescue_teams": 6,
  "blocked_roads": 3,
  "available_ambulances": 10,
  "incidents": [
    {
      "id": "inc_001",
      "title": "Active flood at Lake Road",
      "type": "flood",
      "severity": "critical",
      "status": "active",
      "location_label": "Lake Road",
      "independent_source_count": 3
    },
    {
      "id": "inc_002",
      "title": "Reported structural collapse, Koramangala",
      "type": "structural",
      "severity": "high",
      "status": "active",
      "location_label": "Koramangala",
      "independent_source_count": 2
    }
  ],
  "blocked_access_incident_ids": ["inc_002"]
}
```
The response dynamically calculates hypothetical queue changes without touching live incident database state:
```json
"priority_changes": [
  {
    "incident_id": "inc_002",
    "title": "Reported structural collapse, Koramangala",
    "baseline_rank": 2,
    "scenario_rank": 1,
    "reason": "Access roads blocked, fewer teams available"
  },
  {
    "incident_id": "inc_001",
    "title": "Active flood at Lake Road",
    "baseline_rank": 1,
    "scenario_rank": 2,
    "reason": "Operational constraints shifted queue position from #1 to #2"
  }
]
```
