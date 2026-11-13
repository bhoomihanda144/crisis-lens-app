import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import useDataMode from '../../hooks/useDataMode'

export default function AppShell() {
  const mode = useDataMode()
  const [navOpen, setNavOpen] = useState(false)

  return (
    <div className="min-h-screen bg-navy-950">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-[70] focus:rounded focus:bg-accent focus:px-3 focus:py-1 focus:text-navy-950"
      >
        Skip to content
      </a>
      <Sidebar open={navOpen} onClose={() => setNavOpen(false)} />
      <div className="lg:pl-64">
        <Header onMenu={() => setNavOpen(true)} />
        {mode === 'demo' && (
          <div className="border-b border-verify/30 bg-verify/10 px-4 py-1.5 text-xs text-orange-200">
            SIMULATED DATA. These are demo records, not live emergencies. AI recommendations support human responders and are not dispatch decisions.
          </div>
        )}
        <main id="main" className="mx-auto max-w-7xl p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}