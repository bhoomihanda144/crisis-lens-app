import { Link } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import Badge from '../ui/Badge'
import EmptyState from '../ui/EmptyState'
import { formatDateTime, labelOf } from '../../utils/format'

export default function ConflictPanel({ report, reportsById }) {
  const { conflicts } = report.analysis

  if (conflicts.length === 0) {
    return <EmptyState icon={ShieldCheck} title="No conflicts detected" description="No contradictory statements were found for this report." />
  }

  return (
    <div className="space-y-4">
      {conflicts.map((conflict) => (
        <div key={conflict.id} className="rounded-xl border border-verify/40 bg-navy-900 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="font-medium">{conflict.topic}</p>
            <span className="text-xs text-text-muted">Detected {formatDateTime(conflict.detected_at)}</span>
          </div>
          <ul className="mt-3 space-y-2">
            {conflict.statements.map((s) => {
              const other = reportsById[s.report_id]
              return (
                <li key={s.report_id} className="rounded-md bg-navy-800 px-3 py-2 text-sm">
                  <div className="mb-1 flex flex-wrap items-center gap-2">
                    <Link to={`/analysis?report=${s.report_id}`} className="font-mono text-xs text-accent hover:underline">{s.report_id}</Link>
                    {other && <Badge>{labelOf(other.source.type)}</Badge>}
                    {other && <span className="text-xs text-text-muted">{formatDateTime(other.reported_at)}</span>}
                  </div>
                  {s.text}
                </li>
              )
            })}
          </ul>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
            <span className="text-text-muted">Human verification:</span>
            {conflict.report_ids.map((id) => (
              <Link key={id} to={`/verification?report=${id}`} className="text-accent hover:underline">Verify {id}</Link>
            ))}
          </div>
        </div>
      ))}
      <p className="text-xs text-text-muted">The system flags the disagreement. It does not decide which report is right.</p>
    </div>
  )
}