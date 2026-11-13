import ComingSoon from '../components/ui/ComingSoon'

export default function IncidentDetailsPage() {
  return <ComingSoon title="Incident Details" description="Everything known about one incident." endpoint="GET /incidents/{id}" phase={6} />
}
