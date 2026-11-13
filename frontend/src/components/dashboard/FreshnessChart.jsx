import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

const COLORS = { recent: '#22d3ee', aging: '#f97316', stale: '#64748b' }
const LABELS = { recent: 'Recent (up to 60 min)', aging: 'Aging (61–240 min)', stale: 'Stale (over 240 min)' }

export default function FreshnessChart({ reports }) {
  const counts = { recent: 0, aging: 0, stale: 0 }
  let notAnalysed = 0
  reports.forEach((report) => {
    const status = report.analysis?.freshness.status
    if (status) counts[status] += 1
    else notAnalysed += 1
  })
  const data = Object.entries(counts)
    .filter(([, value]) => value > 0)
    .map(([name, value]) => ({ name, value }))

  if (data.length === 0) {
    return <p className="py-10 text-center text-sm text-text-muted">No analysed reports yet.</p>
  }

  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row">
      <div className="h-56 w-full sm:w-1/2">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={55} outerRadius={85} paddingAngle={2} stroke="none">
              {data.map((entry) => (
                <Cell key={entry.name} fill={COLORS[entry.name]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, name) => [value, LABELS[name]]}
              contentStyle={{ background: '#0f1b33', border: '1px solid #223660', borderRadius: 8 }}
              itemStyle={{ color: '#e6edf8' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="w-full space-y-2 text-sm sm:w-1/2">
        {Object.keys(counts).map((key) => (
          <li key={key} className="flex items-center justify-between gap-2">
            <span className="flex items-center gap-2">
              <span className="inline-block h-3 w-3 rounded-sm" style={{ background: COLORS[key] }} aria-hidden="true" />
              {LABELS[key]}
            </span>
            <span className="font-mono">{counts[key]}</span>
          </li>
        ))}
        {notAnalysed > 0 && (
          <li className="flex items-center justify-between text-text-muted">
            <span>Not analysed yet</span>
            <span className="font-mono">{notAnalysed}</span>
          </li>
        )}
      </ul>
    </div>
  )
}
