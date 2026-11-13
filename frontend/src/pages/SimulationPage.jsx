import { useState } from 'react'
import {
  Play,
  RotateCcw,
  AlertTriangle,
  ShieldAlert,
  CheckCircle2,
  Clock,
  Users,
  Truck,
  ArrowRight,
  Flame,
  Activity,
  Code2,
  ChevronDown,
  ChevronUp,
  Waves,
} from 'lucide-react'
import Card, { CardHeader } from '../components/ui/Card'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import PageHeader from '../components/ui/PageHeader'
import { runSimulation } from '../services/simulationService'

const PRESETS = [
  {
    name: '🌧️ Bellandur Lake Breach (Severe Flood)',
    desc: '3 arterial roads inundated, high population in flood path',
    params: {
      scenario_name: 'Bellandur Lake Breach, 3 roads blocked',
      affected_population: 14000,
      disaster_severity: 4,
      rescue_teams: 5,
      blocked_roads: 3,
      available_ambulances: 4,
    },
  },
  {
    name: '🌊 Monsoon Red Alert (Catastrophic Surge)',
    desc: 'Widespread urban flooding, heavy infrastructure failure',
    params: {
      scenario_name: 'Monsoon Red Alert & Dam Overflow, 5 roads blocked',
      affected_population: 26000,
      disaster_severity: 5,
      rescue_teams: 4,
      blocked_roads: 5,
      available_ambulances: 3,
    },
  },
  {
    name: '⚠️ Localized Waterlogging (Controlled)',
    desc: 'Minor road pooling, adequate standing responder units',
    params: {
      scenario_name: 'Localized waterlogging, 1 road blocked',
      affected_population: 4500,
      disaster_severity: 2,
      rescue_teams: 8,
      blocked_roads: 1,
      available_ambulances: 8,
    },
  },
]

const SEVERITY_LABELS = {
  1: { label: 'Minor (Localized)', color: 'text-slate-400', bar: 'bg-slate-500' },
  2: { label: 'Moderate (Waterlogging)', color: 'text-sky-400', bar: 'bg-sky-500' },
  3: { label: 'Significant (Road Closures)', color: 'text-yellow-400', bar: 'bg-yellow-500' },
  4: { label: 'Severe (Flash Inundation)', color: 'text-orange-400', bar: 'bg-orange-500' },
  5: { label: 'Catastrophic (Critical Surge)', color: 'text-red-400', bar: 'bg-red-500' },
}

export default function SimulationPage() {
  const [form, setForm] = useState(PRESETS[0].params)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [showJson, setShowJson] = useState(false)

  const handlePreset = (preset) => {
    setForm(preset.params)
    setError(null)
  }

  const handleRun = async (e) => {
    if (e) e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const payload = {
        scenario_name: form.scenario_name.trim(),
        affected_population: Number(form.affected_population),
        disaster_severity: Number(form.disaster_severity),
        rescue_teams: Number(form.rescue_teams),
        blocked_roads: Number(form.blocked_roads),
        available_ambulances: Number(form.available_ambulances),
      }
      const data = await runSimulation(payload)
      setResult(data)
    } catch (err) {
      setError(err?.message || 'Failed to execute simulation.')
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setForm(PRESETS[0].params)
    setResult(null)
    setError(null)
  }

  const shortages = result?.results?.shortages || []
  const hasShortages = shortages.length > 0
  const priorityChanges = result?.results?.priority_changes || []

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <PageHeader
        title="What-If Emergency Simulation Engine"
        description="Predict secondary flood cascades, compute rescue deficits, and test road bottleneck scenarios before dispatching teams."
        actions={
          <div className="flex items-center gap-2">
            <span className="flex h-2.5 w-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <Badge tone="verified" className="text-xs font-semibold px-2.5 py-1">
              IS_SIMULATION: TRUE (Isolated Sandbox)
            </Badge>
          </div>
        }
      />

      {/* Preset Quick Selectors */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {PRESETS.map((p, idx) => {
          const isSelected = form.scenario_name === p.params.scenario_name
          return (
            <button
              key={idx}
              type="button"
              onClick={() => handlePreset(p)}
              className={`text-left p-3.5 rounded-xl border transition-all ${
                isSelected
                  ? 'border-accent bg-accent/10 shadow-lg shadow-cyan-950/40 ring-1 ring-accent/50'
                  : 'border-navy-700 bg-navy-800/80 hover:bg-navy-750 hover:border-navy-600'
              }`}
            >
              <p className="font-semibold text-sm text-text-primary">{p.name}</p>
              <p className="mt-1 text-xs text-text-muted">{p.desc}</p>
            </button>
          )
        })}
      </div>

      {/* 2-Column Grid: Form Inputs vs Results */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Simulation Controls (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <Card>
            <CardHeader
              title="Hypothetical Parameters"
              subtitle="Configure disaster forces and available responder capacity"
              action={
                <Button variant="ghost" size="sm" onClick={handleReset} icon={RotateCcw}>
                  Reset
                </Button>
              }
            />

            <form onSubmit={handleRun} className="space-y-4">
              {/* Scenario Name */}
              <div>
                <label className="block text-xs font-medium text-text-muted uppercase tracking-wider mb-1">
                  Scenario Title
                </label>
                <input
                  type="text"
                  required
                  value={form.scenario_name}
                  onChange={(e) => setForm({ ...form, scenario_name: e.target.value })}
                  className="w-full rounded-lg border border-navy-600 bg-navy-900 px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
                />
              </div>

              {/* Disaster Severity Slider (1-5) */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-medium text-text-muted uppercase tracking-wider">
                    Disaster Severity (1–5)
                  </label>
                  <span className={`text-xs font-bold ${SEVERITY_LABELS[form.disaster_severity]?.color}`}>
                    {form.disaster_severity} - {SEVERITY_LABELS[form.disaster_severity]?.label}
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="5"
                  step="1"
                  value={form.disaster_severity}
                  onChange={(e) => setForm({ ...form, disaster_severity: Number(e.target.value) })}
                  className="w-full h-2 bg-navy-700 rounded-lg appearance-none cursor-pointer accent-accent"
                />
                <div className="flex justify-between text-[10px] text-text-muted mt-1">
                  <span>1 (Minor)</span>
                  <span>3 (Elevated)</span>
                  <span>5 (Catastrophic)</span>
                </div>
              </div>

              {/* Affected Population */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-medium text-text-muted uppercase tracking-wider flex items-center gap-1.5">
                    <Users className="h-3.5 w-3.5 text-accent" />
                    At-Risk Population
                  </label>
                  <span className="text-xs font-semibold text-text-primary">
                    {Number(form.affected_population).toLocaleString()} citizens
                  </span>
                </div>
                <input
                  type="range"
                  min="500"
                  max="50000"
                  step="500"
                  value={form.affected_population}
                  onChange={(e) => setForm({ ...form, affected_population: Number(e.target.value) })}
                  className="w-full h-2 bg-navy-700 rounded-lg appearance-none cursor-pointer accent-accent"
                />
              </div>

              {/* Blocked Roads */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-medium text-text-muted uppercase tracking-wider flex items-center gap-1.5">
                    <Waves className="h-3.5 w-3.5 text-orange-400" />
                    Submerged / Blocked Roads
                  </label>
                  <span className="text-xs font-semibold text-orange-400">
                    {form.blocked_roads} arterial routes
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="10"
                  step="1"
                  value={form.blocked_roads}
                  onChange={(e) => setForm({ ...form, blocked_roads: Number(e.target.value) })}
                  className="w-full h-2 bg-navy-700 rounded-lg appearance-none cursor-pointer accent-orange-400"
                />
              </div>

              {/* Available Rescue Teams */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-medium text-text-muted uppercase tracking-wider flex items-center gap-1.5">
                    <Flame className="h-3.5 w-3.5 text-red-400" />
                    Available Rescue Teams
                  </label>
                  <span className="text-xs font-semibold text-text-primary">
                    {form.rescue_teams} teams
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="20"
                  step="1"
                  value={form.rescue_teams}
                  onChange={(e) => setForm({ ...form, rescue_teams: Number(e.target.value) })}
                  className="w-full h-2 bg-navy-700 rounded-lg appearance-none cursor-pointer accent-accent"
                />
              </div>

              {/* Available Ambulances */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs font-medium text-text-muted uppercase tracking-wider flex items-center gap-1.5">
                    <Truck className="h-3.5 w-3.5 text-emerald-400" />
                    Operational Ambulances
                  </label>
                  <span className="text-xs font-semibold text-text-primary">
                    {form.available_ambulances} ambulances
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="20"
                  step="1"
                  value={form.available_ambulances}
                  onChange={(e) => setForm({ ...form, available_ambulances: Number(e.target.value) })}
                  className="w-full h-2 bg-navy-700 rounded-lg appearance-none cursor-pointer accent-emerald-400"
                />
              </div>

              {/* Submit Button */}
              <Button
                type="submit"
                loading={loading}
                icon={Play}
                className="w-full py-2.5 mt-2 font-bold tracking-wide shadow-md shadow-accent/20"
              >
                {loading ? 'Running AI Engine...' : 'Run Live Predictive Simulation'}
              </Button>
            </form>
          </Card>
        </div>

        {/* Right Column: Dynamic Simulation Results (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {error && (
            <div className="p-4 rounded-xl border border-red-500/40 bg-red-950/40 text-red-200 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-sm">Simulation Execution Error</p>
                <p className="text-xs mt-1 text-red-300">{error}</p>
              </div>
            </div>
          )}

          {!result && !loading && !error && (
            <Card className="text-center py-12 border-dashed border-navy-600 bg-navy-900/40">
              <Activity className="h-12 w-12 text-accent/60 mx-auto mb-3 animate-pulse" />
              <h3 className="text-base font-semibold text-text-primary">Ready to Run Simulation</h3>
              <p className="text-sm text-text-muted max-w-md mx-auto mt-1">
                Select a disaster preset above or adjust the parameters on the left, then click{' '}
                <span className="text-accent font-medium">"Run Live Predictive Simulation"</span> to calculate resource shortfalls.
              </p>
            </Card>
          )}

          {loading && (
            <Card className="py-16 text-center bg-navy-900/60">
              <div className="flex flex-col items-center justify-center space-y-3">
                <div className="h-10 w-10 border-4 border-accent border-t-transparent rounded-full animate-spin" />
                <p className="text-sm font-semibold text-text-primary">Calculating Cascade Hazards...</p>
                <p className="text-xs text-text-muted max-w-xs">
                  Evaluating road network inundation delays and reranking live emergency priority scores...
                </p>
              </div>
            </Card>
          )}

          {result && !loading && (
            <div className="space-y-4">
              {/* Status Banner */}
              <div
                className={`p-4 rounded-xl border flex items-center justify-between ${
                  hasShortages
                    ? 'border-red-500/50 bg-red-950/30 text-red-200'
                    : 'border-emerald-500/50 bg-emerald-950/30 text-emerald-200'
                }`}
              >
                <div className="flex items-center gap-3">
                  {hasShortages ? (
                    <ShieldAlert className="h-6 w-6 text-red-400 shrink-0" />
                  ) : (
                    <CheckCircle2 className="h-6 w-6 text-emerald-400 shrink-0" />
                  )}
                  <div>
                    <p className="font-bold text-sm">
                      {hasShortages ? 'CRITICAL DEFICIT DETECTED' : 'CAPACITY ADEQUATE'}
                    </p>
                    <p className="text-xs opacity-90 mt-0.5">{result.results.summary}</p>
                  </div>
                </div>
                <Badge tone={hasShortages ? 'critical' : 'verified'} className="shrink-0 font-mono">
                  ID: {result.scenario_id}
                </Badge>
              </div>

              {/* 3 Metric Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {/* Rescue Teams */}
                <Card className="p-3.5 bg-navy-800">
                  <div className="flex items-center justify-between text-xs text-text-muted">
                    <span>Rescue Teams</span>
                    <Flame className="h-4 w-4 text-accent" />
                  </div>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="text-2xl font-bold text-text-primary">
                      {result.results.resource_demand.rescue_teams}
                    </span>
                    <span className="text-xs text-text-muted">demanded</span>
                  </div>
                  <div className="mt-2 text-xs">
                    {shortages.find((s) => s.resource === 'rescue_teams') ? (
                      <span className="text-red-400 font-semibold flex items-center gap-1">
                        Shortfall: -{shortages.find((s) => s.resource === 'rescue_teams').shortfall} teams
                      </span>
                    ) : (
                      <span className="text-emerald-400 font-semibold">100% Covered</span>
                    )}
                  </div>
                </Card>

                {/* Ambulances */}
                <Card className="p-3.5 bg-navy-800">
                  <div className="flex items-center justify-between text-xs text-text-muted">
                    <span>Ambulances</span>
                    <Truck className="h-4 w-4 text-emerald-400" />
                  </div>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="text-2xl font-bold text-text-primary">
                      {result.results.resource_demand.ambulances}
                    </span>
                    <span className="text-xs text-text-muted">demanded</span>
                  </div>
                  <div className="mt-2 text-xs">
                    {shortages.find((s) => s.resource === 'ambulances') ? (
                      <span className="text-red-400 font-semibold flex items-center gap-1">
                        Shortfall: -{shortages.find((s) => s.resource === 'ambulances').shortfall} units
                      </span>
                    ) : (
                      <span className="text-emerald-400 font-semibold">100% Covered</span>
                    )}
                  </div>
                </Card>

                {/* Response Delay */}
                <Card className="p-3.5 bg-navy-800">
                  <div className="flex items-center justify-between text-xs text-text-muted">
                    <span>Access Delay</span>
                    <Clock className="h-4 w-4 text-orange-400" />
                  </div>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="text-2xl font-bold text-orange-400">
                      +{result.results.estimated_response_delay_minutes}m
                    </span>
                    <span className="text-xs text-text-muted">estimated delay</span>
                  </div>
                  <p className="mt-2 text-xs text-text-muted">
                    {form.blocked_roads} blocked arterial routes
                  </p>
                </Card>
              </div>

              {/* Dynamic Priority Shifts */}
              <Card>
                <CardHeader
                  title="Dynamic Incident Priority Shifts"
                  subtitle="How flood water and road access recalculate live rescue rankings"
                />

                {priorityChanges.length === 0 ? (
                  <p className="text-xs text-text-muted py-2">
                    No priority rank reordering required under current scenario thresholds.
                  </p>
                ) : (
                  <div className="space-y-2.5">
                    {priorityChanges.map((change, idx) => (
                      <div
                        key={idx}
                        className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-lg border border-navy-700 bg-navy-900/60 gap-2"
                      >
                        <div className="space-y-0.5">
                          <p className="text-xs font-semibold text-text-primary">
                            {change.incident_id}: {change.title}
                          </p>
                          <p className="text-[11px] text-text-muted">{change.reason}</p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-xs text-text-muted">Rank {change.baseline_rank}</span>
                          <ArrowRight className="h-3 w-3 text-accent" />
                          <Badge tone="critical" className="font-bold">
                            Rank {change.scenario_rank}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>

              {/* Raw Contract JSON Drawer */}
              <div className="rounded-xl border border-navy-700 bg-navy-900/40 p-3">
                <button
                  type="button"
                  onClick={() => setShowJson(!showJson)}
                  className="w-full flex items-center justify-between text-xs text-text-muted hover:text-text-primary"
                >
                  <span className="flex items-center gap-1.5 font-mono">
                    <Code2 className="h-4 w-4 text-accent" />
                    API Contract v1.0 Section 4.9 Response Inspector
                  </span>
                  {showJson ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </button>

                {showJson && (
                  <pre className="mt-3 p-3 rounded-lg bg-navy-950 text-emerald-400 font-mono text-[11px] overflow-x-auto max-h-64 border border-navy-800">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
