import { api } from './api'
import { isDemo } from './mode'
import * as mock from './mockApi'

export const analyzeReport = (reportId) =>
  isDemo() ? mock.analyzeReport(reportId) : api.post(`/analyze/${encodeURIComponent(reportId)}`)

// sort: 'urgency' | 'verification' (changes ranking only, scores stay separate)
export const getPriority = (sort = 'urgency') =>
  isDemo() ? mock.getPriority(sort) : api.get('/incidents/priority', { params: { sort } })

export const getEvidenceGraph = (incidentId) =>
  isDemo() ? mock.getEvidenceGraph(incidentId) : api.get(`/incidents/${encodeURIComponent(incidentId)}/evidence-graph`)