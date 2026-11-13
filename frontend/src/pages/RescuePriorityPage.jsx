import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Lightbulb, UserCheck, Info, ShieldAlert, ArrowUpRight, ChevronRight } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
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

function RankBadge({ rank }) {
  if (rank === 1) return (
    <div className="flex items-center gap-2 rounded-lg px-3 py-1.5"
      style={{
        background: 'linear-gradient(135deg, rgba(255,59,59,0.15) 0%, rgba(255,59,59,0.05) 100%)',
        border: '1px solid rgba(255,59,59,0.3)',
        boxShadow: '0 0 16px rgba(255,59,59,0.2)',
      }}>
      <span className="animate-dot-blink h-2 w-2 rounded-full bg-critical" />
      <span className="font-tactical text-xs font-bold tracking-widest text-red-300">RANK #1 · CRITICAL PRIORITY</span>
    </div>
  )
  return (
    <div className="flex items-center gap-2 rounded-lg px-3 py-1.5"
      style={{ background: 'rgba(10,18,34,0.6)', border: '1px solid rgba(0,229,255,0.1)' }}>
      <span className="font-tactical text-xs font-semibold tracking-widest text-text-muted">RANK #{rank}</span>
    </div>
  )
}

function PriorityCard({ item, canDecide, onDecide }) {
  const decision = item.human_decision
  const decided = decision.status !== 'not_decided'
  const isTopRank = item.rank === 1

  return (
    <div
      className="rounded-2xl transition-all duration-300 hover:-translate-y-0.5 animate-fade-in-up bracket-corner"
      style={{
        background: 'linear-gradient(135deg, rgba(12,23,43,0.95) 0%, rgba(9,18,34,0.98) 100%)',
        border: isTopRank
          ? '1px solid rgba(255,59,59,0.25)'
          : '1px solid rgba(0,229,255,0.1)',
        boxShadow: isTopRank
          ? '0 0 0 1px rgba(255,59,59,0.08), 0 8px 40px rgba(0,0,0,0.6), 0 0 30px rgba(255,59,59,0.08)'
          : '0 8px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(0,229,255,0.03)',
        backdropFilter: 'blur(16px)',
      }}>

      {/* Top bar accent */}
      <div className="h-px w-full rounded-t-2xl"
        style={{ background: isTopRank
          ? 'linear-gradient(90deg, transparent 0%, rgba(255,59,59,0.6) 30%, rgba(255,59,59,0.6) 70%, transparent 100%)'
          : 'linear-gradient(90deg, transparent 0%, rgba(0,229,255,0.3) 50%, transparent 100%)' }} />

      <div className="p-5">
        {/* Header */}
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-col gap-2">
            <RankBadge rank={item.rank} />
            <h2 className="text-xl font-bold text-text-primary leading-tight">
              <Link to={`/incidents/${item.incident_id}`}
                className="inline-flex items-center gap-2 hover:text-accent transition-colors group">
                {item.title}
                <ArrowUpRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity text-accent" />
              </Link>
            </h2>
            <p className="flex items-center gap-1.5 text-sm text-text-muted">
              <span className="h-1.5 w-1.5 rounded-full bg-accent" />
              {item.location.label}
            </p>
          </div>
          <div className="flex flex-col gap-2 items-end">
            <div className="flex gap-2">
              <Link to={`/graph/${item.incident_id}`}
                className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-accent transition-all hover:text-cyan-300"
                style={{ background: 'rgba(0,229,255,0.07)', border: '1px solid rgba(0,229,255,0.15)' }}>
                Evidence Graph <ChevronRight className="h-3 w-3" />
              </Link>
              <Link to={`/verification?incident=${item.incident_id}`}
                className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-text-muted transition-all hover:text-text-primary"
                style={{ background: 'rgba(10,18,34,0.6)', border: '1px solid rgba(0,229,255,0.08)' }}>
                Verify <ChevronRight className="h-3 w-3" />
              </Link>
            </div>
          </div>
        </div>

        {/* Score triple */}
        <ScoreTriple
          urgency={item.urgency}
          evidenceConfidence={item.evidence_confidence}
          verificationPriority={item.verification_priority}
        />

        {/* AI + Human decision panels */}
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          {/* AI recommendation */}
          <div className="rounded-xl p-4 relative overflow-hidden"
            style={{
              background: 'linear-gradient(135deg, rgba(0,229,255,0.04) 0%, rgba(0,229,255,0.01) 100%)',
              border: '1px solid rgba(0,229,255,0.2)',
              boxShadow: '0 0 20px rgba(0,229,255,0.04)',
            }}>
            <div className="absolute top-0 right-0 w-24 h-24 rounded-full opacity-5 pointer-events-none"
              style={{ background: 'radial-gradient(circle, rgba(0,229,255,1) 0%, transparent 70%)', transform: 'translate(30%, -30%)' }} />
            <p className="flex items-center gap-2 text-sm font-semibold mb-3">
              <Lightbulb className="h-4 w-4 text-accent" aria-hidden="true" />
              <span className="text-accent font-tactical tracking-wider">AI Recommendation</span>
              <Badge tone="info">Advisory Only</Badge>
            </p>
            <p className="mb-1.5 text-[10px] font-tactical font-semibold uppercase tracking-widest text-text-dim">Why This Rank</p>
            <ul className="mb-3 space-y-1.5">
              {item.explanation.map((line) => (
                <li key={line} className="flex items-start gap-2 text-xs text-text-muted">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent" />
                  {line}
                </li>
              ))}
            </ul>
            <p className="mb-1.5 text-[10px] font-tactical font-semibold uppercase tracking-widest text-text-dim">Suggested Next Steps</p>
            <ul className="space-y-1.5">
              {item.recommended_next_steps.map((line) => (
                <li key={line} className="flex items-start gap-2 text-xs text-text-primary">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-verified" />
                  {line}
                </li>
              ))}
            </ul>
          </div>

          {/* Human decision */}
          <div className="rounded-xl p-4"
            style={{
              background: 'linear-gradient(135deg, rgba(10,18,34,0.9) 0%, rgba(6,13,26,0.95) 100%)',
              border: decided ? '1px solid rgba(0,230,118,0.2)' : '1px solid rgba(0,229,255,0.08)',
            }}>
            <p className="flex items-center gap-2 text-sm font-semibold mb-3">
              <UserCheck className={`h-4 w-4 ${decided ? 'text-verified' : 'text-text-muted'}`} aria-hidden="true" />
              <span className={`font-tactical tracking-wider ${decided ? 'text-verified' : 'text-text-muted'}`}>Human Decision</span>
              <Badge tone={decided ? 'verified' : 'neutral'}>{DECISION_LABEL[decision.status] || decision.status}</Badge>
            </p>
            {decided ? (
              <div className="mb-4 rounded-lg p-3"
                style={{ background: 'rgba(0,230,118,0.05)', border: '1px solid rgba(0,230,118,0.1)' }}>
                <p className="text-xs text-text-muted">
                  Recorded by <span className="text-text-primary font-medium">{decision.decided_by || 'unknown'}</span>
                  {decision.decided_at && <> · {formatDateTime(decision.decided_at)}</>}.
                  {decision.note && <><br /><span className="italic">"{decision.note}"</span></>}
                </p>
              </div>
            ) : (
              <p className="mb-4 text-xs text-text-muted leading-relaxed">
                No decision recorded. The AI cannot dispatch anyone — a human responder must choose before any action is taken.
              </p>
            )}
            <Button
              variant={decided ? 'secondary' : 'primary'}
              size="sm"
              disabled={!canDecide}
              onClick={() => onDecide(item)}
            >
              {decided ? 'Change decision' : 'Record a decision'}
            </Button>
          </div>
        </div>
      </div>
    </div>
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
        icon={ShieldAlert}
        description="Urgency, evidence confidence and verification priority are shown separately and never combined. The ranking only sorts the list. The AI advises and a human decides."
        actions={
          <>
            <Button size="sm" variant={sort === 'urgency' ? 'primary' : 'secondary'} onClick={() => setSort('urgency')}>Sort by Urgency</Button>
            <Button size="sm" variant={sort === 'verification' ? 'primary' : 'secondary'} onClick={() => setSort('verification')}>Sort by Verify</Button>
          </>
        }
      />

      {notice && (
        <div role="status" className="mb-4 flex items-start justify-between gap-3 rounded-xl px-4 py-3 text-sm text-green-200 animate-fade-in-up"
          style={{ background: 'rgba(0,230,118,0.08)', border: '1px solid rgba(0,230,118,0.25)', boxShadow: '0 0 20px rgba(0,230,118,0.05)' }}>
          <span>{notice}</span>
          <button onClick={() => setNotice('')} className="text-xs text-text-muted hover:text-text-primary underline">Dismiss</button>
        </div>
      )}
      {!canDecide && (
        <div className="mb-4 flex items-start gap-2 rounded-xl px-4 py-3 text-sm text-text-muted animate-fade-in-up"
          style={{ background: 'rgba(0,229,255,0.04)', border: '1px solid rgba(0,229,255,0.1)' }}>
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
            setNotice(`Decision recorded for "${item.title}". This logs a human judgement and does not dispatch anyone.`)
            setDeciding(null)
            reload()
          }}
        />
      )}
    </>
  )
}
