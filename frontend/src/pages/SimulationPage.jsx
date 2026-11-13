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

function ResultPanel({ scenario }) {
  const anyShort = scenario.teams.shortfall > 0 || scenario.ambulances.shortfall > 0
  return (
    <Card className="border-accent/30">
      <CardHeader
        title={scenario.name}
        subtitle={scenario.generatedAt ? `Generated ${formatDateTime(scenario.generatedAt)}` : 'Latest result'}
        action={<Badge tone="verify">SIMULATION</Badge>}
      />

      <div
        role="status"
        className={cn(
          'mb-4 rounded-lg border px-4 py-3 text-sm',
          anyShort ? 'border-critical/40 bg-critical/10 text-red-200' : 'border-verified/40 bg-verified/10 text-green-200',
        )}
      >
        {scenario.summary || (anyShort ? 'Some resources fall short in this scenario.' : 'Available resources cover the estimated demand.')}
      </div>

      <div className="overflow-x-auto rounded-xl border border-navy-700">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Resources required compared with resources available</caption>
          <thead className="bg-navy-900 text-xs uppercase tracking-wide text-text-muted">
            <tr>
              {['Resource', 'Required', 'Available', 'Coverage', 'Status'].map((h) => (
                <th key={h} scope="col" className="px-4 py-2 font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-navy-700 bg-navy-800">
            <ResourceRow label="Rescue teams" data={scenario.teams} />
            <ResourceRow label="Ambulances" data={scenario.ambulances} />
          </tbody>
        </table>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div className="rounded-lg bg-navy-900 p-3">
          <p className="text-xs text-text-muted">Estimated response delay</p>
          <p className="mt-1 text-2xl font-bold text-accent">{scenario.delay === null ? '—' : `${scenario.delay} min`}</p>
        </div>
        <div className="rounded-lg bg-navy-900 p-3">
          <p className="text-xs text-text-muted">Disaster severity</p>
          <p className="mt-1 text-2xl font-bold">{scenario.inputs.disaster_severity}<span className="text-sm text-text-muted"> / 5</span></p>
        </div>
        <div className="rounded-lg bg-navy-900 p-3">
          <p className="text-xs text-text-muted">Blocked roads</p>
          <p className="mt-1 text-2xl font-bold">{fmt(scenario.inputs.blocked_roads)}</p>
        </div>
      </div>

      <h3 className="mb-2 mt-5 text-sm font-medium">Changed priorities</h3>
      {scenario.changes.length === 0 ? (
        <p className="text-sm text-text-muted">No real incident changes rank in this scenario.</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {scenario.changes.map((c) => (
            <li key={c.incident_id} className="rounded-md bg-navy-900 px-3 py-2">
              <Link to={`/incidents/${c.incident_id}`} className="font-medium text-accent hover:underline">{c.title || c.incident_id}</Link>
              <span className="ml-2 inline-flex items-center gap-1 font-mono text-xs">
                rank {c.baseline_rank ?? '?'} <ArrowRight className="h-3 w-3" aria-hidden="true" /> {c.scenario_rank ?? '?'}
              </span>
              {c.reason && <span className="block text-xs text-text-muted">{c.reason}</span>}
            </li>
          ))}
        </ul>
      )}
      <p className="mt-4 text-xs text-text-muted">
        This is a what-if estimate. Real incident scores are unchanged, nobody is dispatched, and a human decides how to use these results.
      </p>
    </Card>
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
        description="Test a hypothetical disaster and the resources you have. Results are estimates. They never change real incidents, and humans decide what to do with them."
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