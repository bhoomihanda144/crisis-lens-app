import React, { useState } from 'react';
import { runSimulation } from '../services/simulationService';

export default function SimulationPage() {
  const [scenario, setScenario] = useState({
    title: 'Severe Urban Flooding Test',
    severity: 5,
    additional_resources_allocated: { rescue_teams: 4, ambulances: 2 }
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSimulate = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await runSimulation(scenario);
      setResult(res.data || res);
    } catch (err) {
      alert('Simulation failed: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 text-white max-w-4xl">
      <h1 className="text-2xl font-bold mb-2">What-if Simulation Centre</h1>
      <p className="text-gray-400 mb-6">Test hypothetical disaster scenarios and resource allocation limits.</p>
      
      <form onSubmit={handleSimulate} className="bg-gray-800 p-4 rounded border border-gray-700 mb-6 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Scenario Title</label>
          <input 
            type="text" 
            value={scenario.title} 
            onChange={(e) => setScenario({...scenario, title: e.target.value})}
            className="w-full p-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Severity Level (1-8)</label>
          <input 
            type="number" 
            min="1" max="8"
            value={scenario.severity} 
            onChange={(e) => setScenario({...scenario, severity: parseInt(e.target.value)})}
            className="w-full p-2 bg-gray-900 border border-gray-700 rounded text-white text-sm"
          />
        </div>
        <button 
          type="submit" 
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium"
        >
          {loading ? 'Running Simulation...' : 'Run Simulation'}
        </button>
      </form>

      {result && (
        <div className="bg-gray-800 p-4 rounded border border-gray-700 space-y-3">
          <h2 className="font-semibold text-lg text-green-400">Simulation Results</h2>
          <p className="text-sm bg-gray-900 p-3 rounded">{result.summary || JSON.stringify(result)}</p>
        </div>
      )}
    </div>
  );
}