import React, { useEffect, useState } from 'react';
import { listIncidents } from '../services/incidentService';

export default function IncidentMapPage() {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listIncidents()
      .then((res) => {
        setIncidents(res.data?.incidents || res.data || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="p-6 text-white">
      <h1 className="text-2xl font-bold mb-2">Incident Map</h1>
      <p className="text-gray-400 mb-6">Geospatial distribution and real-time incident monitoring.</p>
      {loading ? (
        <p>Loading active incidents...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-gray-800 p-4 rounded border border-gray-700 h-96 flex items-center justify-center text-gray-500">
            [ Leaflet Map View: {incidents.length} Incidents Loaded ]
          </div>
          <div className="bg-gray-800 p-4 rounded border border-gray-700 overflow-y-auto h-96">
            <h2 className="font-semibold mb-3">Active Incidents List</h2>
            {incidents.map((inc) => (
              <div key={inc.id || inc.incident_id} className="mb-3 p-3 bg-gray-900 rounded border border-gray-800">
                <div className="font-medium text-sm">{inc.title || inc.description}</div>
                <div className="text-xs text-gray-400 mt-1">Severity: {inc.severity} | Status: {inc.status}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}