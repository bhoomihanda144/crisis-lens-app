# CrisisLens API Contract v1.0

Status: DRAFT until all three members approve it in writing (a GitHub comment is enough).

This file is the single source of truth for every API request and response.
Nobody adds, renames or removes a field without a Pull Request that changes this file and is approved by all three members.

## 1. Who owns what

| Member | Owns | Must follow this contract by |
|---|---|---|
| Member 1 (Frontend) | React app. Only reads the fields in this file. | Never using a field that is not listed here |
| Member 2 (Backend) | FastAPI routes, Supabase storage, validation, CORS, auth | Returning exactly these shapes |
| Member 3 (AI/ML) | The `analysis` object and graph and simulation logic | Producing exactly the `analysis`, graph and simulation shapes |

Data flow: React → FastAPI → Supabase → AI engine → FastAPI → Supabase → React.
The frontend never talks to Supabase and never holds Supabase keys.

## 2. Conventions

- Base URL (local): `http://127.0.0.1:8000`
- All bodies are JSON. Field names are `snake_case`.
- All timestamps are ISO 8601 in UTC, for example `2026-11-11T14:30:00Z`.
- IDs are strings: `rpt_001` (report), `inc_001` (incident).
- Scores are integers from 0 to 100.
- Authentication (later): `Authorization: Bearer <token>`. Not required until Member 2 announces it.
- Human responders keep control. The AI only produces recommendations. This API has no dispatch endpoint in v1.

### Error format (all non-2xx responses)
```json
{ "error": { "code": "not_found", "message": "Report rpt_999 not found", "details": null } }
```
Codes: `validation_error` (422), `not_found` (404), `unauthorized` (401), `forbidden` (403), `server_error` (500).
Member 2: wrap FastAPI's default 422 `{"detail": [...]}` into this format.

### Allowed values (enums)

| Field | Values |
|---|---|
| `source.type` | `citizen`, `social_media`, `news`, `official`, `sensor`, `responder` |
| `report.status` | `pending_analysis`, `analyzed`, `verified`, `rejected`, `needs_more_info` |
| `freshness.status` | `recent` (age ≤ 60 min), `aging` (61–240 min), `stale` (> 240 min) |
| `incident.type` | `flood`, `fire`, `earthquake`, `landslide`, `structural`, `medical`, `other` |
| `incident.severity` | `low`, `medium`, `high`, `critical` |
| `incident.status` | `active`, `monitoring`, `resolved` |
| relationship `type` / node `role` | `original`, `duplicate`, `forwarded`, `corroborating`, `conflicting` |
| `independence` | `independent`, `forwarded`, `unknown` |
| `corroboration_status` | `corroborated`, `single_source`, `disputed` |
| score `level` (urgency) | `low`, `medium`, `high`, `critical` |
| score `level` (confidence, verification) | `low`, `medium`, `high` |
| `recommendation.type` | `verify_first`, `monitor`, `escalate_for_human_review` |
| verify `action` | `confirm`, `reject`, `request_more_info` |

Freshness thresholds are fixed here so the AI and the UI agree.

## 3. Shared objects

### Location
```json
{ "lat": 12.9304, "lng": 77.6784, "label": "Lake Road, Bellandur" }
```

### Analysis (produced by Member 3, stored and served by Member 2)
```json
{
  "analyzed_at": "2026-11-11T14:31:00Z",
  "engine_version": "0.1.0",
  "duplicate": {
    "is_duplicate": true,
    "matches": [
      { "report_id": "rpt_001", "similarity": 0.91, "reasons": ["Same location", "Similar wording", "Within 10 minutes"] }
    ]
  },
  "source_verification": {
    "independence": "independent",
    "original_report_id": "rpt_001",
    "related": [ { "report_id": "rpt_001", "relation": "duplicate" } ],
    "corroboration_status": "corroborated"
  },
  "freshness": { "status": "recent", "age_minutes": 18, "last_updated": "2026-11-11T14:13:00Z" },
  "conflicts": [
    {
      "id": "cfl_001",
      "topic": "Extent of damage",
      "report_ids": ["rpt_005", "rpt_006"],
      "statements": [
        { "report_id": "rpt_005", "text": "Building collapsed, people trapped" },
        { "report_id": "rpt_006", "text": "Only the compound wall fell, nobody trapped" }
      ],
      "detected_at": "2026-11-11T14:20:00Z"
    }
  ],
  "scores": {
    "urgency": { "score": 90, "level": "critical", "reasons": ["People reported trapped"] },
    "evidence_confidence": { "score": 80, "level": "high", "reasons": ["Two independent sources"] },
    "verification_priority": { "score": 25, "level": "low", "reasons": ["Already corroborated"] }
  },
  "recommendation": {
    "type": "monitor",
    "summary": "Evidence is strong. Pass to a human responder for a decision.",
    "next_steps": ["Notify duty officer", "Re-check in 30 minutes"],
    "requires_human_decision": true
  }
}
```
Rules:
- The three scores are separate on purpose. There is **no** combined score anywhere in this API.
- `requires_human_decision` is always `true`.
- `conflicts` is an empty list when there are none. `duplicate.matches` is an empty list when there are none.

### Report
```json
{
  "id": "rpt_002",
  "text": "Water entering houses on Lake Road...",
  "source": { "type": "citizen", "name": "Citizen reporter" },
  "location": { "lat": 12.9304, "lng": 77.6784, "label": "Lake Road, Bellandur" },
  "reported_at": "2026-11-11T14:13:00Z",
  "received_at": "2026-11-11T14:14:00Z",
  "status": "analyzed",
  "incident_id": "inc_001",
  "forwarded_from": null,
  "analysis": null,
  "verification": null
}
```
- `analysis` is `null` until analysis has run.
- `verification` is `null` until a human acts. Afterwards:
  `{ "action": "confirm", "note": "Called ward officer", "verified_by": "Duty Officer", "verified_at": "2026-11-11T14:40:00Z" }`

### Incident
```json
{
  "id": "inc_001",
  "title": "Flooding near Bellandur lake road",
  "type": "flood",
  "location": { "lat": 12.9304, "lng": 77.6784, "label": "Lake Road, Bellandur" },
  "severity": "critical",
  "status": "active",
  "report_ids": ["rpt_001", "rpt_002"],
  "report_count": 2,
  "independent_source_count": 2,
  "first_reported_at": "2026-11-11T13:50:00Z",
  "last_updated_at": "2026-11-11T14:25:00Z",
  "timeline": [
    {
      "timestamp": "2026-11-11T13:50:00Z",
      "severity": "medium",
      "status": "active",
      "report_count": 1,
      "affected_radius_m": 200,
      "summary": "First report of water entering homes"
    }
  ]
}
```
`timeline` powers the Incident Evolution Map. Entries are oldest first.

## 4. Endpoints

### 4.1 POST /reports (Member 2)
Submit a new report.
Request:
```json
{
  "text": "Water entering ground floor houses on Lake Road",
  "source": { "type": "citizen", "name": "Citizen reporter" },
  "location": { "lat": 12.9304, "lng": 77.6784, "label": "Lake Road, Bellandur" },
  "reported_at": "2026-11-11T14:13:00Z",
  "forwarded_from": null
}
```
- Required: `text`, `source`, `location`. Optional: `reported_at` (defaults to server time), `forwarded_from` (a report ID).
- Response `201`: a Report with `status: "pending_analysis"` and `analysis: null`.

### 4.2 GET /reports (Member 2)
Query parameters (all optional): `q` (text search), `status`, `freshness`, `incident_id`, `sort` (`newest` default, or `verification_priority`), `limit` (default 50), `offset` (default 0).
Response `200`:
```json
{ "items": [ /* Report objects */ ], "total": 8, "limit": 50, "offset": 0 }
```
`sort=verification_priority` returns the Verify-First Queue, highest verification priority first.

### 4.3 GET /reports/{id} (Member 2)
Response `200`: one Report, including `analysis` and `verification` when present. `404` if not found.

### 4.4 GET /incidents (Member 2)
Query parameters (optional): `status`, `severity`, `type`.
Response `200`:
```json
{ "items": [ /* Incident objects */ ], "total": 3 }
```

### 4.5 GET /incidents/{id} (Member 2)
Response `200`: one Incident. `404` if not found. (Added because the Incident Details page needs it.)

### 4.6 POST /analyze/{report_id} (Member 2 calls Member 3)
No request body. Runs the AI engine on the report, stores the result, and returns the updated Report.
Response `200`: a Report with `analysis` filled in and `status: "analyzed"`.

### 4.7 GET /incidents/priority (Member 2 serves, Member 3 computes)
Query parameter: `sort` = `urgency` (default) or `verification`. This chooses the ranking only. The scores stay separate either way.
Response `200`:
```json
{
  "sort": "urgency",
  "items": [
    {
      "rank": 1,
      "incident_id": "inc_001",
      "title": "Flooding near Bellandur lake road",
      "location": { "lat": 12.9304, "lng": 77.6784, "label": "Lake Road, Bellandur" },
      "urgency": { "score": 92, "level": "critical", "reasons": ["Elderly residents reported on upper floors"] },
      "evidence_confidence": { "score": 84, "level": "high", "reasons": ["Three independent sources"] },
      "verification_priority": { "score": 25, "level": "low", "reasons": ["Well corroborated"] },
      "explanation": ["Water level reported at 1.2 m", "Official source confirms"],
      "recommended_next_steps": ["Alert duty officer for dispatch review"],
      "requires_human_decision": true,
      "human_decision": { "status": "not_decided", "decided_by": null, "decided_at": null }
    }
  ]
}
```
`human_decision.status` is `not_decided` in v1. This is a recommendation list, not a dispatch order.

### 4.8 GET /incidents/{id}/evidence-graph (Member 3 produces, Member 2 serves)
Response `200`:
```json
{
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
      "freshness_status": "recent"
    }
  ],
  "edges": [
    {
      "id": "edge_001",
      "source": "rpt_002",
      "target": "rpt_001",
      "type": "duplicate",
      "label": "Duplicate (0.91)",
      "confidence": 0.91
    }
  ]
}
```
Node `id` equals the report ID. An edge goes from the later or derived report (`source`) to the earlier or reference report (`target`).

### 4.9 POST /simulate (Member 3 logic, Member 2 serves)
Request:
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
- `disaster_severity` is an integer from 1 to 5. The other fields are non-negative integers.
- Response `200`:
```json
{
  "scenario_id": "sim_001",
  "is_simulation": true,
  "generated_at": "2026-11-11T14:45:00Z",
  "inputs": { /* the request, echoed back */ },
  "results": {
    "resource_demand": { "rescue_teams": 10, "ambulances": 8 },
    "shortages": [
      { "resource": "rescue_teams", "required": 10, "available": 6, "shortfall": 4 }
    ],
    "estimated_response_delay_minutes": 15,
    "priority_changes": [
      {
        "incident_id": "inc_002",
        "title": "Reported structural collapse, Koramangala",
        "baseline_rank": 2,
        "scenario_rank": 1,
        "reason": "Access roads blocked, fewer teams available"
      }
    ],
    "summary": "Rescue teams are short by 4 under this scenario."
  }
}
```
Scenario comparison: the frontend calls this endpoint once per scenario and compares the results. It does not mix a simulation into real incident data.

### 4.10 PATCH /reports/{id}/verify (Member 2)
Request:
```json
{ "action": "confirm", "note": "Confirmed by ward officer", "verified_by": "Duty Officer" }
```
- Required: `action`. Optional: `note`, `verified_by`.
- Response `200`: the updated Report. Status changes: `confirm` → `verified`, `reject` → `rejected`, `request_more_info` → `needs_more_info`.

## 5. CORS (Member 2)
Allow these origins in FastAPI's `CORSMiddleware`: `http://localhost:5173`, `http://127.0.0.1:5173`, and later the deployed frontend URL. Allow methods `GET, POST, PATCH, OPTIONS` and headers `Content-Type, Authorization`.

## 6. Changing this contract
1. Open a Pull Request that edits only this file.
2. All three members approve it.
3. Bump the version number at the top.
4. Everyone updates their code to match.