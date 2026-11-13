import { useParams, Link } from 'react-router-dom'
import {
  MapPin,
  Clock,
  Share2,
  FileText,
  ArrowLeft,
  Activity,
  AlertTriangle,
  Layers,
  Map,
} from 'lucide-react'
import PageHeader from '../components/ui/PageHeader'
import Card, { CardHeader } from '../components/ui/Card'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Skeleton from '../components/ui/Skeleton'
import ErrorState from '../components/ui/ErrorState'
import EmptyState from '../components/ui/EmptyState'
import useApi from '../hooks/useApi'
import { getIncident } from '../services/incidentService'
import { formatDateTime, labelOf, timeAgo } from '../utils/format'
import { severityTone } from '../utils/tones'

const statusTone = {
  active: 'critical',
  monitoring: 'verify',
  resolved: 'verified',
}

export default function IncidentDetailsPage() {
  const { id } = useParams()
  const { data: incident, loading, error, reload } = useApi(() => getIncident(id), [id])

  if (error) {
    return (
      <>
        <PageHeader title="Incident Details" />
        <ErrorState
          title={`Could not load incident ${id}`}
          message={error.message}
          onRetry={reload}
        />
      </>
    )
  }

  if (loading && !incident) {
    return (
      <div className="space-y-4">
        <PageHeader title="Loading Incident..." />
        <Skeleton className="h-48" />
        <Skeleton className="h-64" />
      </div>
    )
  }

  if (!incident) {
    return (
      <EmptyState
        title="Incident not found"
        description={`No emergency record found for identifier ${id}.`}
        action={
          <Link to="/incidents">
            <Button icon={ArrowLeft}>Back to Incident Queue</Button>
          </Link>
        }
      />
    )
  }

  const timeline = incident.timeline || []

  return (
    <div className="space-y-6">
      <PageHeader
        title={incident.title}
        description={`Incident ID: ${incident.id} · Discovered ${timeAgo(incident.first_reported_at)} · Last active ${timeAgo(incident.last_updated_at)}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Link to="/incidents">
              <Button variant="ghost" size="sm" icon={ArrowLeft}>
                Queue
              </Button>
            </Link>
            <Link to={`/graph/${incident.id}`}>
              <Button variant="secondary" size="sm" icon={Share2}>
                Evidence Graph
              </Button>
            </Link>
            <Link to={`/map?incident=${incident.id}`}>
              <Button variant="primary" size="sm" icon={Map}>
                View on Map
              </Button>
            </Link>
          </div>
        }
      />

      {/* High-level status cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Card className="p-3.5">
          <p className="text-xs text-text-muted">Severity</p>
          <div className="mt-1 flex items-center gap-1.5">
            <Badge tone={severityTone[incident.severity] || 'neutral'} className="capitalize font-bold text-sm">
              {incident.severity}
            </Badge>
          </div>
        </Card>

        <Card className="p-3.5">
          <p className="text-xs text-text-muted">Status</p>
          <div className="mt-1 flex items-center gap-1.5">
            <Badge tone={statusTone[incident.status] || 'neutral'} className="capitalize font-bold text-sm">
              {labelOf(incident.status)}
            </Badge>
          </div>
        </Card>

        <Card className="p-3.5">
          <p className="text-xs text-text-muted">Associated Reports</p>
          <p className="mt-1 text-2xl font-bold text-text-primary">
            {incident.report_count || (incident.report_ids || []).length}
          </p>
        </Card>

        <Card className="p-3.5">
          <p className="text-xs text-text-muted">Independent Sources</p>
          <p className="mt-1 text-2xl font-bold text-accent">
            {incident.independent_source_count ?? (incident.report_count || 1)}
          </p>
        </Card>
      </div>

      {/* 2-Column Info: Location & Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Location & Reports (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <Card>
            <CardHeader title="Incident Location" />
            <div className="space-y-3 text-sm">
              <div className="flex items-start gap-2.5">
                <MapPin className="h-4 w-4 text-accent mt-0.5 shrink-0" />
                <div>
                  <p className="font-semibold text-text-primary">
                    {incident.location?.label || incident.location_label || 'Location unspecified'}
                  </p>
                  {(incident.location?.lat || incident.lat) && (
                    <p className="text-xs text-text-muted mt-0.5 font-mono">
                      Coordinates: {incident.location?.lat || incident.lat},{' '}
                      {incident.location?.lng || incident.lng}
                    </p>
                  )}
                </div>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader
              title="Report References"
              subtitle="Signals grouped under this incident cluster"
            />
            <div className="space-y-2">
              {(incident.report_ids || []).map((repId) => (
                <div
                  key={repId}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-navy-700 bg-navy-900/50 text-xs"
                >
                  <span className="font-mono text-accent font-semibold">{repId}</span>
                  <Link
                    to={`/graph/${incident.id}`}
                    className="text-text-muted hover:text-text-primary flex items-center gap-1"
                  >
                    Inspect in DAG <Share2 className="h-3 w-3" />
                  </Link>
                </div>
              ))}
              {(!incident.report_ids || incident.report_ids.length === 0) && (
                <p className="text-xs text-text-muted">No child reports linked.</p>
              )}
            </div>
          </Card>
        </div>

        {/* Right Column: Timeline Evolution (7 cols) */}
        <div className="lg:col-span-7">
          <Card>
            <CardHeader
              title="Disaster Evolution Timeline"
              subtitle="Chronological audit trail of reported conditions"
            />

            {timeline.length === 0 ? (
              <p className="text-xs text-text-muted py-4">No historical timeline recorded for this incident.</p>
            ) : (
              <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-navy-700">
                {timeline.map((step, idx) => (
                  <div key={idx} className="relative group">
                    <span className="absolute -left-6 top-1 h-3 w-3 rounded-full border-2 border-navy-900 bg-accent ring-2 ring-accent/30" />
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-text-muted">
                          {formatDateTime(step.timestamp)}
                        </span>
                        <Badge tone={severityTone[step.severity] || 'neutral'} className="text-[10px]">
                          {step.severity}
                        </Badge>
                      </div>
                      <p className="text-sm font-medium text-text-primary">{step.summary}</p>
                      {step.affected_radius_m && (
                        <p className="text-xs text-text-muted flex items-center gap-1">
                          <Layers className="h-3 w-3 text-accent" />
                          Estimated affected radius: {step.affected_radius_m}m
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
