import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const short = (text) => (text.length > 20 ? `${text.slice(0, 20)}…` : text)

export default function PriorityScoresChart({ items }) {
  if (!items.length) return <p className="py-10 text-center text-sm text-text-muted">No incidents to chart.</p>

  const data = items.map((item) => ({
    name: short(item.title),
    Urgency: item.urgency.score,
    'Evidence confidence': item.evidence_confidence.score,
    'Verification priority': item.verification_priority.score,
  }))

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid stroke="#223660" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} stroke="#223660" />
          <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 12 }} stroke="#223660" />
          <Tooltip
            cursor={{ fill: 'rgba(148,163,184,0.08)' }}
            contentStyle={{ background: '#0f1b33', border: '1px solid #223660', borderRadius: 8 }}
            labelStyle={{ color: '#e6edf8' }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
          <Bar dataKey="Urgency" fill="#ef4444" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Evidence confidence" fill="#22d3ee" radius={[4, 4, 0, 0]} />
          <Bar dataKey="Verification priority" fill="#f97316" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}