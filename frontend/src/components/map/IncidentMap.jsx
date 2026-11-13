import { Fragment, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { MapContainer, TileLayer, CircleMarker, Circle, Popup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { SEVERITY_COLOR } from './timelineUtils'
import { labelOf, formatDateTime } from '../../utils/format'

// Fits the view to all incidents once (not on every slider move).
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

// Moves the view to the selected incident.
function Focus({ location }) {
  const map = useMap()
  const lat = location?.lat
  const lng = location?.lng
  useEffect(() => {
    if (lat !== undefined && lng !== undefined) map.flyTo([lat, lng], 14, { duration: 0.8 })
  }, [lat, lng, map])
  return null
}

// markers: [{ incident, state }] where state is the timeline entry shown at the chosen time
export default function IncidentMap({ allPoints, markers, selectedId, onSelect, focusLocation }) {
  return (
    <div
      role="region"
      aria-label="Map of incidents. The list beside the map offers the same information."
      className="dark-tiles relative isolate h-[520px] overflow-hidden rounded-xl border border-navy-700"
    >
      <MapContainer center={[12.95, 77.67]} zoom={11} className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitAll points={allPoints} />
        <Focus location={focusLocation} />

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
                    <div>{state.summary}</div>
                    <div className="text-xs opacity-80">{formatDateTime(state.timestamp)}</div>
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