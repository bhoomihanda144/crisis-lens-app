import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, FlaskConical, RotateCcw, X } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import PageHeader from '../components/ui/PageHeader'
import Card, { CardHeader } from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import EmptyState from '../components/ui/EmptyState'
import { runSimulation } from '../services/simulationService'
import { cn } from '../utils/cn'
import { formatDateTime } from '../utils/format'

const MAX_SCENARIOS = 4

const FIELDS = [
  { key: 'affected_population', label: 'Affected population', min: 0, max: 10000000, hint: 'People in the affected area' },
  { key: 'rescue_teams', label: 'Rescue teams available', min: 0, max: 1000, hint: 'Teams ready to deploy' },
  { key: 'blocked_roads', label: 'Blocked roads', min: 0, max: 200, hint: 'Roads that responders cannot use' },
  { key: 'available_ambulances', label: 'Ambulances available', min: 0, max: 1000, hint: 'Ambulances ready to deploy' },
]

const SEVERITY_TEXT = { 1: 'Minor', 2: 'Moderate', 3: 'Serious', 4: 'Severe', 5: 'Catastrophic' }

const PRESETS = [
  { label: 'Moderate flood, roads open', values: { scenario_name: 'Moderate flood, roads open', affected_population: 5000, disaster_severity: 2, rescue_teams: 4, blocked_roads: 0, available_ambulances: 4 } },
  { label: 'Heavy rain, 3 roads blocked', values: { scenario_name: 'Heavy rain, 3 roads blocked', affected_population: 10000, disaster_severity: 3, rescue_teams: 2, blocked_roads: 3, available_ambulances: 3 } },
  { label: 'Major earthquake', values: { scenario_name: 'Major earthquake', affected_population: 50000, disaster_severity: 5, rescue_teams: 10, blocked_roads: 5, available_ambulances: 10 } },
]

const input = 'mt-1 w-full rounded-lg border bg-navy-900 px-3 py-2 text-sm'
const toForm = (values) => Object.fromEntries(Object.entries(values).map(([k, v]) => [k, String(v)]))
const toNum = (v) => (typeof v === 'number' && Number.isFinite(v) ? v : 0)
const isNum = (v) => typeof v === 'number' && Number.isFinite(v)
const fmt = (n) => toNum(n).toLocaleString('en-IN')
const short = (text) => (text.length > 18 ? `${text.slice(0, 18)}…` : text)

// Turns whatever the backend returns into a safe, flat shape for the page.
function normalizeScenario(response, payload, key) {
  const inputs = { ...payload, ...(response?.inputs && typeof response.inputs === 'object' ? response.inputs : {}) }
  const results = response?.results && typeof response.results === 'object' ? response.results : {}
  const demand = results.resource_demand && typeof results.resource_demand === 'object' ? results.resource_demand : {}
  const shortages = Array.isArray(results.shortages) ? results.shortages : null

  function resource(name, required, available) {
    const req = toNum(required)
    const avail = toNum(available)
    const reported = shortages?.find((s) => s?.resource === name)
    const shortfall = reported ? toNum(reported.shortfall) : shortages ? 0 : Math.max(0, req - avail)
    return { required: req, available: avail, shortfall }
  }

  return {
    key,
    name: inputs.scenario_name || 'Untitled scenario',
    inputs,
    teams: resource('rescue_teams', demand.rescue_teams, inputs.rescue_teams),
    ambulances: resource('ambulances', demand.ambulances, inputs.available_ambulances),
    delay: isNum(results.estimated_response_delay_minutes) ? results.estimated_response_delay_minutes : null,
    changes: (Array.isArray(results.priority_changes) ? results.priority_changes : []).filter((c) => c && c.incident_id),
    summary: typeof results.summary === 'string' ? results.summary : '',
    generatedAt: response?.generated_at || null,
  }
}

function ResourceRow({ label, data }) {
  const pct = data.required > 0 ? Math.min(100, Math.round((data.available / data.required) * 100)) : 100
  const short_ = data.shortfall > 0
  return (
    <tr>
      <td className="px-4 py-3">{label}</td>
      <td className="px-4 py-3 font-mono">{fmt(data.required)}</td>
      <td className="px-4 py-3 font-mono">{fmt(data.available)}</td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="h-2 w-24 overflow-hidden rounded bg-navy-700" role="img" aria-label={`${pct}% of the required amount is available`}>
            <div className={cn('h-full', short_ ? 'bg-critical' : 'bg-verified')} style={{ width: `${pct}%` }} />
          </div>
          <span className="font-mono text-xs">{pct}%</span>
        </div>
      </td>
      <td className="px-4 py-3">
        {short_ ? <Badge tone="critical">Short by {fmt(data.shortfall)}</Badge> : <Badge tone="verified">Covered</Badge>}
      </td>
    </tr>
  )
}


function Building({ x, y, scale = 1, tone = 'slate', flooded = false, label }) {
  const palettes = {
    slate: ['#334155', '#1e293b', '#475569'],
    blue: ['#1d4ed8', '#1e40af', '#3b82f6'],
    amber: ['#b45309', '#92400e', '#d97706'],
  }
  const [front, side, roof] = palettes[tone]
  return (
    <g transform={`translate(${x} ${y}) scale(${scale})`}>
      <polygon points="0,0 34,-18 68,0 34,19" fill={roof} stroke="#94a3b8" strokeOpacity=".45" />
      <polygon points="0,0 34,19 34,72 0,53" fill={front} stroke="#94a3b8" strokeOpacity=".25" />
      <polygon points="34,19 68,0 68,53 34,72" fill={side} stroke="#94a3b8" strokeOpacity=".25" />
      {[0, 1, 2].map((i) => (
        <g key={i}>
          <polygon points={`${8 + i * 8},${10 + i * 0} ${16 + i * 8},${6 + i * 0} ${16 + i * 8},${17 + i * 0} ${8 + i * 8},${21 + i * 0}`} fill={flooded ? '#fbbf24' : '#7dd3fc'} opacity=".9" />
          <polygon points={`${42 + i * 7},${17 - i * 4} ${49 + i * 7},${13 - i * 4} ${49 + i * 7},${24 - i * 4} ${42 + i * 7},${28 - i * 4}`} fill={flooded ? '#fbbf24' : '#7dd3fc'} opacity=".85" />
        </g>
      ))}
      {flooded && <path d="M-2 48 Q10 43 22 48 T46 48 T70 48" fill="none" stroke="#67e8f9" strokeWidth="3" />}
      {label && <text x="34" y="-27" textAnchor="middle" fill="#dbeafe" fontSize="10" fontWeight="600">{label}</text>}
    </g>
  )
}

function FloodTerrain({ scenario }) {
  const [level, setLevel] = useState(Math.max(18, scenario.inputs.disaster_severity * 16))
  const [playing, setPlaying] = useState(false)
  const severity = Number(scenario.inputs.disaster_severity) || 1
  const affected = Number(scenario.inputs.affected_population) || 0
  const roadImpact = Math.min(8, Math.max(0, Math.round((level - 30) / 9)))
  const waterTop = 340 - level * 1.35
  const risk = level >= 76 ? 'CRITICAL' : level >= 55 ? 'HIGH' : level >= 32 ? 'MODERATE' : 'LOW'

  useEffect(() => {
    if (!playing) return undefined
    const timer = window.setInterval(() => {
      setLevel((v) => {
        if (v >= 100) {
          setPlaying(false)
          return 100
        }
        return Math.min(100, v + 2)
      })
    }, 90)
    return () => window.clearInterval(timer)
  }, [playing])

  useEffect(() => {
    setLevel(Math.max(18, severity * 16))
    setPlaying(false)
  }, [scenario.key, severity])

  return (
    <Card className="overflow-hidden border-cyan-400/20">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-400" />
            <p className="text-xs font-semibold uppercase tracking-[.18em] text-cyan-300">Live what-if environment</p>
          </div>
          <h3 className="mt-1 text-lg font-semibold text-white">Bellandur flood-zone · 3D tactical view</h3>
          <p className="mt-1 text-xs text-slate-400">Illustrative terrain model · not a live geographic or hydrological feed</p>
        </div>
        <Badge tone={risk === 'CRITICAL' ? 'critical' : risk === 'HIGH' ? 'critical' : 'verify'}>{risk} RISK</Badge>
      </div>

      <div className="relative mt-4 overflow-hidden rounded-xl border border-slate-700 bg-[#071426]">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_50%_15%,rgba(14,165,233,.18),transparent_60%)]" />
        <div className="absolute left-3 top-3 z-10 rounded-md border border-white/10 bg-slate-950/75 px-3 py-2 backdrop-blur">
          <p className="text-[10px] uppercase tracking-widest text-slate-400">Water level index</p>
          <p className="font-mono text-2xl font-bold text-cyan-300">{level}<span className="text-xs text-slate-400"> / 100</span></p>
        </div>
        <div className="absolute right-3 top-3 z-10 rounded-md border border-white/10 bg-slate-950/75 px-3 py-2 text-right backdrop-blur">
          <p className="text-[10px] uppercase tracking-widest text-slate-400">Forecast horizon</p>
          <p className="font-mono text-lg font-semibold text-white">+{Math.round(level * .6)} min</p>
        </div>

        <svg viewBox="0 0 900 500" role="img" aria-label={`Isometric flood scenario at water level ${level} out of 100`} className="block w-full">
          <defs>
            <linearGradient id="terrain" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#29465a" /><stop offset="1" stopColor="#142b3c" />
            </linearGradient>
            <linearGradient id="flood" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#67e8f9" stopOpacity=".82" /><stop offset="1" stopColor="#0369a1" stopOpacity=".88" />
            </linearGradient>
            <pattern id="terrainGrid" width="36" height="36" patternUnits="userSpaceOnUse" patternTransform="skewY(-26)">
              <path d="M36 0H0V36" fill="none" stroke="#8bb4c8" strokeOpacity=".12" strokeWidth="1" />
            </pattern>
            <filter id="glow"><feGaussianBlur stdDeviation="5" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          </defs>
          <path d="M80 160 L500 35 L835 170 L420 455 Z" fill="url(#terrain)" stroke="#5d8498" strokeWidth="2" />
          <path d="M80 160 L500 35 L835 170 L420 455 Z" fill="url(#terrainGrid)" />
          <path d="M100 330 L500 205 L800 320" fill="none" stroke="#94a3b8" strokeWidth="30" strokeOpacity=".28" />
          <path d="M100 330 L500 205 L800 320" fill="none" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="14 10" strokeOpacity=".65" />
          <path d="M210 125 L400 260 L670 365" fill="none" stroke="#94a3b8" strokeWidth="20" strokeOpacity=".25" />
          <path d="M210 125 L400 260 L670 365" fill="none" stroke="#cbd5e1" strokeWidth="2" strokeDasharray="12 9" strokeOpacity=".6" />
          <path d="M145 250 Q260 180 360 230 T580 265 T790 230" fill="none" stroke="#0e7490" strokeWidth="72" strokeOpacity=".55" />
          <path d={`M145 ${Math.max(160, waterTop - 22)} Q260 ${Math.max(115, waterTop - 65)} 360 ${Math.max(160, waterTop - 18)} T580 ${Math.max(185, waterTop + 8)} T790 ${Math.max(160, waterTop - 20)} L790 320 Q580 355 360 300 T145 320 Z`} fill="url(#flood)" opacity={Math.min(.95, .25 + level / 130)} />
          <path d={`M145 ${Math.max(160, waterTop - 22)} Q260 ${Math.max(115, waterTop - 65)} 360 ${Math.max(160, waterTop - 18)} T580 ${Math.max(185, waterTop + 8)} T790 ${Math.max(160, waterTop - 20)}`} fill="none" stroke="#a5f3fc" strokeWidth="3" filter="url(#glow)" />
          <g opacity=".85" stroke="#cffafe" strokeWidth="2" fill="none">
            {[0,1,2,3,4].map(i => <path key={i} d={`M${180+i*112} ${250+Math.sin(i)*20} q22 -9 44 0`} opacity={.25 + (i%2)*.25} />)}
          </g>

          <Building x={155} y={175} scale={1.05} tone="blue" label="SECTOR 01" flooded={level > 55} />
          <Building x={300} y={105} scale={.9} tone="slate" label="RESIDENTIAL" flooded={level > 72} />
          <Building x={455} y={125} scale={1.15} tone="amber" label="HOSPITAL" flooded={level > 82} />
          <Building x={625} y={190} scale={.95} tone="blue" label="SECTOR 03" flooded={level > 45} />
          <Building x={720} y={285} scale={.78} tone="slate" flooded={level > 62} />
          <Building x={365} y={300} scale={.82} tone="amber" flooded={level > 65} />

          <g>
            <path d="M510 210 L565 192 L603 207 L548 225 Z" fill="#64748b" stroke="#cbd5e1" strokeWidth="2" />
            <path d="M548 225 L603 207 L603 220 L548 238 Z" fill="#334155" />
            <path d="M510 210 L548 225 L548 238 L510 223 Z" fill="#475569" />
            <path d="M520 210 L575 193" stroke="#fbbf24" strokeWidth="3" strokeDasharray="6 4" />
            {level > 48 && <path d="M505 232 Q550 220 610 238" stroke="#fb7185" strokeWidth="5" fill="none" strokeDasharray="7 5" />}
            <text x="555" y="178" textAnchor="middle" fill={level > 48 ? '#fda4af' : '#fde68a'} fontSize="12" fontWeight="bold">BRIDGE {level > 48 ? 'AT RISK' : 'OPEN'}</text>
          </g>

          <g transform="translate(245 300)">
            <circle r="17" fill="#052e2b" stroke="#34d399" strokeWidth="2" />
            <path d="M-9 2 L0 -7 L9 2 L6 2 L6 9 L-6 9 L-6 2Z" fill="#6ee7b7" />
            <text x="0" y="32" fill="#a7f3d0" textAnchor="middle" fontSize="11">RESCUE BASE</text>
          </g>
          <g transform="translate(690 110)">
            <circle r="16" fill="#451a03" stroke="#fb923c" strokeWidth="2" />
            <path d="M-8 0 L0 -8 L8 0 L0 8Z" fill="#fdba74" />
            <text x="0" y="29" fill="#fed7aa" textAnchor="middle" fontSize="11">SHELTER</text>
          </g>

          {level > 38 && <g>
            <path d="M245 300 Q360 275 440 270 T620 245" fill="none" stroke="#fbbf24" strokeWidth="4" strokeDasharray="9 7" />
            <text x="440" y="290" fill="#fde68a" fontSize="12" fontWeight="bold">ALTERNATE RESCUE ROUTE</text>
          </g>}
          {level > 58 && <g>
            <path d="M100 330 L500 205 L800 320" fill="none" stroke="#fb7185" strokeWidth="8" strokeOpacity=".85" strokeDasharray="16 10" />
            <rect x="455" y="340" width="190" height="28" rx="6" fill="#7f1d1d" stroke="#fb7185" />
            <text x="550" y="359" fill="#fff1f2" textAnchor="middle" fontSize="12" fontWeight="bold">ROAD ACCESS CUT OFF</text>
          </g>}
          <text x="450" y="480" fill="#94a3b8" textAnchor="middle" fontSize="11" letterSpacing="2">ISOMETRIC TERRAIN · FLOOD EXTENT PREVIEW</text>
        </svg>
      </div>

      <div className="mt-4 rounded-xl border border-slate-700 bg-slate-900/70 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-white">Storm intensity control</p>
            <p className="text-xs text-slate-400">Move the slider to raise or lower the simulated flood plane</p>
          </div>
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => { setLevel(18); setPlaying(false) }}>Reset</Button>
            <Button size="sm" onClick={() => setPlaying(v => !v)}>{playing ? 'Pause forecast' : level >= 100 ? 'Replay forecast' : '▶ Play forecast'}</Button>
          </div>
        </div>
        <input aria-label="Simulated flood level" type="range" min="10" max="100" value={level} onChange={(e) => { setLevel(Number(e.target.value)); setPlaying(false) }} className="mt-4 w-full accent-cyan-400" />
        <div className="flex justify-between text-[10px] uppercase tracking-wider text-slate-500"><span>Low water</span><span>Road flooding</span><span>Severe inundation</span></div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
        <div className="rounded-lg border border-slate-700 bg-slate-900 p-3"><p className="text-[10px] uppercase text-slate-400">People in zone</p><p className="mt-1 text-xl font-bold text-white">{fmt(affected)}</p></div>
        <div className="rounded-lg border border-slate-700 bg-slate-900 p-3"><p className="text-[10px] uppercase text-slate-400">Road segments at risk</p><p className="mt-1 text-xl font-bold text-amber-300">{roadImpact}</p></div>
        <div className="rounded-lg border border-slate-700 bg-slate-900 p-3"><p className="text-[10px] uppercase text-slate-400">Bridge status</p><p className={`mt-1 text-sm font-bold ${level > 48 ? 'text-rose-300' : 'text-emerald-300'}`}>{level > 48 ? 'ACCESS AT RISK' : 'PASSABLE'}</p></div>
        <div className="rounded-lg border border-slate-700 bg-slate-900 p-3"><p className="text-[10px] uppercase text-slate-400">Simulation mode</p><p className="mt-1 text-sm font-bold text-cyan-300">ISOLATED · TRUE</p></div>
      </div>
      <p className="mt-3 text-[11px] leading-relaxed text-slate-500">Demo note: this is a visual, illustrative scenario model. Water level, road impacts and forecast time are presentation estimates—not validated flood predictions. No live dispatch or incident data is changed.</p>
    </Card>
  )
}

function ResultPanel({ scenario }) {
  const anyShort = scenario.teams.shortfall > 0 || scenario.ambulances.shortfall > 0
  return (
    <div className="space-y-5">
      <FloodTerrain scenario={scenario} />
      <Card className="border-accent/30">
        <CardHeader
          title={scenario.name}
          subtitle={scenario.generatedAt ? `Generated ${formatDateTime(scenario.generatedAt)}` : 'Latest result'}
          action={<Badge tone="verify">SIMULATION</Badge>}
        />
        <div role="status" className={cn('mb-4 rounded-lg border px-4 py-3 text-sm', anyShort ? 'border-critical/40 bg-critical/10 text-red-200' : 'border-verified/40 bg-verified/10 text-green-200')}>
          {scenario.summary || (anyShort ? 'Some resources fall short in this scenario.' : 'Available resources cover the estimated demand.')}
        </div>
        <div className="overflow-x-auto rounded-xl border border-navy-700">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Resources required compared with resources available</caption>
            <thead className="bg-navy-900 text-xs uppercase tracking-wide text-text-muted">
              <tr>{['Resource', 'Required', 'Available', 'Coverage', 'Status'].map((h) => <th key={h} scope="col" className="px-4 py-2 font-medium">{h}</th>)}</tr>
            </thead>
            <tbody className="divide-y divide-navy-700 bg-navy-800">
              <ResourceRow label="Rescue teams" data={scenario.teams} />
              <ResourceRow label="Ambulances" data={scenario.ambulances} />
            </tbody>
          </table>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg bg-navy-900 p-3"><p className="text-xs text-text-muted">Estimated response delay</p><p className="mt-1 text-2xl font-bold text-accent">{scenario.delay === null ? '—' : `${scenario.delay} min`}</p></div>
          <div className="rounded-lg bg-navy-900 p-3"><p className="text-xs text-text-muted">Disaster severity</p><p className="mt-1 text-2xl font-bold">{scenario.inputs.disaster_severity}<span className="text-sm text-text-muted"> / 5</span></p></div>
          <div className="rounded-lg bg-navy-900 p-3"><p className="text-xs text-text-muted">Blocked roads</p><p className="mt-1 text-2xl font-bold">{fmt(scenario.inputs.blocked_roads)}</p></div>
        </div>
        <h3 className="mb-2 mt-5 text-sm font-medium">Changed priorities</h3>
        {scenario.changes.length === 0 ? <p className="text-sm text-text-muted">No real incident changes rank in this scenario.</p> : (
          <ul className="space-y-2 text-sm">{scenario.changes.map((c) => (
            <li key={c.incident_id} className="rounded-md bg-navy-900 px-3 py-2">
              <Link to={`/incidents/${c.incident_id}`} className="font-medium text-accent hover:underline">{c.title || c.incident_id}</Link>
              <span className="ml-2 inline-flex items-center gap-1 font-mono text-xs">rank {c.baseline_rank ?? '?'} <ArrowRight className="h-3 w-3" aria-hidden="true" /> {c.scenario_rank ?? '?'}</span>
              {c.reason && <span className="block text-xs text-text-muted">{c.reason}</span>}
            </li>
          ))}</ul>
        )}
        <p className="mt-4 text-xs text-text-muted">This is a what-if estimate. Real incident scores are unchanged, nobody is dispatched, and a human decides how to use these results.</p>
      </Card>
    </div>
  )
}

function Comparison({ scenarios, activeKey, onView, onRemove, onClear }) {
  const rows = [
    { label: 'Affected population', cell: (s) => fmt(s.inputs.affected_population) },
    { label: 'Disaster severity', cell: (s) => `${s.inputs.disaster_severity} of 5` },
    { label: 'Blocked roads', cell: (s) => fmt(s.inputs.blocked_roads) },
    { label: 'Teams (required / available)', cell: (s) => `${fmt(s.teams.required)} / ${fmt(s.teams.available)}` },
    { label: 'Ambulances (required / available)', cell: (s) => `${fmt(s.ambulances.required)} / ${fmt(s.ambulances.available)}` },
    {
      label: 'Shortages',
      cell: (s) =>
        s.teams.shortfall === 0 && s.ambulances.shortfall === 0 ? (
          <Badge tone="verified">None</Badge>
        ) : (
          <div className="flex flex-col items-start gap-1">
            {s.teams.shortfall > 0 && <Badge tone="critical">Teams short by {fmt(s.teams.shortfall)}</Badge>}
            {s.ambulances.shortfall > 0 && <Badge tone="critical">Ambulances short by {fmt(s.ambulances.shortfall)}</Badge>}
          </div>
        ),
    },
    { label: 'Response delay', cell: (s) => (s.delay === null ? '—' : `${s.delay} min`) },
    {
      label: 'Changed priorities',
      cell: (s) =>
        s.changes.length === 0 ? (
          <span className="text-text-muted">None</span>
        ) : (
          <ul className="space-y-1">
            {s.changes.map((c) => (
              <li key={c.incident_id} className="text-xs">{c.title || c.incident_id}: rank {c.baseline_rank ?? '?'} → {c.scenario_rank ?? '?'}</li>
            ))}
          </ul>
        ),
    },
  ]

  const chartData = scenarios.map((s) => ({
    name: short(s.name),
    'Teams required': s.teams.required,
    'Teams available': s.teams.available,
    'Ambulances required': s.ambulances.required,
    'Ambulances available': s.ambulances.available,
  }))

  return (
    <Card>
      <CardHeader
        title="Scenario comparison"
        subtitle={scenarios.length < 2 ? 'Run a second scenario to compare it with this one.' : `Up to ${MAX_SCENARIOS} scenarios side by side. The newest replaces the oldest.`}
        action={<Button size="sm" variant="ghost" onClick={onClear}>Clear all</Button>}
      />
      <div className="overflow-x-auto rounded-xl border border-navy-700">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Comparison of simulated scenarios</caption>
          <thead className="bg-navy-900 text-xs text-text-muted">
            <tr>
              <th scope="col" className="px-4 py-3 font-medium uppercase tracking-wide">Measure</th>
              {scenarios.map((s) => (
                <th key={s.key} scope="col" className={cn('min-w-44 px-4 py-3 font-medium', s.key === activeKey && 'bg-accent/5')}>
                  <div className="flex items-start justify-between gap-2">
                    <button type="button" onClick={() => onView(s.key)} className="text-left text-sm text-text-primary hover:text-accent">
                      {s.name}
                      {s.key === activeKey && <span className="ml-1 text-xs text-accent">(shown)</span>}
                    </button>
                    <button
                      type="button"
                      onClick={() => onRemove(s.key)}
                      aria-label={`Remove ${s.name}`}
                      className="rounded p-0.5 text-text-muted hover:bg-navy-700 hover:text-text-primary"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-navy-700 bg-navy-800">
            {rows.map((row) => (
              <tr key={row.label}>
                <th scope="row" className="px-4 py-3 text-left font-normal text-text-muted">{row.label}</th>
                {scenarios.map((s) => <td key={s.key} className="px-4 py-3 align-top">{row.cell(s)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="mb-2 mt-6 text-sm font-medium">Resources required against available</h3>
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid stroke="#223660" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} stroke="#223660" />
            <YAxis allowDecimals={false} tick={{ fill: '#94a3b8', fontSize: 12 }} stroke="#223660" />
            <Tooltip cursor={{ fill: 'rgba(148,163,184,0.08)' }} contentStyle={{ background: '#0f1b33', border: '1px solid #223660', borderRadius: 8 }} labelStyle={{ color: '#e6edf8' }} />
            <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
            <Bar dataKey="Teams required" fill="#f97316" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Teams available" fill="#22d3ee" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Ambulances required" fill="#ef4444" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Ambulances available" fill="#3b82f6" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

export default function SimulationPage() {
  const [form, setForm] = useState(() => toForm(PRESETS[0].values))
  const [errors, setErrors] = useState({})
  const [running, setRunning] = useState(false)
  const [runError, setRunError] = useState('')
  const [notice, setNotice] = useState('')
  const [scenarios, setScenarios] = useState([])
  const [activeKey, setActiveKey] = useState(null)
  const nextKey = useRef(1)

  const set = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  function validate() {
    const found = {}
    const payload = { scenario_name: form.scenario_name.trim() || 'Untitled scenario' }
    FIELDS.forEach((f) => {
      const text = form[f.key].trim()
      if (!/^\d+$/.test(text)) found[f.key] = 'Enter a whole number, 0 or more.'
      else if (Number(text) < f.min || Number(text) > f.max) found[f.key] = `Must be from ${f.min.toLocaleString('en-IN')} to ${f.max.toLocaleString('en-IN')}.`
      else payload[f.key] = Number(text)
    })
    const severity = Number(form.disaster_severity)
    if (!Number.isInteger(severity) || severity < 1 || severity > 5) found.disaster_severity = 'Severity must be 1 to 5.'
    else payload.disaster_severity = severity
    return { payload, found }
  }

  async function run() {
    if (running) return
    const { payload, found } = validate()
    setErrors(found)
    if (Object.keys(found).length > 0) return

    setRunning(true)
    setRunError('')
    setNotice('')
    try {
      const response = await runSimulation(payload)
      const scenario = normalizeScenario(response, payload, `s${nextKey.current}`)
      nextKey.current += 1
      const dropsOldest = scenarios.length >= MAX_SCENARIOS
      setScenarios((prev) => [...prev, scenario].slice(-MAX_SCENARIOS))
      setActiveKey(scenario.key)
      if (dropsOldest) setNotice(`You already had ${MAX_SCENARIOS} scenarios, so the oldest was removed from the comparison.`)
    } catch (err) {
      setRunError(err?.message || 'The simulation could not be run.')
    } finally {
      setRunning(false)
    }
  }

  function removeScenario(key) {
    const remaining = scenarios.filter((s) => s.key !== key)
    setScenarios(remaining)
    if (activeKey === key) setActiveKey(remaining[remaining.length - 1]?.key ?? null)
  }

  function reset() {
    setForm(toForm(PRESETS[0].values))
    setErrors({})
    setRunError('')
  }

  const active = scenarios.find((s) => s.key === activeKey) || scenarios[scenarios.length - 1] || null

  return (
    <>
      <PageHeader
        title="What-if Simulation Centre"
        description="Explore an illustrative 3D flood scenario, test resource readiness, and see how rising water can threaten roads and rescue access. Estimates only—no live dispatch."
        actions={<Badge tone="verify">Hypothetical only</Badge>}
      />

      <div className="grid gap-6 lg:grid-cols-[420px_1fr]">
        <Card>
          <CardHeader
            title="Scenario controls"
            subtitle="Describe a disaster and your available resources."
            action={<Button size="sm" variant="ghost" icon={RotateCcw} onClick={reset}>Reset</Button>}
          />

          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-text-muted">Start from an example</p>
          <div className="mb-5 flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <Button key={p.label} size="sm" variant="secondary" onClick={() => { setForm(toForm(p.values)); setErrors({}) }}>
                {p.label}
              </Button>
            ))}
          </div>

          <div className="space-y-4">
            <label className="block text-sm">
              Scenario title
              <input
                value={form.scenario_name}
                onChange={(e) => set('scenario_name', e.target.value)}
                maxLength={80}
                className={cn(input, 'border-navy-600')}
                placeholder="For example: Cyclone, coastal ward"
              />
            </label>

            <label className="block text-sm">
              Disaster severity:{' '}
              <span className="font-medium text-accent">{form.disaster_severity} · {SEVERITY_TEXT[form.disaster_severity]}</span>
              <input
                type="range"
                min={1}
                max={5}
                step={1}
                value={form.disaster_severity}
                onChange={(e) => set('disaster_severity', e.target.value)}
                className="mt-2 h-2 w-full cursor-pointer accent-accent"
              />
              <span className="flex justify-between text-xs text-text-muted"><span>1 Minor</span><span>5 Catastrophic</span></span>
              {errors.disaster_severity && <span role="alert" className="mt-1 block text-xs text-red-300">{errors.disaster_severity}</span>}
            </label>

            <div className="grid gap-4 sm:grid-cols-2">
              {FIELDS.map((f) => (
                <label key={f.key} className="block text-sm">
                  {f.label}
                  <input
                    type="text"
                    inputMode="numeric"
                    value={form[f.key]}
                    onChange={(e) => set(f.key, e.target.value)}
                    aria-invalid={Boolean(errors[f.key])}
                    className={cn(input, errors[f.key] ? 'border-critical' : 'border-navy-600')}
                  />
                  {errors[f.key] ? (
                    <span role="alert" className="mt-1 block text-xs text-red-300">{errors[f.key]}</span>
                  ) : (
                    <span className="mt-1 block text-xs text-text-muted">{f.hint}</span>
                  )}
                </label>
              ))}
            </div>
          </div>

          {runError && (
            <div role="alert" className="mt-4 rounded-lg border border-critical/40 bg-critical/10 px-3 py-2 text-sm text-red-300">
              <p>{runError}</p>
              <button type="button" onClick={run} className="mt-1 text-xs underline">Try again</button>
            </div>
          )}

          <Button className="mt-5 w-full" icon={FlaskConical} loading={running} onClick={run}>
            {running ? 'Running simulation…' : 'Run simulation'}
          </Button>
          <p className="mt-2 text-xs text-text-muted">A simulation tests a hypothetical. It never changes real incidents or dispatches anyone.</p>
        </Card>

        <div className="min-w-0">
          {notice && (
            <div role="status" className="mb-4 flex items-start justify-between gap-3 rounded-lg border border-navy-600 bg-navy-800 px-4 py-2 text-sm text-text-muted">
              <span>{notice}</span>
              <button onClick={() => setNotice('')} className="text-xs underline">Dismiss</button>
            </div>
          )}
          {active ? (
            <ResultPanel scenario={active} />
          ) : (
            <EmptyState
              icon={FlaskConical}
              title="No scenarios yet"
              description="Choose an example or set your own numbers, then press Run simulation. Results and comparisons appear here."
            />
          )}
        </div>
      </div>

      {scenarios.length > 0 && (
        <div className="mt-6">
          <Comparison
            scenarios={scenarios}
            activeKey={active?.key}
            onView={setActiveKey}
            onRemove={removeScenario}
            onClear={() => { setScenarios([]); setActiveKey(null); setNotice('') }}
          />
        </div>
      )}
    </>
  )
}