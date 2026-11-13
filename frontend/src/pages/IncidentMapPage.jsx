import { Component, Fragment, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { MapContainer, TileLayer, CircleMarker, Circle, Popup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { Activity, AlertTriangle, ChevronLeft, ChevronRight, MapPin, Pause, Play } from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import Card, { CardHeader } from '../components/ui/Card'
import StatCard from '../components/ui/StatCard'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Skeleton from '../components/ui/Skeleton'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import { SearchInput, Select } from '../components/ui/Input'
import useApi from '../hooks/useApi'
import { listIncidents } from '../services/incidentService'
import { formatDateTime, timeAgo, labelOf } from '../utils/format'
import { severityTone } from '../utils/tones'
import { cn } from '../utils/cn'

const SEVERITY_COLOR = { low: '#94a3b8', medium: '#22d3ee', high: '#f97316', critical: '#ef4444' }
const SEVERITIES = Object.keys(SEVERITY_COLOR)
const STATUSES = ['active', 'monitoring', 'resolved']
const SEVERITY_OPTIONS = [{ value: 'all', label: 'All severities' }, ...SEVERITIES.slice().reverse().map((v) => ({ value: v, label: labelOf(v) }))]
const STATUS_OPTIONS = [{ value: 'all', label: 'All statuses' }, ...STATUSES.map((v) => ({ value: v, label: labelOf(v) }))]
const PLAY_INTERVAL_MS = 1200
const FALLBACK_CENTER = [12.95, 77.67]

const isNum = (v) => typeof v === 'number' && Number.isFinite(v)
const validTime = (t) => typeof t === 'string' && !Number.isNaN(Date.parse(t))

// ---------- Data normalising: the page must not crash on imperfect backend data ----------
function normalizeIncident(raw) {
  const lat = raw?.location?.lat
  const lng = raw?.location?.lng
  const hasCoords = isNum(lat) && isNum(lng) && Math.abs(lat) <= 90 && Math.abs(lng) <= 180
  const severity = SEVERITIES.includes(raw.severity) ? raw.severity : 'low'
  const status = STATUSES.includes(raw.status) ? raw.status : 'active'

  let timeline = (Array.isArray(raw.timeline) ? raw.timeline : [])
    .filter((t) => t && validTime(t.timestamp))
    .map((t) => ({
      timestamp: t.timestamp,
      ms: Date.parse(t.timestamp),
      severity: SEVERITIES.includes(t.severity) ? t.severity : severity,
      status: STATUSES.includes(t.status) ? t.status : status,
      report_count: isNum(t.report_count) ? t.report_count : raw.report_count ?? 0,
      affected_radius_m: isNum(t.affected_radius_m) ? t.affected_radius_m : 100,
      summary: typeof t.summary === 'string' ? t.summary : '',
    }))
    .sort((a, b) => a.ms - b.ms)

  const synthesized = timeline.length === 0
  if (synthesized) {
    const when = [raw.last_updated_at, raw.first_reported_at].find(validTime) || new Date().toISOString()
    timeline = [{
      timestamp: when,
      ms: Date.parse(when),
      severity,
      status,
      report_count: raw.report_count ?? 0,
      affected_radius_m: 100,
      summary: 'Latest known state (no history recorded yet)',
    }]
  }

  return {
    ...raw,
    id: String(raw.id),
    title: raw.title || 'Untitled incident',
    type: raw.type || 'other',
    severity,
    status,
    hasCoords,
    synthesized,
    location: { lat: hasCoords ? lat : null, lng: hasCoords ? lng : null, label: raw?.location?.label || 'Unknown location' },
    timeline,
  }
}

function buildSteps(incidents) {
  const set = new Set()
  incidents.forEach((i) => i.timeline.forEach((t) => set.add(t.ms)))
  return [...set].sort((a, b) => a - b)
}

function stateAt(incident, ms) {
  let current = null
  for (const entry of incident.timeline) {
    if (entry.ms <= ms) current = entry
    else break
  }
  return current
}

// ---------- Map pieces ----------
class MapBoundary extends Component {
  state = { failed: false }
  static getDerivedStateFromError() {
    return { failed: true }
  }
  componentDidCatch(err) {
    console.error('Incident map failed to render', err)
  }
  render() {
    if (this.state.failed) return this.props.fallback
    return this.props.children
  }
}

function FitAll({ points }) {
  const map = useMap()
  const key = JSON.stringify(points)
  useEffect(() => {
    if (points.length === 0) return
    if (points.length === 1) map.setView(points[0], 14)
    else map.fitBounds(points, { padding: [50, 50] })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, map])
  return null
}

function Focus({ lat, lng }) {
  const map = useMap()
  useEffect(() => {
    if (isNum(lat) && isNum(lng)) map.flyTo([lat, lng], 14, { duration: 0.8 })
  }, [lat, lng, map])
  return null
}

function LiveMap({ allPoints, markers, selectedId, selectedLocation, onSelect }) {
  return (
    <div
      role="region"
      aria-label="Map of incidents. The list beside the map has the same information."
      className="dark-tiles relative isolate h-[520px] overflow-hidden rounded-xl border border-navy-700"
    >
      <MapContainer center={FALLBACK_CENTER} zoom={11} className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitAll points={allPoints} />
        <Focus lat={selectedLocation?.lat} lng={selectedLocation?.lng} />
        {markers.map(({ incident, state }) => {
          const color = SEVERITY_COLOR[state.severity]
          const selected = incident.id === selectedId
          const center = [incident.location.lat, incident.location.lng]
          return (
            <Fragment key={incident.id}>
              <Circle
                center={center}
                radius={state.affected_radius_m}
                pathOptions={{ color, weight: 1, dashArray: '4 4', fillColor: color, fillOpacity: 0.12, interactive: false }}
              />
              <CircleMarker
                center={center}
                radius={selected ? 13 : 9}
                pathOptions={{ color: selected ? '#ffffff' : color, weight: selected ? 3 : 1.5, fillColor: color, fillOpacity: 0.9 }}
                eventHandlers={{ click: () => onSelect(incident.id) }}
              >
                <Popup>
                  <div className="space-y-1 text-sm">
                    <div className="font-semibold">{incident.title}</div>
                    <div>{labelOf(state.severity)} · {labelOf(state.status)} · {state.report_count} report(s)</div>
                    <div>Affected radius about {state.affected_radius_m} m</div>
                    {state.summary && <div>{state.summary}</div>}
                    <div className="text-xs opacity-80">{formatDateTime(state.ms)}</div>
                    <Link to={`/incidents/${incident.id}`}>Open incident details</Link>
                  </div>
                </Popup>
              </CircleMarker>
            </Fragment>
          )
        })}
      </MapContainer>
    </div>
  )
}

function MapFallback() {
  return (
    <EmptyState
      icon={MapPin}
      title="The map could not be displayed"
      description="This is usually a network problem loading map tiles. The incident list and timeline still work."
    />
  )
}

// ---------- Page ----------
export default function IncidentMapPage() {
  const [params, setParams] = useSearchParams()
  const selectedId = params.get('incident') || ''
  const [severity, setSeverity] = useState('all')
  const [status, setStatus] = useState('all')
  const [search, setSearch] = useState('')
  const [step, setStep] = useState(null) // null means "latest"
  const [playing, setPlaying] = useState(false)

  const { data, loading, error, reload } = useApi(() => listIncidents(), [])

  const incidents = useMemo(() => {
    const items = Array.isArray(data?.items) ? data.items : []
    return items.filter((i) => i && i.id != null).map(normalizeIncident)
  }, [data])
  const steps = useMemo(() => buildSteps(incidents), [incidents])
  const last = steps.length - 1
  const current = last < 0 ? 0 : step === null ? last : Math.min(step, last)
  const time = steps[current]

  const rows = useMemo(
    () => incidents.map((incident) => ({ incident, state: time === undefined ? null : stateAt(incident, time) })),
    [incidents, time],
  )

  useEffect(() => {
    if (!playing) return undefined
    const id = setInterval(() => {
      setStep((prev) => Math.min((prev === null ? last : prev) + 1, last))
    }, PLAY_INTERVAL_MS)
    return () => clearInterval(id)
  }, [playing, last])

  useEffect(() => {
    if (playing && current >= last) setPlaying(false)
  }, [playing, current, last])

  function togglePlay() {
    if (playing) {
      setPlaying(false)
      return
    }
    if (current >= last) setStep(0)
    setPlaying(true)
  }

  function select(id) {
    setParams(id && id !== selectedId ? { incident: id } : {}, { replace: true })
  }

  function clearFilters() {
    setSeverity('all')
    setStatus('all')
    setSearch('')
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
        <div className="mb-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[1, 2, 3, 4].map((n) => <Skeleton key={n} className="h-24" />)}
        </div>
        <Skeleton className="h-[520px]" />
      </>
    )
  }

  if (incidents.length === 0) {
    return (
      <>
        <PageHeader title="Incident Map" />
        <EmptyState
          icon={MapPin}
          title="No incidents to show"
          description="Incidents appear here once reports have been analysed and grouped."
          action={<Button variant="secondary" onClick={reload}>Refresh</Button>}
        />
      </>
    )
  }

  const q = search.trim().toLowerCase()
  const matches = (r) =>
    r.state &&
    (severity === 'all' || r.state.severity === severity) &&
    (status === 'all' || r.state.status === status) &&
    (!q || `${r.incident.id} ${r.incident.title} ${r.incident.type} ${r.incident.location.label}`.toLowerCase().includes(q))

  const listed = rows.filter(matches)
  const onMap = listed.filter((r) => r.incident.hasCoords)
  const notYetReported = rows.filter((r) => !r.state).length
  const noCoords = incidents.filter((i) => !i.hasCoords).length
  const filtersActive = severity !== 'all' || status !== 'all' || Boolean(search)
  const selected = rows.find((r) => r.incident.id === selectedId) || null
  const changedNow = rows.filter((r) => r.state && r.state.ms === time)
  const anySynthesized = incidents.some((i) => i.synthesized)
  const allPoints = incidents.filter((i) => i.hasCoords).map((i) => [i.location.lat, i.location.lng])

  return (
    <>
      <PageHeader
        title="Incident Map"
        description="See where incidents are and how they changed over time. Marker colour shows severity and the dashed circle shows the estimated affected area. Locations and severity are AI estimates for humans to check."
        actions={<Button size="sm" variant="secondary" onClick={reload}>Refresh</Button>}
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Incidents at this time" value={listed.length} icon={MapPin} hint={filtersActive ? 'After filters' : 'All reported so far'} />
        <StatCard label="Critical" value={listed.filter((r) => r.state.severity === 'critical').length} icon={AlertTriangle} tone="critical" />
        <StatCard label="Active" value={listed.filter((r) => r.state.status === 'active').length} icon={Activity} tone="verify" />
        <StatCard label="Without map location" value={noCoords} hint="Listed but not drawn" tone={noCoords ? 'verify' : 'info'} />
      </div>

      <Card className="mt-6">
        <div className="grid gap-3 md:grid-cols-[1fr_200px_200px_auto]">
          <SearchInput value={search} onChange={setSearch} placeholder="Search title, place, type or ID…" label="Search incidents" />
          <Select value={severity} onChange={setSeverity} options={SEVERITY_OPTIONS} label="Filter by severity at this time" />
          <Select value={status} onChange={setStatus} options={STATUS_OPTIONS} label="Filter by status at this time" />
          {filtersActive && <Button variant="ghost" onClick={clearFilters}>Clear</Button>}
        </div>
      </Card>

      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_380px]">
        <div className="min-w-0 space-y-4">
          <MapBoundary fallback={<MapFallback />}>
            <LiveMap
              allPoints={allPoints}
              markers={onMap}
              selectedId={selectedId}
              selectedLocation={selected?.incident.location}
              onSelect={select}
            />
          </MapBoundary>

          <ul className="flex flex-wrap gap-4 text-xs text-text-muted" aria-label="Map legend">
            {SEVERITIES.map((key) => (
              <li key={key} className="flex items-center gap-1">
                <span className="inline-block h-3 w-3 rounded-full" style={{ background: SEVERITY_COLOR[key] }} aria-hidden="true" />
                {labelOf(key)}
              </li>
            ))}
            <li>Dashed circle: estimated affected radius</li>
          </ul>

          <Card>
            <CardHeader
              title="Incident evolution"
              subtitle="Move the slider or press Play to replay how reports, severity and affected area changed."
              action={<Badge tone="info">Step {current + 1} of {steps.length}</Badge>}
            />
            <p className="mb-3 text-sm">
              Showing the situation at <span className="font-medium text-accent">{formatDateTime(time)}</span>{' '}
              <span className="text-text-muted">({timeAgo(time)})</span>
            </p>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="secondary" icon={playing ? Pause : Play} onClick={togglePlay} disabled={steps.length < 2}>
                {playing ? 'Pause' : 'Play'}
              </Button>
              <Button size="sm" variant="ghost" icon={ChevronLeft} aria-label="Previous step" disabled={current <= 0} onClick={() => { setPlaying(false); setStep(current - 1) }} />
              <input
                type="range"
                min={0}
                max={Math.max(last, 0)}
                step={1}
                value={current}
                disabled={steps.length < 2}
                onChange={(e) => { setPlaying(false); setStep(Number(e.target.value)) }}
                aria-label="Time step"
                aria-valuetext={formatDateTime(time)}
                className="h-2 w-full cursor-pointer accent-accent disabled:cursor-not-allowed"
              />
              <Button size="sm" variant="ghost" icon={ChevronRight} aria-label="Next step" disabled={current >= last} onClick={() => { setPlaying(false); setStep(current + 1) }} />
              <Button size="sm" variant="secondary" disabled={current >= last} onClick={() => { setPlaying(false); setStep(null) }}>Latest</Button>
            </div>
            <div className="mt-1 flex justify-between text-xs text-text-muted">
              <span>{formatDateTime(steps[0])}</span>
              <span>{formatDateTime(steps[last])}</span>
            </div>
            {anySynthesized && (
              <p className="mt-3 text-xs text-text-muted">Some incidents have no recorded history yet, so only their latest known state is shown.</p>
            )}
          </Card>

          <Card>
            <CardHeader title="What changed at this step" />
            {changedNow.length === 0 ? (
              <p className="text-sm text-text-muted">No incident was updated at this moment.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {changedNow.map(({ incident, state }) => (
                  <li key={incident.id} className="rounded-md bg-navy-900 px-3 py-2">
                    <span className="font-medium">{incident.title}</span>
                    {state.summary ? `: ${state.summary}` : ` is now ${labelOf(state.severity)} (${labelOf(state.status)})`}
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
              <div className="text-sm text-text-muted">
                <p>No incidents match the current filters at this time.</p>
                {filtersActive && <Button className="mt-2" size="sm" variant="secondary" onClick={clearFilters}>Clear filters</Button>}
              </div>
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
                        )}
                      >
                        <span className="block text-sm font-medium">{incident.title}</span>
                        <span className="block text-xs text-text-muted">{incident.location.label}</span>
                        <span className="mt-2 flex flex-wrap gap-2">
                          <Badge tone={severityTone[state.severity]}>{labelOf(state.severity)}</Badge>
                          <Badge>{labelOf(state.status)}</Badge>
                          <Badge tone="neutral">{state.report_count} report(s)</Badge>
                          {!incident.hasCoords && <Badge tone="verify">No map location</Badge>}
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
            {notYetReported > 0 && (
              <p className="mt-3 text-xs text-text-muted">{notYetReported} incident(s) had not been reported yet at this time.</p>
            )}
          </Card>

          {selected && (
            <Card>
              <CardHeader
                title={selected.incident.title}
                subtitle={`${labelOf(selected.incident.type)} · ${selected.incident.location.label}`}
                action={<Button size="sm" variant="ghost" onClick={() => select('')}>Close</Button>}
              />
              <div className="mb-3 flex flex-wrap gap-2">
                <Badge tone={severityTone[selected.incident.severity]}>Now: {labelOf(selected.incident.severity)}</Badge>
                <Badge tone="info">{labelOf(selected.incident.status)}</Badge>
                {selected.incident.independent_source_count !== undefined && (
                  <Badge tone="neutral">{selected.incident.independent_source_count} independent source(s)</Badge>
                )}
              </div>
              <dl className="mb-4 grid grid-cols-2 gap-2 text-xs">
                <div><dt className="text-text-muted">Reports</dt><dd>{selected.incident.report_count ?? '—'}</dd></div>
                <div>
                  <dt className="text-text-muted">Coordinates</dt>
                  <dd className="font-mono">
                    {selected.incident.hasCoords ? `${selected.incident.location.lat}, ${selected.incident.location.lng}` : 'Not available'}
                  </dd>
                </div>
                <div>
                  <dt className="text-text-muted">First reported</dt>
                  <dd>{validTime(selected.incident.first_reported_at) ? timeAgo(selected.incident.first_reported_at) : '—'}</dd>
                </div>
                <div>
                  <dt className="text-text-muted">Last updated</dt>
                  <dd>{validTime(selected.incident.last_updated_at) ? timeAgo(selected.incident.last_updated_at) : '—'}</dd>
                </div>
              </dl>

              <h3 className="mb-2 text-sm font-medium">Timeline</h3>
              <ol className="space-y-3 border-l border-navy-600 pl-4">
                {selected.incident.timeline.map((entry) => {
                  const past = entry.ms <= time
                  const shown = selected.state?.ms === entry.ms
                  return (
                    <li key={entry.ms} className={cn('relative', !past && 'opacity-40')}>
                      <span
                        className={cn('absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full', shown ? 'bg-accent ring-2 ring-accent/40' : 'bg-navy-600')}
                        aria-hidden="true"
                      />
                      <p className="text-xs text-text-muted">
                        {formatDateTime(entry.ms)} {shown && <Badge tone="info">Shown on map</Badge>} {!past && <span>(later)</span>}
                      </p>
                      {entry.summary && <p className="text-sm">{entry.summary}</p>}
                      <div className="mt-1 flex flex-wrap gap-2">
                        <Badge tone={severityTone[entry.severity]}>{labelOf(entry.severity)}</Badge>
                        <Badge tone="neutral">{entry.report_count} report(s)</Badge>
                        <Badge tone="neutral">{entry.affected_radius_m} m</Badge>
                      </div>
                    </li>
                  )
                })}
              </ol>

              <div className="mt-4 flex flex-wrap gap-4 text-sm">
                <Link to={`/incidents/${selected.incident.id}`} className="text-accent hover:underline">Details</Link>
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