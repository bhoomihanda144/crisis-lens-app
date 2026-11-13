import Badge from '../ui/Badge'
import Card from '../ui/Card'
import { labelOf } from '../../utils/format'
import { urgencyTone, confidenceTone, verificationTone } from '../../utils/tones'

function ScoreBadge({ value, tones }) {
  if (!value) return <span className="text-text-muted">Not analysed</span>
  return (
    <Badge tone={tones[value.level]}>
      {value.score} · {labelOf(value.level)}
    </Badge>
  )
}

export const UrgencyBadge = ({ value }) => <ScoreBadge value={value} tones={urgencyTone} />
export const ConfidenceBadge = ({ value }) => <ScoreBadge value={value} tones={confidenceTone} />
export const VerificationBadge = ({ value }) => <ScoreBadge value={value} tones={verificationTone} />

export function ScoreTriple({ urgency, evidenceConfidence, verificationPriority }) {
  const items = [
    { title: 'Urgency', hint: 'How serious this would be if the reports are true.', value: urgency, tones: urgencyTone },
    { title: 'Evidence confidence', hint: 'How well independent evidence supports the reports.', value: evidenceConfidence, tones: confidenceTone },
    { title: 'Verification priority', hint: 'How soon a human should check this.', value: verificationPriority, tones: verificationTone },
  ]
  return (
    <div>
      <div className="grid gap-3 md:grid-cols-3">
        {items.map(({ title, hint, value, tones }) => (
          <Card key={title}>
            <p className="text-sm font-medium">{title}</p>
            <p className="text-xs text-text-muted">{hint}</p>
            {value ? (
              <>
                <p className="mt-3 text-3xl font-bold">{value.score}</p>
                <div className="mt-1">
                  <Badge tone={tones[value.level]}>{labelOf(value.level)}</Badge>
                </div>
                <ul className="mt-3 list-disc space-y-1 pl-4 text-xs text-text-muted">
                  {value.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="mt-3 text-sm text-text-muted">Not available</p>
            )}
          </Card>
        ))}
      </div>
      <p className="mt-2 text-xs text-text-muted">These three scores are separate on purpose and are never combined into one number.</p>
    </div>
  )
}