import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Activity, AlertTriangle, ShieldQuestion, Clock } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import Card, { CardHeader } from '../components/ui/Card'
import StatCard from '../components/ui/StatCard'
import Button from '../components/ui/Button'
import Table from '../components/ui/Table'
import Skeleton from '../components/ui/Skeleton'
import ErrorState from '../components/ui/ErrorState'
import FreshnessChart from '../components/dashboard/FreshnessChart'
import PriorityScoresChart from '../components/dashboard/PriorityScoresChart'
import { UrgencyBadge, ConfidenceBadge, VerificationBadge } from '../components/priority/ScoreBadge'
import useApi from '../hooks/useApi'
import { listIncidents } from '../services/incidentService'
import { listReports } from '../services/reportService'
import { getPriority } from '../services/analysisService'

const kpiLink = 'block rounded-xl transition-opacity hover:opacity-90'

export default function OverviewPage() {
  const [sort, setSort] = useState('urgency')
  const base = useApi(() => Promise.all([listIncidents(), listReports({ limit: 100 })]), [])
  const priority = useApi(() => getPriority(sort), [sort])

  if (base.error) {
    return (
      <>
        <PageHeader title="Overview" />
        <ErrorState title="Could not load the dashboard" message={base.error.message} onRetry={base.reload} />
      </>
    )
  }

  const incidents = base.data?.[0].items ?? []
  const reports = base.data?.[1].items ?? []

  const active = incidents.filter((i) => i.status === 'active').length
  const critical = incidents.filter((i) => i.severity === 'critical').length
  const needVerification = reports.filter(
    (r) => r.analysis?.scores.verification_priority.level === 'high' && !['verified', 'rejected'].includes(r.status),
  ).length
  const stale = reports.filter((r) => r.analysis?.freshness.status === 'stale').length

  const columns = [
    { key: 'rank', header: '#', render: (row) => <span className="font-mono">{row.rank}</span> },
    {
      key: 'title',
      header: 'Incident',
      render: (row) => (
        <Link to={`/incidents/${row.incident_id}`} className="font-medium text-accent hover:underline">
          {row.title}
        </Link>
      ),
    },
    { key: 'urgency', header: 'Urgency', render: (row) => <UrgencyBadge value={row.urgency} /> },
    { key: 'confidence', header: 'Evidence confidence', render: (row) => <ConfidenceBadge value={row.evidence_confidence} /> },
    { key: 'verification', header: 'Verification priority', render: (row) => <VerificationBadge value={row.verification_priority} /> },
    { key: 'next', header: 'Suggested next step', render: (row) => <span className="text-text-muted">{row.recommended_next_steps[0]}</span> },
  ]

  return (
    <>
      <PageHeader
        title="Overview"
        description="Situation summary. AI output is advisory: urgency, evidence confidence and verification priority are shown separately, and humans make every dispatch decision."
      />

      {base.loading && !base.data ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((n) => <Skeleton key={n} className="h-28" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Link to="/map" className={kpiLink}>
            <StatCard label="Active incidents" value={active} icon={Activity} hint="Open the incident map" />
          </Link>
          <Link to="/priority" className={kpiLink}>
            <StatCard label="Critical incidents" value={critical} icon={AlertTriangle} tone="critical" hint="Open rescue priority" />
          </Link>
          <Link to="/incidents?sort=verification_priority" className={kpiLink}>
            <StatCard label="Reports to verify first" value={needVerification} icon={ShieldQuestion} tone="verify" hint="High verification priority" />
          </Link>
          <Link to="/incidents?freshness=stale" className={kpiLink}>
            <StatCard label="Stale reports" value={stale} icon={Clock} hint="Older than 4 hours" />
          </Link>
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Report freshness" subtitle="How recent the analysed reports are." />
          {base.loading && !base.data ? <Skeleton className="h-56" /> : <FreshnessChart reports={reports} />}
        </Card>
        <Card>
          <CardHeader title="Three separate scores" subtitle="Per incident. Never combined." />
          {priority.loading && !priority.data ? <Skeleton className="h-72" /> : priority.error ? (
            <ErrorState message={priority.error.message} onRetry={priority.reload} />
          ) : (
            <PriorityScoresChart items={priority.data?.items ?? []} />
          )}
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader
          title="Incident ranking (recommendation only)"
          subtitle="Changing the sort changes the order, not the scores."
          action={
            <div className="flex gap-2">
              <Button size="sm" variant={sort === 'urgency' ? 'primary' : 'secondary'} onClick={() => setSort('urgency')}>By urgency</Button>
              <Button size="sm" variant={sort === 'verification' ? 'primary' : 'secondary'} onClick={() => setSort('verification')}>Verify first</Button>
            </div>
          }
        />
        {priority.loading && !priority.data ? (
          <div className="space-y-2">{[1, 2, 3].map((n) => <Skeleton key={n} className="h-10" />)}</div>
        ) : priority.error ? (
          <ErrorState message={priority.error.message} onRetry={priority.reload} />
        ) : (
          <Table columns={columns} rows={priority.data.items} rowKey={(row) => row.incident_id} caption="Incident ranking" />
        )}
      </Card>
    </>
  )
}