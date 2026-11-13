import { Link } from 'react-router-dom'
import { Copy } from 'lucide-react'
import Badge from '../ui/Badge'
import Table from '../ui/Table'
import EmptyState from '../ui/EmptyState'

export default function DuplicatePanel({ report, reportsById }) {
  const { duplicate } = report.analysis

  const columns = [
    {
      key: 'report_id',
      header: 'Matched report',
      render: (m) => (
        <Link to={`/analysis?report=${m.report_id}`} className="font-mono text-xs text-accent hover:underline">
          {m.report_id}
        </Link>
      ),
    },
    {
      key: 'incident',
      header: 'Matched incident',
      render: (m) => {
        const incidentId = reportsById[m.report_id]?.incident_id
        return incidentId ? (
          <Link to={`/incidents/${incidentId}`} className="font-mono text-xs text-accent hover:underline">{incidentId}</Link>
        ) : (
          <span className="text-text-muted">—</span>
        )
      },
    },
    {
      key: 'similarity',
      header: 'Similarity',
      render: (m) => (
        <div className="flex min-w-32 items-center gap-2">
          <div className="h-2 w-20 overflow-hidden rounded bg-navy-700" aria-hidden="true">
            <div className="h-full bg-accent" style={{ width: `${Math.round(m.similarity * 100)}%` }} />
          </div>
          <span className="font-mono text-xs">{Math.round(m.similarity * 100)}%</span>
        </div>
      ),
    },
    {
      key: 'reasons',
      header: 'Why it was flagged',
      render: (m) => (
        <div className="flex flex-wrap gap-1">
          {m.reasons.map((reason) => <Badge key={reason}>{reason}</Badge>)}
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <p className="text-sm">
        <span className="font-mono text-accent">{report.id}</span>{' '}
        {duplicate.is_duplicate ? <Badge tone="verify">Possible duplicate</Badge> : <Badge>No duplicate found</Badge>}
      </p>
      {duplicate.matches.length === 0 ? (
        <EmptyState icon={Copy} title="No similar reports found" description="This report does not closely match any earlier report." />
      ) : (
        <Table columns={columns} rows={duplicate.matches} rowKey={(m) => m.report_id} caption="Possible duplicate matches" />
      )}
      <p className="text-xs text-text-muted">
        A duplicate means two reports describe the same event. It is not proof that the event is true. Similarity is an AI estimate, so a human should check borderline matches.
      </p>
    </div>
  )
}