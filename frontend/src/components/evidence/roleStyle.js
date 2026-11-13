export const ROLE_STYLE = {
  original: { label: 'Original', color: '#22d3ee', description: 'The earliest report this evidence traces back to.' },
  duplicate: { label: 'Duplicate', color: '#94a3b8', description: 'Describes the same event as another report.' },
  forwarded: { label: 'Forwarded copy', color: '#f97316', description: 'A copy of another report. Not independent evidence.' },
  corroborating: { label: 'Corroborating', color: '#22c55e', description: 'An independent report that supports another one.' },
  conflicting: { label: 'Conflicting', color: '#ef4444', description: 'Contradicts another report. A human must verify.' },
}