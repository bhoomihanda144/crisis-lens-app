export const SEVERITY_COLOR = { low: '#94a3b8', medium: '#22d3ee', high: '#f97316', critical: '#ef4444' }

// Every distinct timestamp in any incident's timeline, oldest first. Each one is a slider step.
export function buildSteps(incidents) {
  const set = new Set()
  incidents.forEach((incident) => incident.timeline.forEach((entry) => set.add(entry.timestamp)))
  return [...set].sort((a, b) => Date.parse(a) - Date.parse(b))
}

// The newest timeline entry at or before `time`, or null if the incident was not reported yet.
export function stateAt(incident, time) {
  let current = null
  for (const entry of incident.timeline) {
    if (Date.parse(entry.timestamp) <= Date.parse(time)) current = entry
    else break
  }
  return current
}