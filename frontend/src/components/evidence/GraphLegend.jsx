import Card, { CardHeader } from '../ui/Card'
import { ROLE_STYLE } from './roleStyle'

export default function GraphLegend() {
  return (
    <Card>
      <CardHeader title="Legend" />
      <ul className="space-y-2 text-sm">
        {Object.entries(ROLE_STYLE).map(([key, style]) => (
          <li key={key} className="flex items-start gap-2">
            <span className="mt-1 inline-block h-3 w-3 shrink-0 rounded-sm" style={{ background: style.color }} aria-hidden="true" />
            <span>
              <span className="font-medium">{style.label}</span>
              <span className="block text-xs text-text-muted">{style.description}</span>
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-text-muted">
        An arrow points from the later or copied report to the earlier or reference report. A dashed moving line marks a conflict.
        Relationships are AI estimates for a human to check.
      </p>
    </Card>
  )
}