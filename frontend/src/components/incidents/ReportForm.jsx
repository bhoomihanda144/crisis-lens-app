import { useState } from 'react'
import Modal from '../ui/Modal'
import Button from '../ui/Button'
import { createReport } from '../../services/reportService'

const PRESETS = {
  bellandur: { label: 'Lake Road, Bellandur', lat: '12.9304', lng: '77.6784' },
  koramangala: { label: '4th Block, Koramangala', lat: '12.9352', lng: '77.6245' },
  whitefield: { label: 'Main Road, Whitefield', lat: '12.9698', lng: '77.7500' },
  custom: { label: '', lat: '', lng: '' },
}
const SOURCE_TYPES = ['citizen', 'social_media', 'news', 'official', 'sensor', 'responder']
const field = 'mt-1 w-full rounded-lg border border-navy-600 bg-navy-900 px-3 py-2 text-sm'

export default function ReportForm({ open, onClose, onCreated }) {
  const [text, setText] = useState('')
  const [sourceType, setSourceType] = useState('citizen')
  const [sourceName, setSourceName] = useState('')
  const [preset, setPreset] = useState('bellandur')
  const [location, setLocation] = useState(PRESETS.bellandur)
  const [forwardedFrom, setForwardedFrom] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [detectingLoc, setDetectingLoc] = useState(false)

  function autoDetectLocation() {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser.')
      return
    }
    setDetectingLoc(true)
    setError('')
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocation({
          label: 'Current Device GPS Location',
          lat: pos.coords.latitude.toFixed(4),
          lng: pos.coords.longitude.toFixed(4),
        })
        setPreset('custom')
        setDetectingLoc(false)
      },
      () => {
        setError('Location permission denied or unavailable. Using preset instead.')
        setDetectingLoc(false)
      },
      { timeout: 8000 }
    )
  }

  function choosePreset(key) {
    setPreset(key)
    setLocation(PRESETS[key])
  }

  function reset() {
    setText('')
    setSourceType('citizen')
    setSourceName('')
    choosePreset('bellandur')
    setForwardedFrom('')
    setError('')
  }

  async function submit() {
    const lat = Number(location.lat)
    const lng = Number(location.lng)
    if (!text.trim()) return setError('Please describe what was reported.')
    if (!location.label.trim()) return setError('Please enter a location name.')
    if (location.lat === '' || Number.isNaN(lat) || lat < -90 || lat > 90) return setError('Latitude must be a number from -90 to 90.')
    if (location.lng === '' || Number.isNaN(lng) || lng < -180 || lng > 180) return setError('Longitude must be a number from -180 to 180.')

    setSaving(true)
    setError('')
    try {
      const report = await createReport({
        text: text.trim(),
        source: { type: sourceType, name: sourceName.trim() || 'Unnamed reporter' },
        location: { lat, lng, label: location.label.trim() },
        forwarded_from: forwardedFrom.trim() || null,
      })
      onCreated(report)
      reset()
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Submit a report"
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button loading={saving} onClick={submit}>Submit report</Button>
        </>
      }
    >
      <div className="max-h-[60vh] space-y-3 overflow-y-auto pr-1">
        <label className="block text-text-primary">
          What was reported?
          <textarea rows={3} value={text} onChange={(e) => setText(e.target.value)} className={field} placeholder="Describe what the reporter saw…" />
        </label>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="block text-text-primary">
            Source type
            <select value={sourceType} onChange={(e) => setSourceType(e.target.value)} className={field}>
              {SOURCE_TYPES.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
            </select>
          </label>
          <label className="block text-text-primary">
            Source name (optional)
            <input value={sourceName} onChange={(e) => setSourceName(e.target.value)} className={field} />
          </label>
        </div>
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-text-primary text-sm">Location</span>
            <button
              type="button"
              disabled={detectingLoc}
              onClick={autoDetectLocation}
              className="text-xs text-accent hover:underline font-medium"
            >
              📍 {detectingLoc ? 'Detecting GPS...' : 'Auto-Detect GPS'}
            </button>
          </div>
          <select value={preset} onChange={(e) => choosePreset(e.target.value)} className={field}>
            <option value="bellandur">Lake Road, Bellandur</option>
            <option value="koramangala">4th Block, Koramangala</option>
            <option value="whitefield">Main Road, Whitefield</option>
            <option value="custom">Custom location…</option>
          </select>
        </div>
        <div className="grid gap-3 sm:grid-cols-3">
          <label className="block text-text-primary sm:col-span-3">
            Location name
            <input value={location.label} onChange={(e) => setLocation({ ...location, label: e.target.value })} className={field} />
          </label>
          <label className="block text-text-primary">
            Latitude
            <input value={location.lat} onChange={(e) => setLocation({ ...location, lat: e.target.value })} className={field} inputMode="decimal" />
          </label>
          <label className="block text-text-primary">
            Longitude
            <input value={location.lng} onChange={(e) => setLocation({ ...location, lng: e.target.value })} className={field} inputMode="decimal" />
          </label>
        </div>
        <label className="block text-text-primary">
          Forwarded from report ID (optional)
          <input value={forwardedFrom} onChange={(e) => setForwardedFrom(e.target.value)} className={field} placeholder="for example rpt_001" />
        </label>
        {error && <p role="alert" className="rounded-lg border border-critical/40 bg-critical/10 px-3 py-2 text-red-300">{error}</p>}
      </div>
    </Modal>
  )
}