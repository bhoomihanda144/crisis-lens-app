import { useEffect, useState } from 'react'
import { Menu } from 'lucide-react'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import Modal from '../ui/Modal'
import { DATA_ORIGIN } from '../../data/mockData'
import useDataMode from '../../hooks/useDataMode'
import { setDataMode } from '../../services/mode'
import { checkConnection, API_BASE_URL } from '../../services/api'

function Clock() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30000)
    return () => clearInterval(id)
  }, [])
  return (
    <time dateTime={now.toISOString()} className="hidden font-mono text-sm text-text-muted sm:block">
      {now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
    </time>
  )
}

export default function Header({ onMenu }) {
  const mode = useDataMode()
  const [checking, setChecking] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  async function switchToLive() {
    setChecking(true)
    try {
      await checkConnection()
      setDataMode('live')
    } catch (err) {
      setErrorMessage(err.message)
    } finally {
      setChecking(false)
    }
  }

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-navy-700 bg-navy-900/90 px-4 backdrop-blur">
      <button onClick={onMenu} aria-label="Open navigation" className="rounded-md p-2 text-text-muted hover:bg-navy-700 lg:hidden">
        <Menu className="h-5 w-5" />
      </button>
      <div className="flex-1" />
      {mode === 'demo' ? <Badge tone="verify">Data: {DATA_ORIGIN}</Badge> : <Badge tone="info">Live backend</Badge>}
      {mode === 'demo' ? (
        <Button size="sm" variant="secondary" loading={checking} onClick={switchToLive}>Use live backend</Button>
      ) : (
        <Button size="sm" variant="secondary" onClick={() => setDataMode('demo')}>Use demo data</Button>
      )}
      <Clock />

      <Modal
        open={Boolean(errorMessage)}
        onClose={() => setErrorMessage('')}
        title="Could not switch to the live backend"
        footer={<Button onClick={() => setErrorMessage('')}>Close</Button>}
      >
        <p>{errorMessage}</p>
        <p className="mt-2">Still in Demo Mode. Backend address: <span className="font-mono text-accent">{API_BASE_URL}</span></p>
      </Modal>
    </header>
  )
}