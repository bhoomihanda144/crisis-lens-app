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

const scoreConfig = {
  urgency: {
    label: 'Urgency',
    hint: 'How serious this would be if reports are true.',
    barColor: 'rgba(255,59,59,0.85)',
    barGlow: '0 0 10px rgba(255,59,59,0.5)',
    trackColor: 'rgba(255,59,59,0.08)',
    icon: '🔴',
  },
  evidenceConfidence: {
    label: 'Evidence Confidence',
    hint: 'How well independent evidence supports reports.',
    barColor: 'rgba(0,229,255,0.85)',
    barGlow: '0 0 10px rgba(0,229,255,0.5)',
    trackColor: 'rgba(0,229,255,0.08)',
    icon: '🔵',
  },
  verificationPriority: {
    label: 'Verification Priority',
    hint: 'How soon a human should check this.',
    barColor: 'rgba(251,191,36,0.85)',
    barGlow: '0 0 10px rgba(251,191,36,0.4)',
    trackColor: 'rgba(251,191,36,0.08)',
    icon: '🟡',
  },
}

function ScoreBar({ value, cfg, tones }) {
  const pct = value ? Math.min(100, Math.max(0, value.score)) : 0
  const tone = value ? tones[value.level] : 'neutral'

  return (
    <div className="rounded-xl p-4 transition-all duration-300 relative overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, rgba(10,18,34,0.9) 0%, rgba(6,13,26,0.95) 100%)',
        border: '1px solid rgba(0,229,255,0.08)',
        boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
      }}>
      {/* Background tint */}
      <div className="absolute inset-0 rounded-xl opacity-30 pointer-events-none"
        style={{ background: `radial-gradient(ellipse at 20% 50%, ${cfg.trackColor} 0%, transparent 70%)` }} />

      <div className="relative">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div>
            <p className="text-xs font-tactical font-semibold uppercase tracking-wider text-text-muted">{cfg.label}</p>
            <p className="text-[10px] text-text-dim mt-0.5 leading-relaxed">{cfg.hint}</p>
          </div>
          {value && <Badge tone={tone}>{labelOf(value.level)}</Badge>}
        </div>

        {/* Score number */}
        {value ? (
          <div className="mb-3 flex items-baseline gap-1.5">
            <span className="font-tactical text-4xl font-bold tabular-nums"
              style={{ color: cfg.barColor, textShadow: cfg.barGlow }}>{value.score}</span>
            <span className="text-sm text-text-dim font-mono">/100</span>
          </div>
        ) : (
          <p className="mb-3 text-sm text-text-dim">Not available</p>
        )}

        {/* Progress bar */}
        <div className="mb-3 h-1.5 w-full rounded-full overflow-hidden"
          style={{ background: cfg.trackColor }}>
          <div
            className="h-full rounded-full transition-all duration-1000 ease-out"
            style={{
              width: `${pct}%`,
              background: `linear-gradient(90deg, ${cfg.barColor.replace('0.85', '0.5')} 0%, ${cfg.barColor} 100%)`,
              boxShadow: cfg.barGlow,
            }}
          />
        </div>

        {/* Reasons */}
        {value?.reasons && (
          <ul className="space-y-0.5">
            {value.reasons.map((reason) => (
              <li key={reason} className="flex items-start gap-1.5 text-[11px] text-text-dim">
                <span className="mt-1 h-1 w-1 shrink-0 rounded-full" style={{ background: cfg.barColor }} />
                {reason}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export function ScoreTriple({ urgency, evidenceConfidence, verificationPriority }) {
  const items = [
    { key: 'urgency',             value: urgency,             tones: urgencyTone,      cfg: scoreConfig.urgency },
    { key: 'evidenceConfidence',  value: evidenceConfidence,  tones: confidenceTone,   cfg: scoreConfig.evidenceConfidence },
    { key: 'verificationPriority',value: verificationPriority,tones: verificationTone, cfg: scoreConfig.verificationPriority },
  ]
  return (
    <div>
      <div className="grid gap-3 md:grid-cols-3">
        {items.map(({ key, value, tones, cfg }) => (
          <ScoreBar key={key} value={value} tones={tones} cfg={cfg} />
        ))}
      </div>
      <p className="mt-2 text-[10px] text-text-dim">
        ⚠ These three scores are intentionally separate and are never combined into a single metric.
      </p>
    </div>
  )
}