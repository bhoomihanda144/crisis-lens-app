import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { MapPin } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import Card, { CardHeader } from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import Skeleton from '../components/ui/Skeleton'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import { Select } from '../components/ui/Input'
import IncidentMap from '../components/map/IncidentMap'
import TimelineControls from '../components/map/TimelineControls'
import { buildSteps, stateAt, SEVERITY_COLOR } from '../components/map/timelineUtils'
import useApi from '../hooks/useApi'
import { listIncidents } from '../services/incidentService'
import { formatDateTime, labelOf } from '../utils/format'
import { severityTone } from '../utils/tones'
import { cn } from '../utils/cn'

const SEVERITY_OPTIONS = [
  { value: 'all', label: 'All severities' },
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
]

export default function IncidentMapPage() {
  const [params, setParams] = useSearchParams()
  const selectedId = params.get('incident') || ''
  const [severity, setSeverity] = useState('all')
  const [step, setStep] = useState(null) // null means "latest"
  const [playing, setPlaying] = useState(false)

  const { data, loading, error, reload } = useApi(() => listIncidents(), [])
  const incidents = useMemo(() => data?.items ?? [], [data])
  const steps = useMemo(() => buildSteps(incidents), [incidents])
  const last = steps.length - 1
  const current = last < 0 ? 0 : step === null ? last : Math.min(step, last)
  const time = steps[current]

  useEffect(() => {
    if (!playing) return undefined
    const id = setInterval(() => {
      setStep((prev) => {
        const next = (prev === null ? last : prev) + 1
        if (next >= last) {
          setPlaying(false)
          return last
        }
        return next
      })
    }, 1200)
    return () => clearInterval(id)
  }, [playing, last])

  function togglePlay() {
    if (playing) return setPlaying(false)
    if (current >= last) setStep(0)
    return setPlaying(true)
  }

  function select(id) {
    setParams(id && id !== selectedId ? { incident: id } : {}, { replace: true })
  }

  if (error) {
    return (
      <>
        <PageHeader title="Incident Map" />
        <ErrorState title="Could not load incidents" message={error.message} onRetry={reload} />
      </>
    )
  }

  if (loading && !data) {
    return (
      <>
        <PageHeader title="Incident Map" />
        <Skeleton className="h-[520px]" />
      </>
    )
  }

  if (incidents.length === 0 || steps.length === 0) {
    return (
      <>
        <PageHeader title="Incident Map" />
        <EmptyState icon={MapPin} title="No incidents to show" description="Incidents appear here once reports have been analysed and grouped." />
      </>
    )
  }

  const rows = incidents.map((incident) => ({ incident, state: stateAt(incident, time) }))
  const visible = rows.filter((r) => r.state && (severity === 'all' || r.state.severity === severity))
  const listed = rows.filter((r) => (r.state ? visible.includes(r) : severity === 'all'))
  const selected = rows.find((r) => r.incident.id === selectedId) || null
  const changedNow = rows.filter((r) => r.state && r.state.timestamp === time)

  return (
    <>
      <PageHeader
        title="Incident Map"
        description="See where incidents are and how they changed over time. Marker colour shows severity, and the dashed circle shows the estimated affected area. Locations and severity are AI estimates for humans to check."
      />

      <div className="mb-4 max-w-xs">
        <Select value={severity} onChange={setSeverity} options={SEVERITY_OPTIONS} label="Filter by severity at this time" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="min-w-0 space-y-4">
          <IncidentMap
            allPoints={incidents.map((i) => [i.location.lat, i.location.lng])}
            markers={visible}
            selectedId={selectedId}
            onSelect={select}
            focusLocation={selected?.incident.location}
          />
          <ul className="flex flex-wrap gap-4 text-xs text-text-muted" aria-label="Map legend">
            {Object.entries(SEVERITY_COLOR).map(([key, color]) => (
              <li key={key} className="flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded-full" style={{ background: color }} aria-hidden="true" />
                {labelOf(key)}
              </li>
            ))}
            <li>Dashed circle: estimated affected radius</li>
          </ul>

          <TimelineControls steps={steps} current={current} onChange={setStep} playing={playing} onTogglePlay={togglePlay} />

          <Card>
            <CardHeader title="What changed at this step" />
            {changedNow.length === 0 ? (
              <p className="text-sm text-text-muted">No incident was updated at this moment.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {changedNow.map(({ incident, state }) => (
                  <li key={incident.id} className="rounded-md bg-navy-900 px-3 py-2">
                    <span className="font-medium">{incident.title}</span>: {state.summary}
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader title="Incidents at this time" subtitle="Select one to focus the map." />
            {listed.length === 0 ? (
              <p className="text-sm text-text-muted">No incidents match this severity at this time.</p>
            ) : (
              <ul className="space-y-2">
                {listed.map(({ incident, state }) => {
                  const isSelected = incident.id === selectedId
                  return (
                    <li key={incident.id}>
                      <button
                        type="button"
                        aria-pressed={isSelected}
                        onClick={() => select(incident.id)}
                        className={cn(
                          'w-full rounded-lg border p-3 text-left transition-colors',
                          isSelected ? 'border-accent bg-accent/5' : 'border-navy-600 hover:bg-navy-700/50',
                          !state && 'opacity-50',
                        )}
                      >
                        <span className="block text-sm font-medium">{incident.title}</span>
                        {state ? (
                          <span className="mt-1 flex flex-wrap gap-2">
                            <Badge tone={severityTone[state.severity]}>{labelOf(state.severity)}</Badge>
                            <Badge>{labelOf(state.status)}</Badge>
                            <Badge tone="neutral">{state.report_count} report(s)</Badge>
                            <Badge tone="neutral">{state.affected_radius_m} m</Badge>
                          </span>
                        ) : (
                          <span className="mt-1 block text-xs text-text-muted">Not reported yet at this time.</span>
                        )}
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </Card>

          {selected && (
            <Card>
              <CardHeader
                title="Selected incident timeline"
                subtitle={selected.incident.title}
                action={<Link to={`/incidents/${selected.incident.id}`} className="text-sm text-accent hover:underline">Details</Link>}
              />
              <ol className="space-y-3 border-l border-navy-600 pl-4">
                {selected.incident.timeline.map((entry) => {
                  const past = Date.parse(entry.timestamp) <= Date.parse(time)
                  const isShown = selected.state?.timestamp === entry.timestamp
                  return (
                    <li key={entry.timestamp} className={cn('relative', !past && 'opacity-40')}>
                      <span
                        className={cn('absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full', isShown ? 'bg-accent ring-2 ring-accent/40' : 'bg-navy-600')}
                        aria-hidden="true"
                      />
                      <p className="text-xs text-text-muted">
                        {formatDateTime(entry.timestamp)} {isShown && <Badge tone="info">Shown on map</Badge>} {!past && <span>(later)</span>}
                      </p>
                      <p className="text-sm">{entry.summary}</p>
                      <div className="mt-1 flex flex-wrap gap-2">
                        <Badge tone={severityTone[entry.severity]}>{labelOf(entry.severity)}</Badge>
                        <Badge tone="neutral">{entry.report_count} report(s)</Badge>
                        <Badge tone="neutral">{entry.affected_radius_m} m</Badge>
                      </div>
                    </li>
                  )
                })}
              </ol>
              <div className="mt-4 flex gap-4 text-sm">
                <Link to={`/graph/${selected.incident.id}`} className="text-accent hover:underline">Evidence graph</Link>
                <Link to={`/verification?incident=${selected.incident.id}`} className="text-accent hover:underline">Verification</Link>
              </div>
            </Card>
          )}
        </div>
      </div>
    </>
  )
}