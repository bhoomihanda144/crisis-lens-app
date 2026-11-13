import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { BadgeCheck, ShieldQuestion, Clock, Ban, FileSearch } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import StatCard from '../components/ui/StatCard'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Table from '../components/ui/Table'
import Skeleton from '../components/ui/Skeleton'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import { SearchInput, Select } from '../components/ui/Input'
import { UrgencyBadge, ConfidenceBadge, VerificationBadge } from '../components/priority/ScoreBadge'
import VerifyModal from '../components/verification/VerifyModal'
import useApi from '../hooks/useApi'
import useDebounce from '../hooks/useDebounce'
import { listReports } from '../services/reportService'
import { timeAgo, labelOf } from '../utils/format'
import { freshnessTone, reportStatusTone } from '../utils/tones'

const VIEWS = [
  { value: 'awaiting', label: 'Awaiting decision' },
  { value: 'needs_more_info', label: 'Needs more info' },
  { value: 'decided', label: 'Decided' },
  { value: 'all', label: 'All reports' },
]

function inView(view, status) {
  if (view === 'all') return true
  if (view === 'awaiting') return status === 'pending_analysis' || status === 'analyzed'
  if (view === 'needs_more_info') return status === 'needs_more_info'
  return status === 'verified' || status === 'rejected'
}

export default function VerificationPage() {
  const [params, setParams] = useSearchParams()
  const view = params.get('view') || 'awaiting'
  const incident = params.get('incident') || ''
  const openId = params.get('report') || ''

  const [search, setSearch] = useState('')
  const q = useDebounce(search, 300)
  const [notice, setNotice] = useState('')

  const { data, loading, error, reload } = useApi(
    () => listReports({ q: q || undefined, incident_id: incident || undefined, sort: 'verification_priority', limit: 100 }),
    [q, incident],
  )

  function setParam(key, value) {
    const next = new URLSearchParams(params)
    if (!value || (key === 'view' && value === 'awaiting')) next.delete(key)
    else next.set(key, value)
    setParams(next, { replace: true })
  }

  const items = data?.items ?? []
  const count = (statuses) => items.filter((r) => statuses.includes(r.status)).length
  const rows = items.filter((r) => inView(view, r.status))
  const selected = items.find((r) => r.id === openId) || null

  const columns = [
    { key: 'id', header: 'Report', render: (r) => <span className="font-mono text-xs text-accent">{r.id}</span> },
    {
      key: 'text',
      header: 'What was reported',
      className: 'min-w-64',
      render: (r) => (
        <div>
          <p className="line-clamp-2">{r.text}</p>
          <p className="mt-1 text-xs text-text-muted">{r.location.label} · {r.source.name} · {timeAgo(r.reported_at)}</p>
        </div>
      ),
    },
    { key: 'verify', header: 'Verification priority', render: (r) => <VerificationBadge value={r.analysis?.scores.verification_priority} /> },
    { key: 'urgency', header: 'Urgency', render: (r) => <UrgencyBadge value={r.analysis?.scores.urgency} /> },
    { key: 'evidence', header: 'Evidence', render: (r) => <ConfidenceBadge value={r.analysis?.scores.evidence_confidence} /> },
    {
      key: 'flags',
      header: 'Flags',
      render: (r) => (
        <div className="flex flex-col items-start gap-1">
          {r.analysis && <Badge tone={freshnessTone[r.analysis.freshness.status]}>{labelOf(r.analysis.freshness.status)}</Badge>}
          {r.analysis?.conflicts.length > 0 && <Badge tone="critical">Conflict</Badge>}
          {r.analysis?.source_verification.independence === 'forwarded' && <Badge tone="verify">Forwarded</Badge>}
        </div>
      ),
    },
    { key: 'status', header: 'Status', render: (r) => <Badge tone={reportStatusTone[r.status]}>{labelOf(r.status)}</Badge> },
    {
      key: 'actions',
      header: 'Actions',
      render: (r) => (
        <div className="flex flex-col items-start gap-1">
          <Button size="sm" variant={inView('decided', r.status) ? 'secondary' : 'primary'} onClick={() => setParam('report', r.id)}>
            {inView('decided', r.status) ? 'Change decision' : 'Review'}
          </Button>
          <Link to={`/analysis?report=${r.id}`} className="text-xs text-accent hover:underline">See analysis</Link>
        </div>
      ),
    },
  ]

  return (
    <>
      <PageHeader
        title="Verification Centre"
        description="Reports are listed with the highest verification priority first. A human confirms, rejects or asks for more information. Verification records a decision about the report and never dispatches anyone."
      />

      {notice && (
        <div role="status" className="mb-4 flex items-start justify-between gap-3 rounded-lg border border-verified/40 bg-verified/10 px-4 py-2 text-sm text-green-200">
          <span>{notice}</span>
          <button onClick={() => setNotice('')} className="text-xs underline">Dismiss</button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Awaiting decision" value={count(['pending_analysis', 'analyzed'])} icon={ShieldQuestion} tone="verify" />
        <StatCard label="Needs more info" value={count(['needs_more_info'])} icon={Clock} />
        <StatCard label="Verified" value={count(['verified'])} icon={BadgeCheck} tone="verified" />
        <StatCard label="Rejected" value={count(['rejected'])} icon={Ban} tone="critical" />
      </div>

      <Card className="mt-6">
        {incident && (
          <p className="mb-3 text-sm">
            Showing incident <span className="font-mono text-accent">{incident}</span> only.{' '}
            <button onClick={() => setParam('incident', '')} className="text-accent underline">Show all</button>
          </p>
        )}
        <div className="mb-4 grid gap-3 md:grid-cols-[1fr_220px]">
          <SearchInput value={search} onChange={setSearch} placeholder="Search text, ID, source or place…" label="Search reports" />
          <Select value={view} onChange={(v) => setParam('view', v)} options={VIEWS} label="Choose a view" />
        </div>

        {error ? (
          <ErrorState title="Could not load reports" message={error.message} onRetry={reload} />
        ) : loading && !data ? (
          <div className="space-y-2">{[1, 2, 3, 4].map((n) => <Skeleton key={n} className="h-14" />)}</div>
        ) : rows.length === 0 ? (
          <EmptyState icon={FileSearch} title="Nothing here" description="No reports match this view and search." />
        ) : (
          <div className={loading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
            <Table columns={columns} rows={rows} rowKey={(r) => r.id} caption="Verification queue" />
          </div>
        )}
      </Card>

      {selected && (
        <VerifyModal
          key={selected.id}
          report={selected}
          onClose={() => setParam('report', '')}
          onSaved={(updated) => {
            setNotice(`Report ${updated.id} marked “${labelOf(updated.status)}”. This records a decision about the report, not a dispatch.`)
            setParam('report', '')
            reload()
          }}
        />
      )}
    </>
  )
}