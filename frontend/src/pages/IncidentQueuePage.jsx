import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Plus, FileSearch } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Table from '../components/ui/Table'
import Skeleton from '../components/ui/Skeleton'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import { SearchInput, Select } from '../components/ui/Input'
import ReportForm from '../components/incidents/ReportForm'
import { UrgencyBadge, ConfidenceBadge, VerificationBadge } from '../components/priority/ScoreBadge'
import useApi from '../hooks/useApi'
import useDebounce from '../hooks/useDebounce'
import { listReports } from '../services/reportService'
import { analyzeReport } from '../services/analysisService'
import { timeAgo, labelOf } from '../utils/format'
import { freshnessTone, reportStatusTone } from '../utils/tones'

const STATUS_OPTIONS = [
  { value: 'all', label: 'All statuses' },
  { value: 'pending_analysis', label: 'Pending analysis' },
  { value: 'analyzed', label: 'Analysed' },
  { value: 'needs_more_info', label: 'Needs more info' },
  { value: 'verified', label: 'Verified' },
  { value: 'rejected', label: 'Rejected' },
]
const FRESHNESS_OPTIONS = [
  { value: 'all', label: 'All freshness' },
  { value: 'recent', label: 'Recent' },
  { value: 'aging', label: 'Aging' },
  { value: 'stale', label: 'Stale' },
]
const SORT_OPTIONS = [
  { value: 'newest', label: 'Newest first' },
  { value: 'verification_priority', label: 'Verify first (highest verification priority)' },
]

export default function IncidentQueuePage() {
  const [params, setParams] = useSearchParams()
  const status = params.get('status') || 'all'
  const freshness = params.get('freshness') || 'all'
  const sort = params.get('sort') || 'newest'

  const [search, setSearch] = useState('')
  const q = useDebounce(search, 300)
  const [formOpen, setFormOpen] = useState(false)
  const [notice, setNotice] = useState('')
  const [actionError, setActionError] = useState('')
  const [analyzingId, setAnalyzingId] = useState(null)

  const { data, loading, error, reload } = useApi(
    () =>
      listReports({
        q: q || undefined,
        status: status === 'all' ? undefined : status,
        freshness: freshness === 'all' ? undefined : freshness,
        sort,
        limit: 100,
      }),
    [q, status, freshness, sort],
  )

  function setParam(key, value) {
    const next = new URLSearchParams(params)
    if (!value || value === 'all' || (key === 'sort' && value === 'newest')) next.delete(key)
    else next.set(key, value)
    setParams(next, { replace: true })
  }

  const filtersActive = Boolean(search) || status !== 'all' || freshness !== 'all' || sort !== 'newest'

  function clearFilters() {
    setSearch('')
    setParams({}, { replace: true })
  }

  async function analyze(id) {
    setAnalyzingId(id)
    setActionError('')
    try {
      await analyzeReport(id)
      setNotice(`Report ${id} analysed. Scores are AI recommendations for a human to review.`)
      reload()
    } catch (err) {
      setActionError(err.message)
    } finally {
      setAnalyzingId(null)
    }
  }

  const columns = [
    { key: 'id', header: 'Report', render: (r) => <span className="font-mono text-xs text-accent">{r.id}</span> },
    {
      key: 'text',
      header: 'What was reported',
      className: 'min-w-64',
      render: (r) => (
        <div>
          <p className="line-clamp-2">{r.text}</p>
          <p className="mt-1 text-xs text-text-muted">{r.location.label} · {r.source.name}</p>
        </div>
      ),
    },
    {
      key: 'freshness',
      header: 'Freshness',
      render: (r) =>
        r.analysis ? (
          <Badge tone={freshnessTone[r.analysis.freshness.status]}>{labelOf(r.analysis.freshness.status)}</Badge>
        ) : (
          <span className="text-text-muted">Not analysed</span>
        ),
    },
    { key: 'urgency', header: 'Urgency', render: (r) => <UrgencyBadge value={r.analysis?.scores.urgency} /> },
    { key: 'confidence', header: 'Evidence', render: (r) => <ConfidenceBadge value={r.analysis?.scores.evidence_confidence} /> },
    { key: 'verify', header: 'Verify', render: (r) => <VerificationBadge value={r.analysis?.scores.verification_priority} /> },
    { key: 'status', header: 'Status', render: (r) => <Badge tone={reportStatusTone[r.status]}>{labelOf(r.status)}</Badge> },
    { key: 'reported', header: 'Reported', render: (r) => <span className="whitespace-nowrap">{timeAgo(r.reported_at)}</span> },
    {
      key: 'actions',
      header: 'Actions',
      render: (r) => (
        <div className="flex flex-col items-start gap-1">
          {r.status === 'pending_analysis' && (
            <Button size="sm" loading={analyzingId === r.id} onClick={() => analyze(r.id)}>Analyze</Button>
          )}
          {r.incident_id && (
            <Link to={`/incidents/${r.incident_id}`} className="text-xs text-accent hover:underline">Open incident</Link>
          )}
        </div>
      ),
    },
  ]

  return (
    <>
      <PageHeader
        title="Incident Queue"
        description="All reports with their separate scores. Use “Verify first” to see which reports a human should check soonest."
        actions={<Button icon={Plus} onClick={() => setFormOpen(true)}>Submit report</Button>}
      />

      {notice && (
        <div role="status" className="mb-4 flex items-start justify-between gap-3 rounded-lg border border-verified/40 bg-verified/10 px-4 py-2 text-sm text-green-200">
          <span>{notice}</span>
          <button onClick={() => setNotice('')} className="text-xs underline">Dismiss</button>
        </div>
      )}
      {actionError && (
        <div role="alert" className="mb-4 rounded-lg border border-critical/40 bg-critical/10 px-4 py-2 text-sm text-red-300">{actionError}</div>
      )}

      <Card>
        <div className="mb-4 grid gap-3 md:grid-cols-[1fr_180px_160px_260px_auto]">
          <SearchInput value={search} onChange={setSearch} placeholder="Search text, ID, source or place…" label="Search reports" />
          <Select value={status} onChange={(v) => setParam('status', v)} options={STATUS_OPTIONS} label="Filter by status" />
          <Select value={freshness} onChange={(v) => setParam('freshness', v)} options={FRESHNESS_OPTIONS} label="Filter by freshness" />
          <Select value={sort} onChange={(v) => setParam('sort', v)} options={SORT_OPTIONS} label="Sort reports" />
          {filtersActive && <Button variant="ghost" onClick={clearFilters}>Clear</Button>}
        </div>

        {error ? (
          <ErrorState title="Could not load reports" message={error.message} onRetry={reload} />
        ) : loading && !data ? (
          <div className="space-y-2">{[1, 2, 3, 4, 5].map((n) => <Skeleton key={n} className="h-12" />)}</div>
        ) : data.items.length === 0 ? (
          <EmptyState
            icon={FileSearch}
            title="No reports match"
            description="Try a different search or clear the filters."
            action={filtersActive && <Button variant="secondary" onClick={clearFilters}>Clear filters</Button>}
          />
        ) : (
          <div className={loading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
            <p className="mb-2 text-xs text-text-muted">{data.total} report(s)</p>
            <Table columns={columns} rows={data.items} rowKey={(r) => r.id} caption="Reports" />
          </div>
        )}
      </Card>

      <ReportForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onCreated={(report) => {
          setNotice(`Report ${report.id} submitted with status “${labelOf(report.status)}”. Press Analyze to run analysis.`)
          reload()
        }}
      />
    </>
  )
}