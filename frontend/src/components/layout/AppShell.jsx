import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import useDataMode from '../../hooks/useDataMode'

export default function AppShell() {
  const mode = useDataMode()
  const [navOpen, setNavOpen] = useState(false)

  return (
    <div className="relative min-h-screen" style={{ background: '#03070f' }}>
      {/* Global background grid (behind everything) */}
      <div className="pointer-events-none fixed inset-0 z-0"
        style={{
          backgroundImage: 'linear-gradient(rgba(0,229,255,0.013) 1px, transparent 1px), linear-gradient(90deg, rgba(0,229,255,0.013) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }} />

      <a href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-[70] focus:rounded focus:bg-accent focus:px-3 focus:py-1 focus:text-navy-950">
        Skip to content
      </a>
      <Sidebar open={navOpen} onClose={() => setNavOpen(false)} />
      <div className="relative z-10 lg:pl-64">
        <Header onMenu={() => setNavOpen(true)} />
        {mode === 'demo' && (
          <div className="flex items-center gap-3 px-4 py-2 text-xs text-orange-200"
            style={{ background: 'linear-gradient(90deg, rgba(255,140,0,0.1) 0%, rgba(255,140,0,0.05) 100%)', borderBottom: '1px solid rgba(255,140,0,0.2)' }}>
            <span className="font-tactical font-bold tracking-wider text-orange-400">◈ DEMO MODE</span>
            <span className="text-text-dim">·</span>
            Simulated data only — not live emergencies. AI recommendations support human responders and are not dispatch decisions.
          </div>
        )}
        <main id="main" className="mx-auto max-w-7xl p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}