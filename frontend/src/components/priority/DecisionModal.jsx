import { useState } from 'react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import { UrgencyBadge, ConfidenceBadge, VerificationBadge } from './ScoreBadge'
import { recordDecision } from '../../services/incidentService'
import { DECISIONS } from '../../utils/decisions'

const field = 'mt-1 w-full rounded-lg border border-navy-600 bg-navy-900 px-3 py-2 text-sm text-text-primary'
const NAME_KEY = 'crisislens_verifier_name'

function savedName() {
  try { return sessionStorage.getItem(NAME_KEY) || '' } catch { return '' }
}

// Render with key={item.incident_id} so the form resets for each incident.
export default function DecisionModal({ item, onClose, onSaved }) {
  const [status, setStatus] = useState('')
  const [note, setNote] = useState('')
  const [decidedBy, setDecidedBy] = useState(savedName)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit() {
    const chosen = DECISIONS.find((d) => d.value === status)
    if (!chosen) return setError('Choose a decision first.')
    if (chosen.needsNote && !note.trim()) return setError('Please add a note explaining this decision.')
    if (!decidedBy.trim()) return setError('Enter your name or role so the decision can be traced.')

    setSaving(true)
    setError('')
    try {
      await recordDecision(item.incident_id, {
        status,
        decided_by: decidedBy.trim(),
        note: note.trim() || undefined,
      })
      try { sessionStorage.setItem(NAME_KEY, decidedBy.trim()) } catch { /* ignore */ }
      onSaved(item)
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
      title="Record a human decision"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button loading={saving} onClick={submit}>Save decision</Button>
        </>
      }
    >
      <div className="max-h-[60vh] space-y-4 overflow-y-auto pr-1">
        <div className="rounded-lg bg-navy-900 p-3">
          <p className="font-medium text-text-primary">{item.title}</p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            <span>Urgency <UrgencyBadge value={item.urgency} /></span>
            <span>Evidence <ConfidenceBadge value={item.evidence_confidence} /></span>
            <span>Verify <VerificationBadge value={item.verification_priority} /></span>
          </div>
          <p className="mt-2 text-xs">AI suggested: {item.recommended_next_steps.join('; ')}</p>
        </div>

        <fieldset>
          <legend className="mb-1 text-sm font-medium text-text-primary">Your decision</legend>
          <div className="space-y-2">
            {DECISIONS.map((d) => (
              <label key={d.value} className="flex cursor-pointer items-start gap-3 rounded-lg border border-navy-600 p-3 has-[:checked]:border-accent has-[:checked]:bg-accent/5">
                <input type="radio" name="decision" value={d.value} checked={status === d.value} onChange={() => setStatus(d.value)} className="mt-1" />
                <span>
                  <span className="block text-sm font-medium text-text-primary">{d.title}</span>
                  <span className="block text-xs">{d.hint}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <label className="block text-text-primary">
          Note {DECISIONS.find((d) => d.value === status)?.needsNote ? '(required)' : '(optional)'}
          <textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} className={field} />
        </label>
        <label className="block text-text-primary">
          Your name or role
          <input value={decidedBy} onChange={(e) => setDecidedBy(e.target.value)} className={field} />
        </label>

        <p className="text-xs">This logs a human judgement. CrisisLens does not dispatch anyone.</p>
        {error && <p role="alert" className="rounded-lg border border-critical/40 bg-critical/10 px-3 py-2 text-red-300">{error}</p>}
      </div>
    </Modal>
  )
}