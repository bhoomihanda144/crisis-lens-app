export const DATA_ORIGIN = 'SIMULATED'

const minsAgo = (m) => new Date(Date.now() - m * 60000).toISOString()
const freshnessOf = (m) => (m <= 60 ? 'recent' : m <= 240 ? 'aging' : 'stale')
const score = (value, level, reasons) => ({ score: value, level, reasons })

const LOC = {
  bellandur: { lat: 12.9304, lng: 77.6784, label: 'Lake Road, Bellandur' },
  koramangala: { lat: 12.9352, lng: 77.6245, label: '4th Block, Koramangala' },
  whitefield: { lat: 12.9698, lng: 77.75, label: 'Main Road, Whitefield' },
}

const cfl001 = {
  id: 'cfl_001',
  topic: 'Extent of damage',
  report_ids: ['rpt_005', 'rpt_006'],
  statements: [
    { report_id: 'rpt_005', text: 'Building collapsed, people trapped' },
    { report_id: 'rpt_006', text: 'Only the compound wall fell, nobody trapped' },
  ],
  detected_at: minsAgo(35),
}

function makeReport({
  id, text, sourceType, sourceName, location, ageMinutes, incidentId,
  forwardedFrom = null, duplicate, sourceVerification, conflicts = [],
  urgency, confidence, verification, recommendation,
}) {
  return {
    id,
    text,
    source: { type: sourceType, name: sourceName },
    location,
    reported_at: minsAgo(ageMinutes),
    received_at: minsAgo(ageMinutes - 1 > 0 ? ageMinutes - 1 : 0),
    status: 'analyzed',
    incident_id: incidentId,
    forwarded_from: forwardedFrom,
    analysis: {
      analyzed_at: minsAgo(2),
      engine_version: 'mock-0.1.0',
      duplicate,
      source_verification: sourceVerification,
      freshness: { status: freshnessOf(ageMinutes), age_minutes: ageMinutes, last_updated: minsAgo(ageMinutes) },
      conflicts,
      scores: { urgency, evidence_confidence: confidence, verification_priority: verification },
      recommendation: { ...recommendation, requires_human_decision: true },
    },
    verification: null,
  }
}

export const mockReports = [
  makeReport({
    id: 'rpt_001', text: 'Water entering ground floor houses on Lake Road. About 40 people, including elderly, on first floors.',
    sourceType: 'citizen', sourceName: 'Citizen reporter A', location: LOC.bellandur, ageMinutes: 25, incidentId: 'inc_001',
    duplicate: { is_duplicate: false, matches: [] },
    sourceVerification: { independence: 'independent', original_report_id: 'rpt_001', related: [
      { report_id: 'rpt_002', relation: 'duplicate' }, { report_id: 'rpt_003', relation: 'forwarded' }, { report_id: 'rpt_004', relation: 'corroborating' } ], corroboration_status: 'corroborated' },
    urgency: score(92, 'critical', ['Elderly residents on upper floors', 'Rising water reported']),
    confidence: score(84, 'high', ['Confirmed by an official source', 'Two independent sources']),
    verification: score(25, 'low', ['Already corroborated']),
    recommendation: { type: 'escalate_for_human_review', summary: 'Strong evidence and high urgency. Refer to a duty officer for a decision.', next_steps: ['Alert duty officer', 'Re-check water level in 30 minutes'] },
  }),
  makeReport({
    id: 'rpt_002', text: 'Lake Road is flooding, water inside homes, families moving upstairs.',
    sourceType: 'citizen', sourceName: 'Citizen reporter B', location: LOC.bellandur, ageMinutes: 18, incidentId: 'inc_001',
    duplicate: { is_duplicate: true, matches: [{ report_id: 'rpt_001', similarity: 0.91, reasons: ['Same location', 'Similar wording', 'Within 10 minutes'] }] },
    sourceVerification: { independence: 'independent', original_report_id: 'rpt_001', related: [{ report_id: 'rpt_001', relation: 'duplicate' }], corroboration_status: 'corroborated' },
    urgency: score(88, 'critical', ['Families relocating upstairs']),
    confidence: score(80, 'high', ['Independent source describing the same event']),
    verification: score(20, 'low', ['Matches an existing corroborated incident']),
    recommendation: { type: 'monitor', summary: 'Duplicate of rpt_001 from an independent source. Counts as corroboration.', next_steps: ['Link to incident inc_001'] },
  }),
  makeReport({
    id: 'rpt_003', text: 'FWD: Water entering ground floor houses on Lake Road. 40 people on first floors. Please share!',
    sourceType: 'social_media', sourceName: 'Social media account C', location: LOC.bellandur, ageMinutes: 12, incidentId: 'inc_001', forwardedFrom: 'rpt_001',
    duplicate: { is_duplicate: true, matches: [{ report_id: 'rpt_001', similarity: 0.97, reasons: ['Near-identical text', 'Forward marker "FWD"'] }] },
    sourceVerification: { independence: 'forwarded', original_report_id: 'rpt_001', related: [{ report_id: 'rpt_001', relation: 'forwarded' }], corroboration_status: 'single_source' },
    urgency: score(85, 'high', ['Same event as rpt_001']),
    confidence: score(20, 'low', ['Forwarded copy, not independent evidence']),
    verification: score(10, 'low', ['Covered by original report']),
    recommendation: { type: 'monitor', summary: 'Forwarded copy of rpt_001. It does not add independent evidence.', next_steps: ['Do not count as corroboration'] },
  }),
  makeReport({
    id: 'rpt_004', text: 'Ward officer on site: water level about 1.2 m on Lake Road, two vehicles stranded.',
    sourceType: 'official', sourceName: 'Ward officer', location: LOC.bellandur, ageMinutes: 8, incidentId: 'inc_001',
    duplicate: { is_duplicate: false, matches: [] },
    sourceVerification: { independence: 'independent', original_report_id: null, related: [{ report_id: 'rpt_001', relation: 'corroborating' }], corroboration_status: 'corroborated' },
    urgency: score(90, 'critical', ['Official confirms 1.2 m water level']),
    confidence: score(92, 'high', ['Official on-site source']),
    verification: score(10, 'low', ['Official source']),
    recommendation: { type: 'escalate_for_human_review', summary: 'Official on-site confirmation. Refer to a duty officer.', next_steps: ['Alert duty officer'] },
  }),
  makeReport({
    id: 'rpt_005', text: 'Building has collapsed on 4th Block. People trapped inside!',
    sourceType: 'citizen', sourceName: 'Citizen reporter D', location: LOC.koramangala, ageMinutes: 95, incidentId: 'inc_002',
    duplicate: { is_duplicate: false, matches: [] },
    sourceVerification: { independence: 'independent', original_report_id: 'rpt_005', related: [{ report_id: 'rpt_007', relation: 'forwarded' }, { report_id: 'rpt_006', relation: 'conflicting' }], corroboration_status: 'disputed' },
    conflicts: [cfl001],
    urgency: score(85, 'critical', ['People reported trapped']),
    confidence: score(35, 'low', ['Contradicted by rpt_006', 'No second independent source']),
    verification: score(92, 'high', ['Direct conflict with another report', 'High potential urgency']),
    recommendation: { type: 'verify_first', summary: 'Conflicting reports about a possible collapse. Verify on the ground first.', next_steps: ['Call the nearest responder', 'Ask for photo or video evidence'] },
  }),
  makeReport({
    id: 'rpt_006', text: 'Only a compound wall fell near 4th Block. Nobody trapped, building is fine.',
    sourceType: 'responder', sourceName: 'Patrol unit', location: LOC.koramangala, ageMinutes: 40, incidentId: 'inc_002',
    duplicate: { is_duplicate: false, matches: [] },
    sourceVerification: { independence: 'independent', original_report_id: 'rpt_006', related: [{ report_id: 'rpt_005', relation: 'conflicting' }], corroboration_status: 'disputed' },
    conflicts: [cfl001],
    urgency: score(40, 'medium', ['Reports no one trapped']),
    confidence: score(55, 'medium', ['Responder source', 'Contradicts rpt_005']),
    verification: score(88, 'high', ['Direct conflict with another report']),
    recommendation: { type: 'verify_first', summary: 'Responder report conflicts with a citizen report. Needs a human check.', next_steps: ['Confirm with the patrol unit', 'Compare with rpt_005'] },
  }),
  makeReport({
    id: 'rpt_007', text: 'FWD: Building collapsed 4th Block Koramangala, people trapped, share to help.',
    sourceType: 'social_media', sourceName: 'Social media account E', location: LOC.koramangala, ageMinutes: 70, incidentId: 'inc_002', forwardedFrom: 'rpt_005',
    duplicate: { is_duplicate: true, matches: [{ report_id: 'rpt_005', similarity: 0.95, reasons: ['Near-identical text', 'Forward marker "FWD"'] }] },
    sourceVerification: { independence: 'forwarded', original_report_id: 'rpt_005', related: [{ report_id: 'rpt_005', relation: 'forwarded' }], corroboration_status: 'disputed' },
    urgency: score(80, 'high', ['Same claim as rpt_005']),
    confidence: score(15, 'low', ['Forwarded copy of a disputed report']),
    verification: score(60, 'medium', ['Spreads a disputed claim']),
    recommendation: { type: 'verify_first', summary: 'Forwarded copy of a disputed claim. Do not treat as extra evidence.', next_steps: ['Resolve rpt_005 vs rpt_006 first'] },
  }),
  makeReport({
    id: 'rpt_008', text: 'Sparking power line and a small fire near the bus stop on Main Road.',
    sourceType: 'citizen', sourceName: 'Citizen reporter F', location: LOC.whitefield, ageMinutes: 310, incidentId: 'inc_003',
    duplicate: { is_duplicate: false, matches: [] },
    sourceVerification: { independence: 'independent', original_report_id: 'rpt_008', related: [], corroboration_status: 'single_source' },
    urgency: score(45, 'medium', ['Fire reported but described as small']),
    confidence: score(30, 'low', ['Single source', 'Report is stale']),
    verification: score(55, 'medium', ['Stale single-source report']),
    recommendation: { type: 'verify_first', summary: 'Old single-source report. Check whether the fire is still active.', next_steps: ['Contact the electricity board', 'Request a fresh update'] },
  }),
]

export const mockIncidents = [
  {
    id: 'inc_001', title: 'Flooding near Bellandur lake road', type: 'flood', location: LOC.bellandur,
    severity: 'critical', status: 'active', report_ids: ['rpt_001', 'rpt_002', 'rpt_003', 'rpt_004'], report_count: 4,
    independent_source_count: 3, first_reported_at: minsAgo(60), last_updated_at: minsAgo(8),
    timeline: [
      { timestamp: minsAgo(60), severity: 'medium', status: 'active', report_count: 1, affected_radius_m: 200, summary: 'First report of water entering homes' },
      { timestamp: minsAgo(30), severity: 'high', status: 'active', report_count: 3, affected_radius_m: 450, summary: 'More reports, spreading along the lake road' },
      { timestamp: minsAgo(8), severity: 'critical', status: 'active', report_count: 4, affected_radius_m: 700, summary: 'Official confirms 1.2 m water level' },
    ],
  },
  {
    id: 'inc_002', title: 'Reported structural collapse, Koramangala', type: 'structural', location: LOC.koramangala,
    severity: 'high', status: 'active', report_ids: ['rpt_005', 'rpt_006', 'rpt_007'], report_count: 3,
    independent_source_count: 2, first_reported_at: minsAgo(95), last_updated_at: minsAgo(40),
    timeline: [
      { timestamp: minsAgo(95), severity: 'high', status: 'active', report_count: 1, affected_radius_m: 100, summary: 'Citizen reports a collapsed building' },
      { timestamp: minsAgo(70), severity: 'high', status: 'active', report_count: 2, affected_radius_m: 100, summary: 'Claim forwarded on social media' },
      { timestamp: minsAgo(40), severity: 'medium', status: 'monitoring', report_count: 3, affected_radius_m: 50, summary: 'Responder says only a wall fell. Reports conflict' },
    ],
  },
  {
    id: 'inc_003', title: 'Power line fire, Whitefield', type: 'fire', location: LOC.whitefield,
    severity: 'medium', status: 'monitoring', report_ids: ['rpt_008'], report_count: 1,
    independent_source_count: 1, first_reported_at: minsAgo(310), last_updated_at: minsAgo(310),
    timeline: [
      { timestamp: minsAgo(310), severity: 'medium', status: 'active', report_count: 1, affected_radius_m: 30, summary: 'Single report of a small fire near a power line' },
    ],
  },
]

const priorityItems = [
  {
    incident_id: 'inc_001', title: 'Flooding near Bellandur lake road', location: LOC.bellandur,
    urgency: score(92, 'critical', ['Elderly residents on upper floors']),
    evidence_confidence: score(84, 'high', ['Official source and two independent reports']),
    verification_priority: score(25, 'low', ['Well corroborated']),
    explanation: ['Water level reported at 1.2 m', 'Official source confirms', 'Forwarded copies were not counted as evidence'],
    recommended_next_steps: ['Refer to the duty officer for a dispatch decision', 'Re-check in 30 minutes'],
    requires_human_decision: true, human_decision: { status: 'not_decided', decided_by: null, decided_at: null },
  },
  {
    incident_id: 'inc_002', title: 'Reported structural collapse, Koramangala', location: LOC.koramangala,
    urgency: score(85, 'critical', ['People reported trapped']),
    evidence_confidence: score(38, 'low', ['Conflicting reports']),
    verification_priority: score(91, 'high', ['Direct conflict between a citizen and a responder']),
    explanation: ['Possible collapse claim is disputed', 'Verification could change the response completely'],
    recommended_next_steps: ['Verify with a responder on site first', 'Do not dispatch based on this alone'],
    requires_human_decision: true, human_decision: { status: 'not_decided', decided_by: null, decided_at: null },
  },
  {
    incident_id: 'inc_003', title: 'Power line fire, Whitefield', location: LOC.whitefield,
    urgency: score(45, 'medium', ['Small fire reported']),
    evidence_confidence: score(30, 'low', ['Single source, stale']),
    verification_priority: score(55, 'medium', ['Needs a fresh update']),
    explanation: ['Report is more than 5 hours old', 'Single source only'],
    recommended_next_steps: ['Request a fresh update from the area'],
    requires_human_decision: true, human_decision: { status: 'not_decided', decided_by: null, decided_at: null },
  },
]

export function getMockPriority(sort = 'urgency') {
  const key = sort === 'verification' ? 'verification_priority' : 'urgency'
  const items = [...priorityItems]
    .sort((a, b) => b[key].score - a[key].score)
    .map((item, i) => ({ rank: i + 1, ...item }))
  return { sort, items }
}

export const mockGraphs = {
  inc_001: {
    incident_id: 'inc_001',
    nodes: [
      { id: 'rpt_001', report_id: 'rpt_001', label: 'Citizen A: Lake Road flooding', role: 'original', source_type: 'citizen', source_name: 'Citizen reporter A', timestamp: minsAgo(25), excerpt: 'Water entering ground floor houses...', freshness_status: 'recent' },
      { id: 'rpt_002', report_id: 'rpt_002', label: 'Citizen B: Lake Road flooding', role: 'duplicate', source_type: 'citizen', source_name: 'Citizen reporter B', timestamp: minsAgo(18), excerpt: 'Lake Road is flooding...', freshness_status: 'recent' },
      { id: 'rpt_003', report_id: 'rpt_003', label: 'Social: forwarded copy', role: 'forwarded', source_type: 'social_media', source_name: 'Social media account C', timestamp: minsAgo(12), excerpt: 'FWD: Water entering ground floor houses...', freshness_status: 'recent' },
      { id: 'rpt_004', report_id: 'rpt_004', label: 'Ward officer: 1.2 m water', role: 'corroborating', source_type: 'official', source_name: 'Ward officer', timestamp: minsAgo(8), excerpt: 'Water level about 1.2 m...', freshness_status: 'recent' },
    ],
    edges: [
      { id: 'edge_001', source: 'rpt_002', target: 'rpt_001', type: 'duplicate', label: 'Duplicate (0.91)', confidence: 0.91 },
      { id: 'edge_002', source: 'rpt_003', target: 'rpt_001', type: 'forwarded', label: 'Forwarded (0.97)', confidence: 0.97 },
      { id: 'edge_003', source: 'rpt_004', target: 'rpt_001', type: 'corroborating', label: 'Corroborates', confidence: 0.88 },
    ],
  },
  inc_002: {
    incident_id: 'inc_002',
    nodes: [
      { id: 'rpt_005', report_id: 'rpt_005', label: 'Citizen D: building collapse', role: 'original', source_type: 'citizen', source_name: 'Citizen reporter D', timestamp: minsAgo(95), excerpt: 'Building has collapsed on 4th Block...', freshness_status: 'aging' },
      { id: 'rpt_007', report_id: 'rpt_007', label: 'Social: forwarded copy', role: 'forwarded', source_type: 'social_media', source_name: 'Social media account E', timestamp: minsAgo(70), excerpt: 'FWD: Building collapsed 4th Block...', freshness_status: 'aging' },
      { id: 'rpt_006', report_id: 'rpt_006', label: 'Patrol: only a wall fell', role: 'conflicting', source_type: 'responder', source_name: 'Patrol unit', timestamp: minsAgo(40), excerpt: 'Only a compound wall fell...', freshness_status: 'recent' },
    ],
    edges: [
      { id: 'edge_004', source: 'rpt_007', target: 'rpt_005', type: 'forwarded', label: 'Forwarded (0.95)', confidence: 0.95 },
      { id: 'edge_005', source: 'rpt_006', target: 'rpt_005', type: 'conflicting', label: 'Conflicts: extent of damage', confidence: 0.8 },
    ],
  },
  inc_003: {
    incident_id: 'inc_003',
    nodes: [
      { id: 'rpt_008', report_id: 'rpt_008', label: 'Citizen F: power line fire', role: 'original', source_type: 'citizen', source_name: 'Citizen reporter F', timestamp: minsAgo(310), excerpt: 'Sparking power line and a small fire...', freshness_status: 'stale' },
    ],
    edges: [],
  },
}

// Simple arithmetic stand-in for Member 3's simulation. NOT a real model.
export function mockSimulate(inputs) {
  const { affected_population, disaster_severity, rescue_teams, blocked_roads, available_ambulances } = inputs
  const teamsNeeded = Math.ceil((affected_population / 5000) * (disaster_severity / 2))
  const ambulancesNeeded = Math.ceil((affected_population / 2000) * (disaster_severity / 3))
  const shortages = []
  if (teamsNeeded > rescue_teams) shortages.push({ resource: 'rescue_teams', required: teamsNeeded, available: rescue_teams, shortfall: teamsNeeded - rescue_teams })
  if (ambulancesNeeded > available_ambulances) shortages.push({ resource: 'ambulances', required: ambulancesNeeded, available: available_ambulances, shortfall: ambulancesNeeded - available_ambulances })
  const priority_changes = blocked_roads >= 3
    ? [{ incident_id: 'inc_002', title: 'Reported structural collapse, Koramangala', baseline_rank: 2, scenario_rank: 1, reason: 'Access roads blocked, fewer teams available' }]
    : []
  return {
    scenario_id: `sim_${Date.now()}`,
    is_simulation: true,
    generated_at: new Date().toISOString(),
    inputs,
    results: {
      resource_demand: { rescue_teams: teamsNeeded, ambulances: ambulancesNeeded },
      shortages,
      estimated_response_delay_minutes: blocked_roads * 5,
      priority_changes,
      summary: shortages.length ? `Shortages found in ${shortages.length} resource type(s) under this simulated scenario.` : 'Resources cover the simulated demand.',
    },
  }
}