// Stand-in for the backend in Demo Mode. SIMULATED. Not Member 2's or Member 3's code.
import { mockReports, mockIncidents, mockGraphs, getMockPriority, mockSimulate } from '../data/mockData'
import { ApiError } from './api'

const reports = structuredClone(mockReports)
const incidents = structuredClone(mockIncidents)

const reply = (value, ms = 350) =>
  new Promise((resolve) => setTimeout(() => resolve(structuredClone(value)), ms))
const fail = (status, code, message) =>
  new Promise((_, reject) => setTimeout(() => reject(new ApiError({ code, message, status })), 250))

const findReport = (id) => reports.find((r) => r.id === id)
const freshnessOf = (m) => (m <= 60 ? 'recent' : m <= 240 ? 'aging' : 'stale')
const levelOf = (s) => (s >= 75 ? 'critical' : s >= 50 ? 'high' : s >= 25 ? 'medium' : 'low')
const threeLevel = (s) => (s >= 67 ? 'high' : s >= 34 ? 'medium' : 'low')
const words = (t) => new Set(t.toLowerCase().replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter((w) => w.length > 2))
const jaccard = (a, b) => {
  const inter = [...a].filter((w) => b.has(w)).length
  return inter / (a.size + b.size - inter || 1)
}

export function listReports({ q, status, freshness, incident_id, sort = 'newest', limit = 50, offset = 0 } = {}) {
  let items = reports.filter((r) => {
    const haystack = `${r.id} ${r.text} ${r.source.name} ${r.location.label}`.toLowerCase()
    return (
      (!q || haystack.includes(q.toLowerCase())) &&
      (!status || r.status === status) &&
      (!freshness || r.analysis?.freshness.status === freshness) &&
      (!incident_id || r.incident_id === incident_id)
    )
  })
  items = [...items].sort((a, b) =>
    sort === 'verification_priority'
      ? (b.analysis?.scores.verification_priority.score ?? -1) - (a.analysis?.scores.verification_priority.score ?? -1)
      : new Date(b.reported_at) - new Date(a.reported_at),
  )
  return reply({ items: items.slice(offset, offset + limit), total: items.length, limit, offset })
}

export function getReport(id) {
  const report = findReport(id)
  return report ? reply(report) : fail(404, 'not_found', `Report ${id} not found`)
}

export function createReport(body) {
  if (!body?.text?.trim() || !body?.source?.type || !body?.location) {
    return fail(422, 'validation_error', 'text, source and location are required')
  }
  const now = new Date().toISOString()
  const report = {
    id: `rpt_${String(reports.length + 1).padStart(3, '0')}`,
    text: body.text.trim(),
    source: body.source,
    location: body.location,
    reported_at: body.reported_at || now,
    received_at: now,
    status: 'pending_analysis',
    incident_id: null,
    forwarded_from: body.forwarded_from || null,
    analysis: null,
    verification: null,
  }
  reports.push(report)
  return reply(report)
}

export function analyzeReport(id) {
  const report = findReport(id)
  if (!report) return fail(404, 'not_found', `Report ${id} not found`)

  const age = Math.max(0, Math.round((Date.now() - new Date(report.reported_at).getTime()) / 60000))
  const mine = words(report.text)
  const matches = reports
    .filter((r) => r.id !== id && r.location.label === report.location.label)
    .map((r) => ({ report_id: r.id, similarity: Number(jaccard(mine, words(r.text)).toFixed(2)) }))
    .filter((m) => m.similarity >= 0.4)
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, 3)
    .map((m) => ({ ...m, reasons: ['Same location', 'Similar wording'] }))

  const forwarded = Boolean(report.forwarded_from) || /^fwd/i.test(report.text)
  const keywords = ['trapped', 'collapse', 'fire', 'flood', 'injured', 'water', 'elderly', 'children']
  const hits = keywords.filter((k) => report.text.toLowerCase().includes(k)).length
  const urgency = Math.min(95, 25 + hits * 15)
  const confidence = forwarded ? 20 : report.source.type === 'official' || report.source.type === 'responder' ? 70 : 45
  const verification = Math.round((urgency * (100 - confidence)) / 100)

  report.analysis = {
    analyzed_at: new Date().toISOString(),
    engine_version: 'mock-analyzer-0.0.1 (SIMULATED)',
    duplicate: { is_duplicate: matches.length > 0, matches },
    source_verification: {
      independence: forwarded ? 'forwarded' : 'unknown',
      original_report_id: forwarded ? report.forwarded_from : report.id,
      related: matches.map((m) => ({ report_id: m.report_id, relation: 'duplicate' })),
      corroboration_status: matches.length ? 'corroborated' : 'single_source',
    },
    freshness: { status: freshnessOf(age), age_minutes: age, last_updated: report.reported_at },
    conflicts: [],
    scores: {
      urgency: { score: urgency, level: levelOf(urgency), reasons: ['Keyword-based demo estimate'] },
      evidence_confidence: { score: confidence, level: threeLevel(confidence), reasons: [forwarded ? 'Forwarded copy' : 'Demo estimate by source type'] },
      verification_priority: { score: verification, level: threeLevel(verification), reasons: ['Demo estimate'] },
    },
    recommendation: {
      type: verification >= 50 ? 'verify_first' : urgency >= 75 && confidence >= 60 ? 'escalate_for_human_review' : 'monitor',
      summary: 'Simulated recommendation from the demo analyzer. Not a real AI result.',
      next_steps: ['A human responder reviews this report'],
      requires_human_decision: true,
    },
  }
  report.status = 'analyzed'
  return reply(report, 700)
}

export function listIncidents({ status, severity, type } = {}) {
  const items = incidents.filter(
    (i) => (!status || i.status === status) && (!severity || i.severity === severity) && (!type || i.type === type),
  )
  return reply({ items, total: items.length })
}

export function getIncident(id) {
  const incident = incidents.find((i) => i.id === id)
  return incident ? reply(incident) : fail(404, 'not_found', `Incident ${id} not found`)
}

export const getPriority = (sort = 'urgency') => reply(getMockPriority(sort))

export function getEvidenceGraph(id) {
  return mockGraphs[id] ? reply(mockGraphs[id]) : fail(404, 'not_found', `No evidence graph for incident ${id}`)
}

export function runSimulation(body) {
  const nonNegative = ['affected_population', 'rescue_teams', 'blocked_roads', 'available_ambulances']
  const valid =
    nonNegative.every((k) => Number.isInteger(body?.[k]) && body[k] >= 0) &&
    Number.isInteger(body?.disaster_severity) && body.disaster_severity >= 1 && body.disaster_severity <= 5
  if (!valid) return fail(422, 'validation_error', 'Severity must be 1 to 5 and all other fields must be whole numbers of 0 or more')
  return reply({ ...mockSimulate(body), inputs: body }, 600)
}

export function verifyReport(id, body) {
  const report = findReport(id)
  if (!report) return fail(404, 'not_found', `Report ${id} not found`)
  const statusByAction = { confirm: 'verified', reject: 'rejected', request_more_info: 'needs_more_info' }
  if (!statusByAction[body?.action]) return fail(422, 'validation_error', 'action must be confirm, reject or request_more_info')
  report.status = statusByAction[body.action]
  report.verification = {
    action: body.action,
    note: body.note || '',
    verified_by: body.verified_by || null,
    verified_at: new Date().toISOString(),
  }
  return reply(report)
}