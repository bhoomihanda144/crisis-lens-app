import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Lightbulb, UserCheck, Info } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import Card, { CardHeader } from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Skeleton from '../components/ui/Skeleton'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import { ScoreTriple } from '../components/priority/ScoreBadge'
import DecisionModal from '../components/priority/DecisionModal'
import useApi from '../hooks/useApi'
import useDataMode from '../hooks/useDataMode'
import { getPriority } from '../services/analysisService'
import { DECISION_ENDPOINT_AGREED } from '../services/incidentService'
import { DECISION_LABEL } from '../utils/decisions'
import { formatDateTime } from '../utils/format'

function PriorityCard({ item, canDecide, onDecide }) {
  const decision = item.human_decision
  const decided = decision.status !== 'not_decided'

  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs text-text-muted">Rank {item.rank} (a sort order, not a score)</p>
          <h2 className="text-lg font-semibold">
            <Link to={`/incidents/${item.incident_id}`} className="hover:text-accent">{item.title}</Link>
          </h2>
          <p className="text-sm text-text-muted">{item.location.label}</p>
        </div>
        <div className="flex gap-4 text-sm">
          <Link to={`/graph/${item.incident_id}`} className="text-accent hover:underline">Evidence graph</Link>
          <Link to={`/verification?incident=${item.incident_id}`} className="text-accent hover:underline">Verification</Link>
        </div>
      </div>

      <ScoreTriple
        urgency={item.urgency}
        evidenceConfidence={item.evidence_confidence}
        verificationPriority={item.verification_priority}
      />

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-accent/30 p-4">
          <p className="flex items-center gap-2 text-sm font-semibold">
            <Lightbulb className="h-4 w-4 text-accent" aria-hidden="true" />
            AI recommendation <Badge tone="info">Advice only</Badge>
          </p>
          <p className="mb-1 mt-3 text-xs font-medium uppercase tracking-wide text-text-muted">Why</p>
          <ul className="list-disc space-y-1 pl-5 text-sm text-text-muted">
            {item.explanation.map((line) => <li key={line}>{line}</li>)}
          </ul>
          <p className="mb-1 mt-3 text-xs font-medium uppercase tracking-wide text-text-muted">Suggested next steps</p>
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {item.recommended_next_steps.map((line) => <li key={line}>{line}</li>)}
          </ul>
        </div>

        <div className="rounded-xl bg-navy-900 p-4">
          <p className="flex items-center gap-2 text-sm font-semibold">
            <UserCheck className="h-4 w-4 text-verified" aria-hidden="true" />
            Human decision
            <Badge tone={decided ? 'verified' : 'neutral'}>{DECISION_LABEL[decision.status] || decision.status}</Badge>
          </p>
          {decided ? (
            <p className="mt-3 text-sm text-text-muted">
              Recorded by {decision.decided_by || 'unknown'}
              {decision.decided_at && <> on {formatDateTime(decision.decided_at)}</>}.
              {decision.note && <> Note: “{decision.note}”</>}
            </p>
          ) : (
            <p className="mt-3 text-sm text-text-muted">
              Nothing has been decided. The AI cannot dispatch anyone. A responder must choose.
            </p>
          )}
          <Button
            className="mt-4"
            variant={decided ? 'secondary' : 'primary'}
            disabled={!canDecide}
            onClick={() => onDecide(item)}
          >
            {decided ? 'Change decision' : 'Record a decision'}
          </Button>
        </div>
      </div>
    </Card>
  )
}

export default function RescuePriorityPage() {
  const mode = useDataMode()
  const canDecide = mode === 'demo' || DECISION_ENDPOINT_AGREED
  const [sort, setSort] = useState('urgency')
  const [deciding, setDeciding] = useState(null)
  const [notice, setNotice] = useState('')
  const { data, loading, error, reload } = useApi(() => getPriority(sort), [sort])

  return (
    <>
      <PageHeader
        title="Smart Rescue Priority"
        description="Urgency, evidence confidence and verification priority are shown separately and never combined. The ranking only sorts the list. The AI advises and a human decides."
        actions={
          <>
            <Button size="sm" variant={sort === 'urgency' ? 'primary' : 'secondary'} onClick={() => setSort('urgency')}>Sort by urgency</Button>
            <Button size="sm" variant={sort === 'verification' ? 'primary' : 'secondary'} onClick={() => setSort('verification')}>Sort verify first</Button>
          </>
        }
      />

      {notice && (
        <div role="status" className="mb-4 flex items-start justify-between gap-3 rounded-lg border border-verified/40 bg-verified/10 px-4 py-2 text-sm text-green-200">
          <span>{notice}</span>
          <button onClick={() => setNotice('')} className="text-xs underline">Dismiss</button>
        </div>
      )}
      {!canDecide && (
        <div className="mb-4 flex items-start gap-2 rounded-lg border border-navy-600 bg-navy-800 px-4 py-2 text-sm text-text-muted">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden="true" />
          Recording decisions is switched off in Live Mode until the team adds it to the approved API contract. Use Demo Mode to try the screen.
        </div>
      )}

      {error ? (
        <ErrorState title="Could not load priorities" message={error.message} onRetry={reload} />
      ) : loading && !data ? (
        <div className="space-y-4"><Skeleton className="h-96" /><Skeleton className="h-96" /></div>
      ) : data.items.length === 0 ? (
        <EmptyState title="Nothing to prioritise" description="There are no incidents to rank right now." />
      ) : (
        <div className={loading ? 'space-y-6 opacity-60 transition-opacity' : 'space-y-6 transition-opacity'}>
          {data.items.map((item) => (
            <PriorityCard key={item.incident_id} item={item} canDecide={canDecide} onDecide={setDeciding} />
          ))}
        </div>
      )}

      {deciding && (
        <DecisionModal
          key={deciding.incident_id}
          item={deciding}
          onClose={() => setDeciding(null)}
          onSaved={(item) => {
            setNotice(`Decision recorded for “${item.title}”. This logs a human judgement and does not dispatch anyone.`)
            setDeciding(null)
            reload()
          }}
        />
      )}
    </>
  )
}