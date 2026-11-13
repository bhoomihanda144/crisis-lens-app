import { Link, useNavigate, useParams } from 'react-router-dom'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import Skeleton from '../components/ui/Skeleton'
import ErrorState from '../components/ui/ErrorState'
import { Select } from '../components/ui/Input'
import EvidenceGraph from '../components/evidence/EvidenceGraph'
import { ROLE_STYLE } from '../components/evidence/roleStyle'
import useApi from '../hooks/useApi'
import { listIncidents } from '../services/incidentService'
import { getEvidenceGraph } from '../services/analysisService'
import { relationTone } from '../utils/tones'

export default function EvidenceGraphPage() {
  const { id } = useParams()
  const navigate = useNavigate()

  const incidents = useApi(() => listIncidents(), [])
  const list = incidents.data?.items ?? []
  const incidentId = id || list[0]?.id || null

  const graphRequest = useApi(() => (incidentId ? getEvidenceGraph(incidentId) : Promise.resolve(null)), [incidentId])
  const graph = graphRequest.data

  if (incidents.error) {
    return (
      <>
        <PageHeader title="Evidence Relationship Graph" />
        <ErrorState title="Could not load incidents" message={incidents.error.message} onRetry={incidents.reload} />
      </>
    )
  }

  const roleCounts = {}
  graph?.nodes.forEach((n) => {
    roleCounts[n.role] = (roleCounts[n.role] || 0) + 1
  })

  return (
    <>
      <PageHeader
        title="Evidence Relationship Graph"
        description="How the reports of one incident relate: original, duplicate, forwarded, corroborating and conflicting. Click a report for details. Scroll or use the controls to zoom, and drag the background to pan."
      />

      <Card className="mb-4">
        {incidents.loading && !incidents.data ? (
          <Skeleton className="h-10" />
        ) : list.length === 0 ? (
          <p className="text-sm text-text-muted">There are no incidents yet.</p>
        ) : (
          <div className="grid items-center gap-3 md:grid-cols-[1fr_auto]">
            <Select
              value={incidentId || ''}
              onChange={(v) => navigate(`/graph/${v}`)}
              options={list.map((i) => ({ value: i.id, label: `${i.id} — ${i.title}` }))}
              label="Choose an incident"
            />
            {incidentId && (
              <div className="flex gap-4 text-sm">
                <Link to={`/incidents/${incidentId}`} className="text-accent hover:underline">Incident details</Link>
                <Link to={`/verification?incident=${incidentId}`} className="text-accent hover:underline">Verification</Link>
              </div>
            )}
          </div>
        )}
      </Card>

      {graphRequest.error ? (
        <ErrorState
          title={graphRequest.error.code === 'not_found' ? 'No graph for this incident' : 'Could not load the graph'}
          message={graphRequest.error.message}
          onRetry={graphRequest.error.code === 'not_found' ? undefined : graphRequest.reload}
        />
      ) : graphRequest.loading && !graph ? (
        <Skeleton className="h-[520px]" />
      ) : graph ? (
        <>
          <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
            <span className="text-text-muted">{graph.nodes.length} report(s), {graph.edges.length} relationship(s):</span>
            {Object.entries(roleCounts).map(([role, count]) => (
              <Badge key={role} tone={relationTone[role]}>{ROLE_STYLE[role]?.label || role}: {count}</Badge>
            ))}
          </div>
          {graph.edges.length === 0 && (
            <p className="mb-3 text-sm text-text-muted">This incident has a single report, so there are no relationships to draw yet.</p>
          )}
          <EvidenceGraph key={graph.incident_id} graph={graph} />
        </>
      ) : null}
    </>
  )
}