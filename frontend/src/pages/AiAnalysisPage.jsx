import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Cpu, RefreshCw, UserCheck } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import Card, { CardHeader } from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Tabs from '../components/ui/Tabs'
import Skeleton from '../components/ui/Skeleton'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import { Select } from '../components/ui/Input'
import { ScoreTriple } from '../components/priority/ScoreBadge'
import DuplicatePanel from '../components/analysis/DuplicatePanel'
import SourcePanel from '../components/analysis/SourcePanel'
import FreshnessPanel from '../components/analysis/FreshnessPanel'
import ConflictPanel from '../components/analysis/ConflictPanel'
import useApi from '../hooks/useApi'
import { listReports, getReport } from '../services/reportService'
import { analyzeReport } from '../services/analysisService'
import { timeAgo, labelOf } from '../utils/format'
import { reportStatusTone, recommendationTone } from '../utils/tones'

export default function AiAnalysisPage() {
  const [params, setParams] = useSearchParams()
  const [tab, setTab] = useState('duplicates')
  const [analyzing, setAnalyzing] = useState(false)
  const [actionError, setActionError] = useState('')

  const list = useApi(() => listReports({ limit: 100 }), [])
  const reports = list.data?.items ?? []
  const reportsById = Object.fromEntries(reports.map((r) => [r.id, r]))
  const selectedId = params.get('report') || reports[0]?.id || null

  const detail = useApi(() => (selectedId ? getReport(selectedId) : Promise.resolve(null)), [selectedId])
  const report = detail.data

  async function analyze() {
    setAnalyzing(true)
    setActionError('')
    try {
      await analyzeReport(selectedId)
      detail.reload()
      list.reload()
    } catch (err) {
      setActionError(err.message)
    } finally {
      setAnalyzing(false)
    }
  }

  const options = reports.map((r) => ({
    value: r.id,
    label: `${r.id} — ${r.text.length > 55 ? `${r.text.slice(0, 55)}…` : r.text}`,
  }))

  if (list.error) {
    return (
      <>
        <PageHeader title="AI Analysis" />
        <ErrorState title="Could not load reports" message={list.error.message} onRetry={list.reload} />
      </>
    )
  }

  const analysis = report?.analysis
  const tabs = analysis
    ? [
        { id: 'duplicates', label: 'Duplicates', count: analysis.duplicate.matches.length },
        { id: 'sources', label: 'Independent sources', count: analysis.source_verification.related.length },
        { id: 'freshness', label: 'Freshness' },
        { id: 'conflicts', label: 'Conflicts', count: analysis.conflicts.length },
      ]
    : []

  return (
    <>
      <PageHeader
        title="AI Analysis"
        description="Choose a report to see how the system judged duplicates, source independence, freshness and conflicts. These are recommendations for a human to check."
      />

      <Card className="mb-6">
        {list.loading && !list.data ? (
          <Skeleton className="h-10" />
        ) : reports.length === 0 ? (
          <p className="text-sm text-text-muted">There are no reports yet. Submit one from the Incident Queue.</p>
        ) : (
          <div className="grid gap-3 md:grid-cols-[1fr_auto]">
            <Select
              value={selectedId || ''}
              onChange={(v) => setParams({ report: v }, { replace: true })}
              options={options}
              label="Choose a report"
            />
            <Button
              icon={analysis ? RefreshCw : Cpu}
              variant={analysis ? 'secondary' : 'primary'}
              loading={analyzing}
              onClick={analyze}
              disabled={!selectedId}
            >
              {analysis ? 'Re-run analysis' : 'Run analysis'}
            </Button>
          </div>
        )}
        {actionError && <p role="alert" className="mt-3 rounded-lg border border-critical/40 bg-critical/10 px-3 py-2 text-sm text-red-300">{actionError}</p>}
      </Card>

      {detail.error ? (
        <ErrorState
          title={detail.error.code === 'not_found' ? 'Report not found' : 'Could not load this report'}
          message={detail.error.message}
          onRetry={detail.error.code === 'not_found' ? undefined : detail.reload}
        />
      ) : detail.loading && !report ? (
        <>
          <Skeleton className="mb-4 h-28" />
          <Skeleton className="h-64" />
        </>
      ) : report ? (
        <>
          <Card>
            <CardHeader
              title={<span className="font-mono text-accent">{report.id}</span>}
              subtitle={`${report.source.name} (${labelOf(report.source.type)}) · ${report.location.label} · reported ${timeAgo(report.reported_at)}`}
              action={<Badge tone={reportStatusTone[report.status]}>{labelOf(report.status)}</Badge>}
            />
            <p className="text-sm">{report.text}</p>
            <div className="mt-3 flex flex-wrap gap-4 text-sm">
              {report.incident_id && <Link to={`/incidents/${report.incident_id}`} className="text-accent hover:underline">Open incident {report.incident_id}</Link>}
              {report.incident_id && <Link to={`/graph/${report.incident_id}`} className="text-accent hover:underline">Evidence graph</Link>}
              <Link to={`/verification?report=${report.id}`} className="text-accent hover:underline">Verify this report</Link>
            </div>
          </Card>

          {!analysis ? (
            <div className="mt-6">
              <EmptyState
                icon={Cpu}
                title="This report has not been analysed"
                description="Run the analysis to see duplicates, source independence, freshness, conflicts and the three separate scores."
                action={<Button loading={analyzing} onClick={analyze}>Run analysis</Button>}
              />
            </div>
          ) : (
            <>
              <h2 className="mb-2 mt-6 text-base font-semibold">Scores</h2>
              <ScoreTriple
                urgency={analysis.scores.urgency}
                evidenceConfidence={analysis.scores.evidence_confidence}
                verificationPriority={analysis.scores.verification_priority}
              />

              <Card className="mt-4 border-accent/30">
                <CardHeader
                  title="AI recommendation"
                  subtitle="Advice for a human responder. This is not a dispatch decision."
                  action={<Badge tone={recommendationTone[analysis.recommendation.type]}>{labelOf(analysis.recommendation.type)}</Badge>}
                />
                <p className="text-sm">{analysis.recommendation.summary}</p>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-text-muted">
                  {analysis.recommendation.next_steps.map((step) => <li key={step}>{step}</li>)}
                </ul>
                <p className="mt-3 flex items-center gap-2 text-xs text-text-muted">
                  <UserCheck className="h-4 w-4 text-accent" aria-hidden="true" />
                  A human must decide what happens next.
                </p>
              </Card>

              <Card className="mt-6">
                <Tabs tabs={tabs} value={tab} onChange={setTab} label="Analysis sections" />
                {tab === 'duplicates' && <DuplicatePanel report={report} reportsById={reportsById} />}
                {tab === 'sources' && <SourcePanel report={report} reportsById={reportsById} />}
                {tab === 'freshness' && <FreshnessPanel report={report} />}
                {tab === 'conflicts' && <ConflictPanel report={report} reportsById={reportsById} />}
              </Card>

              <p className="mt-3 text-xs text-text-muted">
                Analysed {timeAgo(analysis.analyzed_at)} · engine {analysis.engine_version}
                {/mock|simulated/i.test(analysis.engine_version) && <Badge tone="verify" className="ml-2">SIMULATED</Badge>}
              </p>
            </>
          )}
        </>
      ) : null}
    </>
  )
}