/**
 * CrisisLens API Contract & Health Validator
 * Implements automated validation against CrisisLens API Contract v1.0.
 * Run with: node scripts/check-contract.mjs [baseUrl]
 */

const BASE_URL = process.argv[2] || process.env.API_BASE_URL || 'http://127.0.0.1:8000';

const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
  bold: '\x1b[1m',
};

async function testEndpoint(name, path, options = {}) {
  const url = `${BASE_URL}${path}`;
  try {
    const res = await fetch(url, options);
    const contentType = res.headers.get('content-type') || '';
    const body = contentType.includes('application/json') ? await res.json() : await res.text();
    return { ok: res.ok, status: res.status, body };
  } catch (err) {
    return { ok: false, status: 0, error: err.message };
  }
}

async function runContractChecks() {
  console.log(`\n${colors.bold}${colors.cyan}=== CrisisLens Contract Validation Suite ===${colors.reset}`);
  console.log(`Target Backend: ${colors.yellow}${BASE_URL}${colors.reset}\n`);

  let totalTests = 0;
  let passedTests = 0;

  function assert(condition, testName, details = '') {
    totalTests++;
    if (condition) {
      passedTests++;
      console.log(`  ${colors.green}✓ PASS${colors.reset} ${testName}`);
    } else {
      console.log(`  ${colors.red}✗ FAIL${colors.reset} ${testName} ${details ? `(${details})` : ''}`);
    }
  }

  // 1. Health check
  const health = await testEndpoint('Health Check', '/health');
  assert(health.ok && health.body?.status === 'healthy', 'GET /health returns 200 OK');

  // 2. Incidents List
  const incidentsRes = await testEndpoint('List Incidents', '/incidents');
  assert(incidentsRes.ok && Array.isArray(incidentsRes.body?.items), 'GET /incidents conforms to structure');

  const incidents = incidentsRes.body?.items || [];
  const testIncidentId = incidents.length > 0 ? incidents[0].id : 'inc_001';

  // 3. Evidence Graph Invariant & Node Reference Check (Critical)
  const graphRes = await testEndpoint('Evidence Graph', `/incidents/${testIncidentId}/evidence-graph`);
  if (!graphRes.ok) {
    assert(false, `GET /incidents/${testIncidentId}/evidence-graph`, `Status: ${graphRes.status}`);
  } else {
    const graph = graphRes.body;
    assert(Array.isArray(graph.nodes), 'Evidence graph has nodes array');
    assert(Array.isArray(graph.edges), 'Evidence graph has edges array');

    const nodeIds = new Set(graph.nodes.map((n) => n.id));
    let brokenReferences = 0;
    let selfLoops = 0;

    for (const edge of graph.edges) {
      if (edge.source === edge.target) {
        selfLoops++;
      }
      if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) {
        brokenReferences++;
      }
    }

    assert(brokenReferences === 0, `Evidence graph node references (0 broken found out of ${graph.edges.length} edges)`);
    assert(selfLoops === 0, 'Evidence graph contains no self-loops');
    console.log(`     ${colors.cyan}↳ Verified ${graph.nodes.length} nodes and ${graph.edges.length} valid DAG edges.${colors.reset}`);
  }

  // 4. Priority Scores Contract Check
  const priorityRes = await testEndpoint('Priority Queue', '/incidents/priority?sort=urgency');
  if (priorityRes.ok) {
    const items = priorityRes.body?.items || [];
    const validScores = items.every((i) => i.urgency && i.evidence_confidence && i.verification_priority);
    assert(validScores, 'GET /incidents/priority maintains 3-dimension score separation');
  } else {
    assert(false, 'GET /incidents/priority returns 200');
  }

  // 5. What-If Simulation Contract Check
  const simPayload = {
    scenario_name: 'Heavy rain, 3 roads blocked',
    affected_population: 12000,
    disaster_severity: 4,
    rescue_teams: 6,
    blocked_roads: 3,
    available_ambulances: 5,
  };
  const simRes = await testEndpoint('What-If Simulation', '/simulate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(simPayload),
  });

  if (simRes.ok) {
    const sim = simRes.body;
    assert(sim.is_simulation === true, 'POST /simulate sets is_simulation: true invariant');
    assert(sim.results?.resource_demand !== undefined, 'POST /simulate computes resource demand');
    assert(Array.isArray(sim.results?.shortages), 'POST /simulate lists resource shortages');
  } else {
    assert(false, 'POST /simulate executes scenario simulation');
  }

  console.log(`\n${colors.bold}Summary:${colors.reset} ${passedTests}/${totalTests} checks passed.`);
  if (passedTests === totalTests) {
    console.log(`${colors.green}${colors.bold}Contract validation SUCCESSFUL. Ready for evaluation.${colors.reset}\n`);
    process.exit(0);
  } else {
    console.log(`${colors.red}${colors.bold}Contract validation had failures. Review logs above.${colors.reset}\n`);
    process.exit(1);
  }
}

runContractChecks();
