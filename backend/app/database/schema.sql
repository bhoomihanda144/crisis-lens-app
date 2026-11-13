-- =============================================================================
-- CrisisLens – Trust-Aware Emergency Intelligence System
-- Database Schema for Supabase PostgreSQL
-- Version: 1.0 (Strictly aligned with CrisisLens API Contract v1.0)
-- 
-- Key Design Decisions:
-- 1. Direct Semantic Primary Keys: TEXT IDs (e.g. inc_001, rpt_001) matching the public API contract directly.
-- 2. Three Separate Scores: Urgency, Confidence, Verification Priority are stored in separate integer columns (0-100).
-- 3. Simulation Isolation: The simulations table has zero foreign keys to actual incident data.
-- 4. Audit Trail: Every human verification action is appended to the verifications table.
-- 5. No destructive commands: Does NOT use DROP TABLE or TRUNCATE.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- TABLE 1: incidents
-- Real-world emergency events grouped from correlated reports.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('flood', 'fire', 'earthquake', 'landslide', 'structural', 'medical', 'other')),
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    location_label TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    status TEXT NOT NULL CHECK (status IN ('active', 'monitoring', 'resolved')),
    report_count INTEGER NOT NULL DEFAULT 0 CHECK (report_count >= 0),
    independent_source_count INTEGER NOT NULL DEFAULT 0 CHECK (independent_source_count >= 0),
    first_reported_at TIMESTAMPTZ NOT NULL,
    last_updated_at TIMESTAMPTZ NOT NULL,
    timeline JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- TABLE 2: reports
-- Raw emergency reports submitted from citizens, news, sensors, officials, etc.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('citizen', 'social_media', 'news', 'official', 'sensor', 'responder')),
    source_name TEXT NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    location_label TEXT NOT NULL,
    reported_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending_analysis', 'analyzed', 'verified', 'rejected', 'needs_more_info')) DEFAULT 'pending_analysis',
    incident_id TEXT REFERENCES incidents(id) ON DELETE SET NULL,
    forwarded_from TEXT REFERENCES reports(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- TABLE 3: report_relationships
-- Edges connecting reports for the Evidence Relationship Graph.
-- Direct edge goes from derived/later report (source) to original/reference (target).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS report_relationships (
    id TEXT PRIMARY KEY,
    source_report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    target_report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('original', 'duplicate', 'forwarded', 'corroborating', 'conflicting')),
    confidence DOUBLE PRECISION NOT NULL DEFAULT 1.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
    label TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_no_self_relationship CHECK (source_report_id <> target_report_id)
);

-- -----------------------------------------------------------------------------
-- TABLE 4: analysis_results
-- AI-generated intelligence produced per report.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS analysis_results (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL UNIQUE REFERENCES reports(id) ON DELETE CASCADE,
    incident_id TEXT REFERENCES incidents(id) ON DELETE SET NULL,
    analyzed_at TIMESTAMPTZ NOT NULL,
    engine_version TEXT NOT NULL,
    urgency_score INTEGER NOT NULL CHECK (urgency_score >= 0 AND urgency_score <= 100),
    evidence_confidence_score INTEGER NOT NULL CHECK (evidence_confidence_score >= 0 AND evidence_confidence_score <= 100),
    verification_priority_score INTEGER NOT NULL CHECK (verification_priority_score >= 0 AND verification_priority_score <= 100),
    raw_analysis JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- TABLE 5: priority_scores
-- Incident-level priority rankings maintaining the three separate scores.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS priority_scores (
    id TEXT PRIMARY KEY,
    incident_id TEXT NOT NULL UNIQUE REFERENCES incidents(id) ON DELETE CASCADE,
    urgency_score INTEGER NOT NULL CHECK (urgency_score >= 0 AND urgency_score <= 100),
    urgency_level TEXT NOT NULL CHECK (urgency_level IN ('low', 'medium', 'high', 'critical')),
    urgency_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_confidence_score INTEGER NOT NULL CHECK (evidence_confidence_score >= 0 AND evidence_confidence_score <= 100),
    evidence_confidence_level TEXT NOT NULL CHECK (evidence_confidence_level IN ('low', 'medium', 'high')),
    evidence_confidence_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    verification_priority_score INTEGER NOT NULL CHECK (verification_priority_score >= 0 AND verification_priority_score <= 100),
    verification_priority_level TEXT NOT NULL CHECK (verification_priority_level IN ('low', 'medium', 'high')),
    verification_priority_reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanation JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommended_next_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    requires_human_decision BOOLEAN NOT NULL DEFAULT TRUE,
    human_decision_status TEXT NOT NULL DEFAULT 'not_decided',
    decided_by TEXT,
    decided_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- TABLE 6: verifications
-- Audit trail of human decision-maker verification actions.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS verifications (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    action TEXT NOT NULL CHECK (action IN ('confirm', 'reject', 'request_more_info')),
    note TEXT,
    verified_by TEXT,
    verified_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- TABLE 7: simulations
-- What-if emergency scenarios. Strictly isolated from live incidents.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS simulations (
    id TEXT PRIMARY KEY,
    scenario_name TEXT NOT NULL,
    is_simulation BOOLEAN NOT NULL DEFAULT TRUE,
    generated_at TIMESTAMPTZ NOT NULL,
    inputs JSONB NOT NULL,
    results JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- INDEXES FOR PERFORMANCE
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_reports_incident_id ON reports(incident_id);
CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
CREATE INDEX IF NOT EXISTS idx_reports_reported_at ON reports(reported_at DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity);
CREATE INDEX IF NOT EXISTS idx_report_rel_source ON report_relationships(source_report_id);
CREATE INDEX IF NOT EXISTS idx_report_rel_target ON report_relationships(target_report_id);
CREATE INDEX IF NOT EXISTS idx_analysis_report_id ON analysis_results(report_id);
CREATE INDEX IF NOT EXISTS idx_priority_incident_id ON priority_scores(incident_id);
CREATE INDEX IF NOT EXISTS idx_priority_urgency ON priority_scores(urgency_score DESC);
CREATE INDEX IF NOT EXISTS idx_priority_verification ON priority_scores(verification_priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_verifications_report_id ON verifications(report_id);

-- -----------------------------------------------------------------------------
-- ROW LEVEL SECURITY (RLS) POLICIES
-- Ensures database is secured against unauthenticated public access.
-- The backend uses the SUPABASE_SERVICE_ROLE_KEY to perform privileged operations.
-- -----------------------------------------------------------------------------
ALTER TABLE incidents ENABLE ROW LEVEL SECURITY;
ALTER TABLE reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE priority_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE simulations ENABLE ROW LEVEL SECURITY;

-- Service Role Key bypasses RLS automatically in Supabase.
-- Explicit service-role policies ensure privileged access is clearly recognized.
DROP POLICY IF EXISTS "Service role full access on incidents" ON incidents;
CREATE POLICY "Service role full access on incidents" ON incidents FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service role full access on reports" ON reports;
CREATE POLICY "Service role full access on reports" ON reports FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service role full access on report_relationships" ON report_relationships;
CREATE POLICY "Service role full access on report_relationships" ON report_relationships FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service role full access on analysis_results" ON analysis_results;
CREATE POLICY "Service role full access on analysis_results" ON analysis_results FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service role full access on priority_scores" ON priority_scores;
CREATE POLICY "Service role full access on priority_scores" ON priority_scores FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service role full access on verifications" ON verifications;
CREATE POLICY "Service role full access on verifications" ON verifications FOR ALL USING (auth.role() = 'service_role');

DROP POLICY IF EXISTS "Service role full access on simulations" ON simulations;
CREATE POLICY "Service role full access on simulations" ON simulations FOR ALL USING (auth.role() = 'service_role');
