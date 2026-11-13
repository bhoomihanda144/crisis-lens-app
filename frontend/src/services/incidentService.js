import { api, ApiError } from './api'
import { isDemo } from './mode'
import * as mock from './mockApi'

// Set to true only after the team approves the decision endpoint in the contract (v1.1) and Member 2 has built it.
export const DECISION_ENDPOINT_AGREED = false

// params: { status, severity, type }
export const listIncidents = (params) => (isDemo() ? mock.listIncidents(params) : api.get('/incidents', { params }))
export const getIncident = (id) => (isDemo() ? mock.getIncident(id) : api.get(`/incidents/${encodeURIComponent(id)}`))

// body: { status: 'referred_to_duty_officer' | 'monitoring' | 'dismissed', decided_by, note? }
// Logs a human judgement. It does not dispatch anyone.
export function recordDecision(incidentId, body) {
  if (isDemo()) return mock.recordDecision(incidentId, body)
  if (!DECISION_ENDPOINT_AGREED) {
    return Promise.reject(
      new ApiError({
        code: 'not_supported',
        message: 'Recording decisions is not part of the approved API contract yet.',
      }),
    )
  }
  return api.patch(`/incidents/${encodeURIComponent(incidentId)}/decision`, body)
}