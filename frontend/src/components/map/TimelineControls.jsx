import { Play, Pause, ChevronLeft, ChevronRight } from 'lucide-react'
import Card, { CardHeader } from '../ui/Card'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import { formatDateTime, timeAgo } from '../../utils/format'

export default function TimelineControls({ steps, current, onChange, playing, onTogglePlay }) {
  const last = steps.length - 1
  return (
    <Card>
      <CardHeader
        title="Incident evolution"
        subtitle="Move the slider or press Play to see how reports, severity and affected area changed over time."
        action={<Badge tone="info">Step {current + 1} of {steps.length}</Badge>}
      />
      <p className="mb-3 text-sm">
        Showing the situation at <span className="font-medium text-accent">{formatDateTime(steps[current])}</span>{' '}
        <span className="text-text-muted">({timeAgo(steps[current])})</span>
      </p>
      <div className="flex items-center gap-2">
        <Button size="sm" variant="secondary" icon={playing ? Pause : Play} onClick={onTogglePlay}>
          {playing ? 'Pause' : 'Play'}
        </Button>
        <Button size="sm" variant="ghost" icon={ChevronLeft} aria-label="Previous step" disabled={current <= 0} onClick={() => onChange(current - 1)} />
        <input
          type="range"
          min={0}
          max={last}
          step={1}
          value={current}
          onChange={(e) => onChange(Number(e.target.value))}
          aria-label="Time step"
          aria-valuetext={formatDateTime(steps[current])}
          className="h-2 w-full cursor-pointer accent-accent"
        />
        <Button size="sm" variant="ghost" icon={ChevronRight} aria-label="Next step" disabled={current >= last} onClick={() => onChange(current + 1)} />
        <Button size="sm" variant="secondary" disabled={current >= last} onClick={() => onChange(last)}>Latest</Button>
      </div>
      <div className="mt-1 flex justify-between text-xs text-text-muted">
        <span>{formatDateTime(steps[0])}</span>
        <span>{formatDateTime(steps[last])}</span>
      </div>
    </Card>
  )
}