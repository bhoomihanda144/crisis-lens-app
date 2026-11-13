import { Link } from 'react-router-dom'
import { MousePointerClick } from 'lucide-react'
import Card, { CardHeader } from '../ui/Card'
import Badge from '../ui/Badge'
import { ROLE_STYLE } from './roleStyle'
import { formatDateTime, timeAgo, labelOf } from '../../utils/format'
import { freshnessTone, relationTone } from '../../utils/tones'

export default function NodeDetails({ node, graph }) {
  if (!node) {
    return (
      <Card className="flex flex-col items-center justify-center py-10 text-center">
        <MousePointerClick className="h-8 w-8 text-text-muted" aria-hidden="true" />
        <p className="mt-2 text-sm text-text-muted">Select a report in the graph to see its details and relationships.</p>
      </Card>
    )
  }

  const style = ROLE_STYLE[node.role]
  const related = graph.edges
    .filter((e) => e.source === node.id || e.target === node.id)
    .map((e) => ({
      edge: e,
      otherId: e.source === node.id ? e.target : e.source,
      direction: e.source === node.id ? 'points to' : 'is pointed to by',
    }))

  return (
    <Card>
      <CardHeader
        title={<span className="font-mono text-accent">{node.report_id}</span>}
        subtitle={`${node.source_name} (${labelOf(node.source_type)})`}
        action={<Badge tone={relationTone[node.role]}>{style?.label || labelOf(node.role)}</Badge>}
      />
      <p className="text-sm">{node.excerpt}</p>
      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
        <div>
          <dt className="text-text-muted">Reported</dt>
          <dd>{formatDateTime(node.timestamp)} ({timeAgo(node.timestamp)})</dd>
        </div>
        <div>
          <dt className="text-text-muted">Freshness</dt>
          <dd><Badge tone={freshnessTone[node.freshness_status]}>{labelOf(node.freshness_status)}</Badge></dd>
        </div>
      </dl>

      <h3 className="mb-1 mt-4 text-sm font-medium">Relationships</h3>
      {related.length === 0 ? (
        <p className="text-xs text-text-muted">This report has no links to other reports.</p>
      ) : (
        <ul className="space-y-2 text-xs">
          {related.map(({ edge, otherId, direction }) => (
            <li key={edge.id} className="rounded-md bg-navy-900 px-3 py-2">
              <Badge tone={relationTone[edge.type]}>{labelOf(edge.type)}</Badge>{' '}
              {direction}{' '}
              <Link to={`/analysis?report=${otherId}`} className="font-mono text-accent hover:underline">{otherId}</Link>
              <span className="mt-1 block text-text-muted">
                {edge.label} · confidence {Math.round(edge.confidence * 100)}%
              </span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-4 flex flex-wrap gap-4 text-sm">
        <Link to={`/analysis?report=${node.report_id}`} className="text-accent hover:underline">Open analysis</Link>
        <Link to={`/verification?report=${node.report_id}`} className="text-accent hover:underline">Verify this report</Link>
      </div>
    </Card>
  )
}