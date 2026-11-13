import { useState } from 'react'
import PageHeader from '../components/ui/PageHeader'
import Card, { CardHeader } from '../components/ui/Card'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import useDataMode from '../hooks/useDataMode'
import { API_BASE_URL } from '../services/api'
import { listReports, getReport, createReport } from '../services/reportService'
import { listIncidents, getIncident } from '../services/incidentService'
import { analyzeReport, getPriority, getEvidenceGraph } from '../services/analysisService'
import { runSimulation } from '../services/simulationService'
import { verifyReport } from '../services/verificationService'

const TESTS = [
  { name: 'GET /reports', run: () => listReports({ sort: 'verification_priority' }) },
  { name: 'GET /reports/rpt_001', run: () => getReport('rpt_001') },
  { name: 'GET /reports/rpt_999 (expect 404)', run: () => getReport('rpt_999') },
  {
    name: 'POST /reports',
    run: () =>
      createReport({
        text: 'Test report: water rising near the school',
        source: { type: 'citizen', name: 'API test' },
        location: { lat: 12.9304, lng: 77.6784, label: 'Lake Road, Bellandur' },
      }),
  },
  { name: 'GET /incidents', run: () => listIncidents() },
  { name: 'GET /incidents/inc_001', run: () => getIncident('inc_001') },
  { name: 'POST /analyze/rpt_001', run: () => analyzeReport('rpt_001') },
  { name: 'GET /incidents/priority', run: () => getPriority('urgency') },
  { name: 'GET /incidents/inc_001/evidence-graph', run: () => getEvidenceGraph('inc_001') },
  {
    name: 'POST /simulate',
    run: () =>
      runSimulation({ scenario_name: 'API test', affected_population: 12000, disaster_severity: 4, rescue_teams: 6, blocked_roads: 3, available_ambulances: 5 }),
  },
  {
    name: 'PATCH /reports/rpt_008/verify (changes data)',
    run: () => verifyReport('rpt_008', { action: 'request_more_info', note: 'API test', verified_by: 'Tester' }),
  },
]

export default function ApiTestPage() {
  const mode = useDataMode()
  const [running, setRunning] = useState(null)
  const [result, setResult] = useState(null)

  async function run(test) {
    setRunning(test.name)
    setResult(null)
    const started = performance.now()
    try {
      const data = await test.run()
      setResult({ name: test.name, ok: true, ms: Math.round(performance.now() - started), body: data })
    } catch (err) {
      setResult({ name: test.name, ok: false, ms: Math.round(performance.now() - started), body: { code: err.code, status: err.status, message: err.message } })
    } finally {
      setRunning(null)
    }
  }

  return (
    <>
      <PageHeader title="API Test (developer tool)" description="Calls every service and shows the raw response. Remove before final release." />
      <Card className="mb-6">
        <p className="text-sm">
          Mode: <Badge tone={mode === 'demo' ? 'verify' : 'info'}>{mode}</Badge>{' '}
          Backend: <span className="font-mono text-accent">{API_BASE_URL}</span>
        </p>
      </Card>
      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Card>
          <CardHeader title="Endpoints" />
          <div className="flex flex-col gap-2">
            {TESTS.map((t) => (
              <Button key={t.name} variant="secondary" size="sm" loading={running === t.name} onClick={() => run(t)} className="justify-start text-left">
                {t.name}
              </Button>
            ))}
          </div>
        </Card>
        <Card>
          <CardHeader
            title="Response"
            action={result && <Badge tone={result.ok ? 'verified' : 'critical'}>{result.ok ? 'OK' : 'Error'} · {result.ms} ms</Badge>}
          />
          {result ? (
            <pre className="max-h-[70vh] overflow-auto rounded-lg bg-navy-950 p-3 font-mono text-xs text-slate-300">{JSON.stringify(result.body, null, 2)}</pre>
          ) : (
            <p className="text-sm text-text-muted">Pick an endpoint on the left.</p>
          )}
        </Card>
      </div>
    </>
  )
}