import { Construction } from 'lucide-react'
import PageHeader from './PageHeader'
import Card from './Card'
import Badge from './Badge'

export default function ComingSoon({ title, description, endpoint, phase }) {
  return (
    <>
      <PageHeader title={title} description={description} />
      <Card className="flex items-start gap-3">
        <Construction className="mt-0.5 h-5 w-5 text-verify" aria-hidden="true" />
        <div className="space-y-2 text-sm">
          <p>This page is scheduled for Phase {phase}.</p>
          <p className="text-text-muted">
            Data source: <Badge tone="info">{endpoint}</Badge>
          </p>
        </div>
      </Card>
    </>
  )
}