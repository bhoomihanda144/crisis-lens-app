import { api } from './api'
import { isDemo } from './mode'
import * as mock from './mockApi'

// params: { q, status, freshness, incident_id, sort, limit, offset }
export const listReports = (params) => (isDemo() ? mock.listReports(params) : api.get('/reports', { params }))
export const getReport = (id) => (isDemo() ? mock.getReport(id) : api.get(`/reports/${encodeURIComponent(id)}`))
export const createReport = (body) => (isDemo() ? mock.createReport(body) : api.post('/reports', body))