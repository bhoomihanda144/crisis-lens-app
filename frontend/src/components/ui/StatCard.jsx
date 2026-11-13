import { cn } from '../../utils/cn'
import Card from './Card'

const tones = {
  info: 'text-accent',
  critical: 'text-critical',
  verify: 'text-verify',
  verified: 'text-verified',
}

export default function StatCard({ label, value, hint, icon: Icon, tone = 'info' }) {
  return (
    <Card>
      <div className="flex items-start justify-between">
        <p className="text-sm text-text-muted">{label}</p>
        {Icon && <Icon className={cn('h-5 w-5', tones[tone])} aria-hidden="true" />}
      </div>
      <p className={cn('mt-2 text-3xl font-bold', tones[tone])}>{value}</p>
      {hint && <p className="mt-1 text-xs text-text-muted">{hint}</p>}
    </Card>
  )
}