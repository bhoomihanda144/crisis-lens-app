import { api } from './api'
import { isDemo } from './mode'
import * as mock from './mockApi'

// body: { action: 'confirm' | 'reject' | 'request_more_info', note?, verified_by? }
export const verifyReport = (reportId, body) =>
  isDemo() ? mock.verifyReport(reportId, body) : api.patch(`/reports/${encodeURIComponent(reportId)}/verify`, body)