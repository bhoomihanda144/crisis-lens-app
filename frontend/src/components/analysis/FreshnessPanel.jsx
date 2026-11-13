import Badge from '../ui/Badge'
import { formatDateTime, formatMinutes, timeAgo, labelOf } from '../../utils/format'
import { freshnessTone } from '../../utils/tones'

const BAR_COLOR = { recent: 'bg-accent', aging: 'bg-verify', stale: 'bg-slate-500' }

export default function FreshnessPanel({ report }) {
  const { freshness, analyzed_at } = report.analysis
  const percent = Math.min(100, (freshness.age_minutes / 240) * 100)

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg bg-navy-900 p-3">
          <p className="text-xs text-text-muted">Status</p>
          <div className="mt-1"><Badge tone={freshnessTone[freshness.status]}>{labelOf(freshness.status)}</Badge></div>
        </div>
        <div className="rounded-lg bg-navy-900 p-3">
          <p className="text-xs text-text-muted">Report timestamp</p>
          <p className="mt-1 text-sm">{formatDateTime(report.reported_at)}</p>
          <p className="text-xs text-text-muted">{timeAgo(report.reported_at)}</p>
        </div>
        <div className="rounded-lg bg-navy-900 p-3">
          <p className="text-xs text-text-muted">Age when analysed</p>
          <p className="mt-1 text-sm">{formatMinutes(freshness.age_minutes)}</p>
          <p className="text-xs text-text-muted">Analysed {timeAgo(analyzed_at)}</p>
        </div>
        <div className="rounded-lg bg-navy-900 p-3">
          <p className="text-xs text-text-muted">Last update to this information</p>
          <p className="mt-1 text-sm">{formatDateTime(freshness.last_updated)}</p>
        </div>
      </div>

      <div>
        <p className="mb-2 text-sm font-medium">Age against the freshness limits</p>
        <div className="relative h-3 rounded bg-navy-700" role="img" aria-label={`Report age ${formatMinutes(freshness.age_minutes)} of 240 minutes`}>
          <div className={`h-full rounded ${BAR_COLOR[freshness.status]}`} style={{ width: `${percent}%` }} />
          <span className="absolute top-0 h-3 w-px bg-slate-300" style={{ left: '25%' }} aria-hidden="true" />
        </div>
        <div className="relative mt-1 h-4 text-xs text-text-muted">
          <span className="absolute left-0">0</span>
          <span className="absolute -translate-x-1/2" style={{ left: '25%' }}>60 min</span>
          <span className="absolute right-0">240 min and older</span>
        </div>
        <p className="mt-3 text-xs text-text-muted">
          Recent: up to 60 minutes. Aging: 61 to 240 minutes. Stale: over 240 minutes. Age was measured when the analysis ran, so re-run the analysis to refresh it.
        </p>
      </div>
    </div>
  )
}