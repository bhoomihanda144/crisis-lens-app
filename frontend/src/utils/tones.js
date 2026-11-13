export const severityTone = { low: 'neutral', medium: 'info', high: 'verify', critical: 'critical' }
export const freshnessTone = { recent: 'info', aging: 'verify', stale: 'neutral' }
export const reportStatusTone = {
  pending_analysis: 'neutral',
  analyzed: 'info',
  verified: 'verified',
  rejected: 'critical',
  needs_more_info: 'verify',
}
export const verificationLevelTone = { low: 'verified', medium: 'verify', high: 'critical' }
export const urgencyTone = { low: 'neutral', medium: 'info', high: 'critical', critical: 'critical' }
export const confidenceTone = { low: 'verify', medium: 'info', high: 'verified' }
export const verificationTone = { low: 'neutral', medium: 'verify', high: 'verify' }
export const independenceTone = { independent: 'info', forwarded: 'verify', unknown: 'neutral' }
export const corroborationTone = { corroborated: 'verified', single_source: 'verify', disputed: 'critical' }
export const relationTone = { original: 'info', duplicate: 'neutral', forwarded: 'verify', corroborating: 'verified', conflicting: 'critical' }
export const recommendationTone = { verify_first: 'verify', monitor: 'info', escalate_for_human_review: 'critical' }