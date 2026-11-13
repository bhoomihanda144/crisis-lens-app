import { useState } from 'react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import Badge from '../ui/Badge'
import { UrgencyBadge, ConfidenceBadge, VerificationBadge } from '../priority/ScoreBadge'
import { verifyReport } from '../../services/verificationService'
import { formatDateTime, labelOf } from '../../utils/format'
import { reportStatusTone } from '../../utils/tones'

const ACTIONS = [
  { value: 'confirm', title: 'Confirm', hint: 'The information has been checked and is credible.', needsNote: false },
  { value: 'reject', title: 'Reject', hint: 'The information is false, mistaken or unusable.', needsNote: true },
  { value: 'request_more_info', title: 'Request more information', hint: 'It cannot be decided yet. More evidence is needed.', needsNote: true },
]
const field = 'mt-1 w-full rounded-lg border border-navy-600 bg-navy-900 px-3 py-2 text-sm text-text-primary'
const NAME_KEY = 'crisislens_verifier_name'

function savedName() {
  try { return sessionStorage.getItem(NAME_KEY) || '' } catch { return '' }
}

// Render with key={report.id} so the form resets for each report.
export default function VerifyModal({ report, onClose, onSaved }) {
  const [action, setAction] = useState('')
  const [note, setNote] = useState('')
  const [verifiedBy, setVerifiedBy] = useState(savedName)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const analysis = report.analysis
  const previous = report.verification

  async function submit() {
    const chosen = ACTIONS.find((a) => a.value === action)
    if (!chosen) return setError('Choose a decision first.')
    if (chosen.needsNote && !note.trim()) return setError('Please add a note explaining this decision.')
    if (!verifiedBy.trim()) return setError('Enter your name or role so the decision can be traced.')

    setSaving(true)
    setError('')
    try {
      const updated = await verifyReport(report.id, {
        action,
        note: note.trim() || undefined,
        verified_by: verifiedBy.trim(),
      })
      try { sessionStorage.setItem(NAME_KEY, verifiedBy.trim()) } catch { /* ignore */ }
      onSaved(updated)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={`Verify ${report.id}`}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button loading={saving} onClick={submit}>Save decision</Button>
        </>
      }
    >
      <div className="max-h-[60vh] space-y-4 overflow-y-auto pr-1">
        <div className="rounded-lg bg-navy-900 p-3">
          <p className="text-text-primary">{report.text}</p>
          <p className="mt-1 text-xs">
            {report.source.name} ({labelOf(report.source.type)}) · {report.location.label} · {formatDateTime(report.reported_at)}
          </p>
          {analysis ? (
            <div className="mt-2 flex flex-wrap gap-2 text-xs">
              <span>Urgency <UrgencyBadge value={analysis.scores.urgency} /></span>
              <span>Evidence <ConfidenceBadge value={analysis.scores.evidence_confidence} /></span>
              <span>Verify <VerificationBadge value={analysis.scores.verification_priority} /></span>
            </div>
          ) : (
            <p className="mt-2 text-xs">Not analysed yet. You can still record a decision.</p>
          )}
        </div>

        {analysis?.conflicts.length > 0 && (
          <div className="rounded-lg border border-verify/40 p-3">
            <p className="mb-1 text-xs font-medium text-orange-300">Conflicting statements</p>
            {analysis.conflicts.map((c) => (
              <ul key={c.id} className="space-y-1 text-xs">
                {c.statements.map((s) => (
                  <li key={s.report_id}><span className="mr-1 font-mono text-accent">{s.report_id}</span>{s.text}</li>
                ))}
              </ul>
            ))}
          </div>
        )}

        {previous && (
          <p className="text-xs">
            Previous decision: <Badge tone={reportStatusTone[report.status]}>{labelOf(previous.action)}</Badge> by {previous.verified_by || 'unknown'} on {formatDateTime(previous.verified_at)}
            {previous.note && <> — “{previous.note}”</>}
          </p>
        )}

        <fieldset>
          <legend className="mb-1 text-sm font-medium text-text-primary">Your decision</legend>
          <div className="space-y-2">
            {ACTIONS.map((a) => (
              <label key={a.value} className="flex cursor-pointer items-start gap-3 rounded-lg border border-navy-600 p-3 has-[:checked]:border-accent has-[:checked]:bg-accent/5">
                <input type="radio" name="decision" value={a.value} checked={action === a.value} onChange={() => setAction(a.value)} className="mt-1" />
                <span>
                  <span className="block text-sm font-medium text-text-primary">{a.title}</span>
                  <span className="block text-xs">{a.hint}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <label className="block text-text-primary">
          Note {action && action !== 'confirm' ? '(required)' : '(optional)'}
          <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} className={field} placeholder="For example: called the ward officer, confirmed by phone" />
        </label>
        <label className="block text-text-primary">
          Your name or role
          <input value={verifiedBy} onChange={(e) => setVerifiedBy(e.target.value)} className={field} />
        </label>

        <p className="text-xs">This records your judgement about the report. It does not dispatch anyone.</p>
        {error && <p role="alert" className="rounded-lg border border-critical/40 bg-critical/10 px-3 py-2 text-red-300">{error}</p>}
      </div>
    </Modal>
  )
}