import { useEffect, useState } from 'react'
import { Menu, Radio, Zap, Shield } from 'lucide-react'
import Button from '../ui/Button'
import Modal from '../ui/Modal'
import { DATA_ORIGIN } from '../../data/mockData'
import useDataMode from '../../hooks/useDataMode'
import { setDataMode } from '../../services/mode'
import { checkConnection, API_BASE_URL } from '../../services/api'

const TICKER_EVENTS = [
  '⬤ FLOOD ALERT · Bellandur Lake sector water level +2.4m',
  '⬤ RESCUE DISPATCH · Team Alpha en route to Whitefield',
  '⬤ EVIDENCE CONFIRMED · Incident INC-004 upgraded to CRITICAL',
  '⬤ SYSTEM NOMINAL · All 10 endpoints healthy · Latency 42ms',
  '⬤ AI ENGINE · 6-stage analysis pipeline active · Confidence 87%',
  '⬤ VERIFICATION · 3 incidents awaiting human review',
  '⬤ SIMULATION · What-if engine on standby · Last run 04:12 UTC',
]

function LiveTicker() {
  const text = TICKER_EVENTS.join('   ·   ') + '   ·   ' + TICKER_EVENTS.join('   ·   ')
  return (
    <div className="hidden lg:flex flex-1 overflow-hidden relative mx-4">
      <div className="absolute inset-y-0 left-0 w-8 z-10"
        style={{ background: 'linear-gradient(90deg, #060d1a 0%, transparent 100%)' }} />
      <div className="absolute inset-y-0 right-0 w-8 z-10"
        style={{ background: 'linear-gradient(-90deg, #060d1a 0%, transparent 100%)' }} />
      <div className="animate-ticker whitespace-nowrap font-mono text-[10px] text-text-dim tracking-wider flex items-center gap-0">
        {text}
      </div>
    </div>
  )
}

function DualClock() {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const utcTime = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZone: 'UTC' })
  const istTime = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZone: 'Asia/Kolkata' })
  return (
    <div className="hidden sm:flex flex-col items-end gap-0.5">
      <div className="flex items-center gap-1.5">
        <span className="text-[9px] font-tactical text-text-dim tracking-widest">UTC</span>
        <time className="font-mono text-xs text-accent font-semibold tabular-nums">{utcTime}</time>
      </div>
      <div className="flex items-center gap-1.5">
        <span className="text-[9px] font-tactical text-text-dim tracking-widest">IST</span>
        <time className="font-mono text-xs text-text-muted tabular-nums">{istTime}</time>
      </div>
    </div>
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

  const isLive = mode === 'live'

  return (
    <>
      {/* Top status strip */}
      <div className="sticky top-0 z-40 h-5 flex items-center justify-between px-4 overflow-hidden"
        style={{ background: 'linear-gradient(90deg, rgba(0,229,255,0.07) 0%, rgba(0,0,0,0) 40%, rgba(0,230,118,0.05) 100%)', borderBottom: '1px solid rgba(0,229,255,0.08)' }}>
        <div className="flex items-center gap-2">
          <span className="animate-dot-blink h-1.5 w-1.5 rounded-full bg-verified inline-block" />
          <span className="font-mono text-[9px] text-text-dim tracking-widest uppercase">Active Monitoring · Bellandur Lake · Karnataka Emergency Ops</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-mono text-[9px] text-text-dim">THREAT LVL:</span>
          <span className="font-mono text-[9px] text-critical font-bold tracking-widest">HIGH</span>
          <span className="font-mono text-[9px] text-text-dim">·</span>
          <span className="font-mono text-[9px] text-text-dim">NODES: 10/10</span>
        </div>
      </div>

      {/* Main header */}
      <header className="sticky top-5 z-30 flex h-13 items-center gap-3 px-4"
        style={{
          background: 'linear-gradient(180deg, rgba(6,13,26,0.98) 0%, rgba(9,18,34,0.95) 100%)',
          borderBottom: '1px solid rgba(0,229,255,0.12)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          boxShadow: '0 1px 0 rgba(0,229,255,0.05), 0 4px 24px rgba(0,0,0,0.5)'
        }}>

        <button onClick={onMenu} aria-label="Open navigation"
          className="rounded-md p-2 text-text-muted hover:bg-navy-700 lg:hidden transition-colors">
          <Menu className="h-5 w-5" />
        </button>

        {/* Live activity ticker */}
        <LiveTicker />

        {/* Mode toggle */}
        <div className="flex items-center gap-1 rounded-lg p-1"
          style={{ background: 'rgba(10,18,36,0.8)', border: '1px solid rgba(0,229,255,0.1)' }}>
          <button
            onClick={() => setDataMode('demo')}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-all duration-200 ${
              !isLive
                ? 'text-amber-300'
                : 'text-text-dim hover:text-text-muted'
            }`}
            style={!isLive ? { background: 'rgba(251,191,36,0.1)', boxShadow: '0 0 8px rgba(251,191,36,0.15)' } : {}}>
            <Shield className="h-3 w-3" />
            DEMO
          </button>
          <button
            onClick={isLive ? undefined : switchToLive}
            disabled={checking}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1 text-xs font-medium transition-all duration-200 ${
              isLive
                ? 'text-verified'
                : 'text-text-dim hover:text-text-muted'
            }`}
            style={isLive ? { background: 'rgba(0,230,118,0.1)', boxShadow: '0 0 8px rgba(0,230,118,0.2)' } : {}}>
            {checking ? (
              <span className="h-3 w-3 animate-spin rounded-full border border-verified border-t-transparent" />
            ) : (
              <span className={`h-1.5 w-1.5 rounded-full ${isLive ? 'bg-verified animate-dot-blink' : 'bg-text-dim'}`} />
            )}
            LIVE
          </button>
        </div>

        {/* Clock */}
        <DualClock />

        {/* System health dot */}
        <div className="hidden sm:flex items-center gap-1.5 rounded-md px-2 py-1"
          style={{ background: 'rgba(0,230,118,0.06)', border: '1px solid rgba(0,230,118,0.15)' }}>
          <Radio className="h-3.5 w-3.5 text-verified" />
          <span className="font-mono text-[10px] text-verified font-semibold">NOMINAL</span>
        </div>

        <Modal
          open={Boolean(errorMessage)}
          onClose={() => setErrorMessage('')}
          title="Could not switch to the live backend"
          footer={<Button onClick={() => setErrorMessage('')}>Close</Button>}
        >
          <p>{errorMessage}</p>
          <p className="mt-2">Still in Demo Mode. Backend: <span className="font-mono text-accent">{API_BASE_URL}</span></p>
        </Modal>
      </header>
    </>
  )
}