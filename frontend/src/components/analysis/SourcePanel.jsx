import { Link } from 'react-router-dom'
import { Share2 } from 'lucide-react'
import Badge from '../ui/Badge'
import Table from '../ui/Table'
import EmptyState from '../ui/EmptyState'
import { labelOf } from '../../utils/format'
import { independenceTone, corroborationTone, relationTone } from '../../utils/tones'

const INDEPENDENCE_TEXT = {
  independent: 'Reported from its own observation, not copied from another report.',
  forwarded: 'A forward or copy of another report. It does not add independent evidence.',
  unknown: 'The system could not tell whether this source is independent.',
}
const CORROBORATION_TEXT = {
  corroborated: 'At least two independent sources describe the same event.',
  single_source: 'Only one independent source so far.',
  disputed: 'Reports disagree with each other. Verify before acting.',
}

export default function SourcePanel({ report, reportsById }) {
  const sv = report.analysis.source_verification

  const columns = [
    {
      key: 'report_id',
      header: 'Related report',
      render: (item) => (
        <Link to={`/analysis?report=${item.report_id}`} className="font-mono text-xs text-accent hover:underline">{item.report_id}</Link>
      ),
    },
    { key: 'relation', header: 'Relationship', render: (item) => <Badge tone={relationTone[item.relation]}>{labelOf(item.relation)}</Badge> },
    {
      key: 'source',
      header: 'Source',
      render: (item) => {
        const other = reportsById[item.report_id]
        return other ? `${other.source.name} (${labelOf(other.source.type)})` : '—'
      },
    },
  ]

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-lg bg-navy-900 p-3">
          <p className="text-xs text-text-muted">This report</p>
          <div className="mt-1"><Badge tone={independenceTone[sv.independence]}>{labelOf(sv.independence)}</Badge></div>
          <p className="mt-2 text-xs text-text-muted">{INDEPENDENCE_TEXT[sv.independence]}</p>
        </div>
        <div className="rounded-lg bg-navy-900 p-3">
          <p className="text-xs text-text-muted">Original source</p>
          <p className="mt-1">
            {sv.original_report_id ? (
              <Link to={`/analysis?report=${sv.original_report_id}`} className="font-mono text-sm text-accent hover:underline">{sv.original_report_id}</Link>
            ) : (
              <span className="text-sm text-text-muted">Not identified</span>
            )}
          </p>
          <p className="mt-2 text-xs text-text-muted">The earliest report this one traces back to.</p>
        </div>
        <div className="rounded-lg bg-navy-900 p-3">
          <p className="text-xs text-text-muted">Corroboration</p>
          <div className="mt-1"><Badge tone={corroborationTone[sv.corroboration_status]}>{labelOf(sv.corroboration_status)}</Badge></div>
          <p className="mt-2 text-xs text-text-muted">{CORROBORATION_TEXT[sv.corroboration_status]}</p>
        </div>
      </div>

      {sv.related.length === 0 ? (
        <EmptyState icon={Share2} title="No related reports" description="Nothing else is linked to this report yet." />
      ) : (
        <Table columns={columns} rows={sv.related} rowKey={(item) => `${item.report_id}-${item.relation}`} caption="Source relationships" />
      )}
      <p className="text-xs text-text-muted">Forwarded and copied reports are never counted as independent corroboration.</p>
    </div>
  )
}