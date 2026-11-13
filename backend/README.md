# CrisisLens – Backend, Database & API Integration
**Member 2: Backend, Database, API Development & Integration Lead**

CrisisLens is a **Trust-Aware Emergency Intelligence System** built to convert noisy, duplicated, forwarded, and conflicting disaster reports into explainable, evidence-backed intelligence for emergency decision-makers.

This repository directory (`backend/`) contains the complete Python FastAPI backend, Supabase PostgreSQL database schemas, and integration connectors strictly adhering to **CrisisLens API Contract v1.0**.

---

## 1. System Architecture

```text
backend/
├── app/
│   ├── main.py                     # FastAPI entry point, CORS, contract error handlers
│   ├── core/
│   │   ├── config.py               # Pydantic BaseSettings, environment variable loader
│   │   ├── exceptions.py           # Contract-compliant non-2xx error formatters
│   │   └── security.py             # Security utilities
│   ├── database/
│   │   ├── supabase_client.py      # Authenticated Supabase PostgreSQL client singleton
│   │   └── schema.sql              # Clean 7-table schema with RLS and indexes
│   ├── schemas/                    # Pydantic v2 validation models
│   │   ├── common.py               # Location, Source, Freshness, Score schemas
│   │   ├── report.py               # ReportCreate, ReportResponse, ReportListResponse
│   │   ├── incident.py             # IncidentResponse, IncidentListResponse, Timeline
│   │   ├── analysis.py             # AnalysisObject, DuplicateInfo, SourceVerification
│   │   ├── evidence.py             # EvidenceGraphResponse, GraphNode, GraphEdge
│   │   ├── priority.py             # PriorityResponse, PriorityItem, HumanDecision
│   │   ├── simulation.py           # SimulationRequest, SimulationResponse
│   │   └── verification.py         # VerificationRequest, VerificationResponse
│   ├── routers/                    # Modular API route controllers
│   │   ├── reports.py              # POST /reports, GET /reports, GET /reports/{id}
│   │   ├── incidents.py            # GET /incidents, GET /incidents/{id}
│   │   ├── analysis.py             # POST /analyze/{report_id}
│   │   ├── priority.py             # GET /incidents/priority
│   │   ├── evidence.py             # GET /incidents/{id}/evidence-graph
│   │   ├── simulations.py          # POST /simulate
│   │   └── verification.py         # PATCH /reports/{id}/verify
│   ├── services/                   # Business logic & data orchestration
│   │   ├── report_service.py       # Report creation, filtering & retrieval
│   │   ├── incident_service.py     # Incident aggregation & chronological timeline
│   │   ├── analysis_service.py     # AI analysis persistence & edge updates
│   │   ├── priority_service.py     # Dynamic ranking & separate score maintenance
│   │   ├── evidence_service.py     # Evidence graph nodes and directed edges
│   │   ├── simulation_service.py   # Isolated what-if scenario simulations
│   │   ├── verification_service.py # Human reviewer audit log & status mapping
│   │   └── ai_client.py            # Async HTTP client to Member 3 with fallback
│   └── utils/
│       ├── id_generator.py         # Semantic IDs: rpt_xxx, inc_xxx, sim_xxx, cfl_xxx
│       └── datetime_utils.py       # ISO 8601 UTC formatter & freshness calculator
├── tests/                          # 28 Automated test cases (100% passing)
│   ├── test_health.py
│   ├── test_reports.py
│   ├── test_incidents.py
│   ├── test_analysis.py
│   ├── test_priority.py
│   ├── test_evidence.py
│   ├── test_simulations.py
│   ├── test_verification.py
│   └── test_ai_integration.py
├── seed_data.py                    # Seeds baseline incidents into Supabase
├── test_database.py                # Database connectivity & table diagnostic
├── .env.example                    # Template environment variables
├── .gitignore                      # Prevents committing secrets or venv
└── requirements.txt                # Pinned production dependencies
```

---

## 2. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.10+ | Core backend runtime |
| **Framework** | FastAPI | High-performance async REST API framework |
| **Server** | Uvicorn | ASGI production-grade web server |
| **Validation** | Pydantic v2 & Pydantic-Settings | Strict request/response validation |
| **Database** | Supabase PostgreSQL | Managed relational database with Row Level Security |
| **Database Client**| Supabase Python SDK | Privileged backend access via Service Role Key |
| **HTTP Client** | HTTPX | Asynchronous communication with Member 3's AI Engine |
| **Testing** | Pytest & Pytest-Asyncio | Automated contract and integration test suite |

---

## 3. Database Design (7 Tables)

All tables use semantic text primary keys matching API Contract v1.0 directly (`rpt_001`, `inc_001`, `sim_001`, `cfl_001`), eliminating UUID mapping friction:

1. **`incidents`**: Aggregated disaster events (`title`, `type`, `severity`, `status`, `timeline` JSONB, `report_count`, `independent_source_count`).
2. **`reports`**: Raw incoming reports (`text`, `source_type`, `source_name`, `lat`, `lng`, `location_label`, `reported_at`, `received_at`, `status`, `forwarded_from`).
3. **`report_relationships`**: Graph edges between reports (`source_report_id` [later] $\to$ `target_report_id` [earlier], `type`, `confidence`, `label`).
4. **`analysis_results`**: AI intelligence per report (`urgency_score`, `evidence_confidence_score`, `verification_priority_score`, `raw_analysis` JSONB).
5. **`priority_scores`**: Incident ranking maintaining the three separate scores ($0$–$100$) and human decision tracking (`requires_human_decision: true`).
6. **`verifications`**: Immutable audit log of human verification decisions (`action`, `note`, `verified_by`, `verified_at`).
7. **`simulations`**: What-if scenario results (`inputs`, `results`, `is_simulation: true`) strictly isolated from live incident data.

---

## 4. API Endpoints Reference (CrisisLens Contract v1.0)

Base URL: `http://127.0.0.1:8000`

| # | Endpoint | Method | Description |
|---|---|---|---|
| 1 | `/health` | GET | Health check diagnostic (`status: "healthy"`) |
| 2 | `/reports` | POST | Submit new report (`status: "pending_analysis"`, `analysis: null`) |
| 3 | `/reports` | GET | List reports with filters (`q`, `status`, `freshness`, `sort=newest\|verification_priority`) |
| 4 | `/reports/{id}` | GET | Retrieve report with analysis & verification data |
| 5 | `/incidents` | GET | List aggregated incidents with chronological timeline |
| 6 | `/incidents/{id}` | GET | Retrieve incident details and associated report IDs |
| 7 | `/analyze/{report_id}` | POST | Run AI engine analysis, store results, update report status to `analyzed` |
| 8 | `/incidents/priority` | GET | Ranked priority queue (`sort=urgency` or `sort=verification`) |
| 9 | `/incidents/{id}/evidence-graph` | GET | Graph data (Node ID == Report ID; directed edges) |
| 10 | `/simulate` | POST | What-if disaster simulation (`is_simulation: true`) |
| 11 | `/reports/{id}/verify` | PATCH | Human verification (`confirm`, `reject`, `request_more_info`) |

---

## 5. Local Setup & Running Instructions

### 5.1 Navigate to Backend Directory
```powershell
cd C:\Users\dell\Desktop\crisis-lens\backend
```

### 5.2 Activate Virtual Environment
```powershell
.\venv\Scripts\Activate.ps1
```

### 5.3 Install Dependencies
```powershell
pip install -r requirements.txt
```

### 5.4 Configure Environment Variables (`.env`)
Create `.env` based on `.env.example`:
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
AI_ENGINE_URL=http://127.0.0.1:8001
APP_ENV=development
API_PORT=8000
API_HOST=127.0.0.1
```

### 5.5 Verify Database Connectivity
```powershell
python test_database.py
```

### 5.6 Seed Initial Baseline Incidents
```powershell
python seed_data.py
```

### 5.7 Start the Backend Server
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Open interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

## 6. Running Automated Tests

Run the complete 28-test verification suite:
```powershell
pytest tests
```
*Result*: 28 passed across all endpoint and integration suites in under 17 seconds.

---

## 7. Team Integration Handover

### For Member 1 (Frontend):
- **Base URL**: `http://127.0.0.1:8000`
- **CORS**: Configured for `http://localhost:5173` and `http://127.0.0.1:5173`.
- **Live Health Check**: Your top navigation toggle (`checkConnection`) calls `GET /incidents`.
- **Error Format**: All errors return `{ "error": { "code": "...", "message": "...", "details": ... } }`.

### For Member 3 (AI/ML):
- **Service Endpoint**: Backend calls `{AI_ENGINE_URL}/analyze` with `{"report": {...}, "context_reports": [...]}`.
- **Contract Output**: Return the exact JSON structure defined in `AnalysisObject` (`duplicate`, `source_verification`, `freshness`, `conflicts`, `scores`, `recommendation`).
- **Resilience**: The backend incorporates a built-in fallback engine, so frontend and backend development continue uninterrupted even during AI model training.
