import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Map as MapIcon, ListChecks, Cpu, Network, ShieldAlert, FlaskConical, BadgeCheck, X, Radar } from 'lucide-react'
import { cn } from '../../utils/cn'

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/map', label: 'Incident Map', icon: MapIcon },
  { to: '/incidents', label: 'Incident Queue', icon: ListChecks },
  { to: '/analysis', label: 'AI Analysis', icon: Cpu },
  { to: '/graph', label: 'Evidence Graph', icon: Network },
  { to: '/priority', label: 'Rescue Priority', icon: ShieldAlert },
  { to: '/simulation', label: 'What-if Simulation', icon: FlaskConical },
  { to: '/verification', label: 'Verification Centre', icon: BadgeCheck },
]

export default function Sidebar({ open, onClose }) {
  return (
    <>
      {open && <div className="fixed inset-0 z-40 bg-black/60 lg:hidden" onClick={onClose} aria-hidden="true" />}
      <aside
        aria-label="Primary"
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-navy-700 bg-navy-900 transition-transform duration-200 lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-14 items-center justify-between border-b border-navy-700 px-4">
          <div className="flex items-center gap-2">
            <Radar className="h-6 w-6 text-accent" aria-hidden="true" />
            <div className="leading-tight">
              <p className="font-bold">CrisisLens</p>
              <p className="text-[10px] uppercase tracking-wider text-text-muted">Trust-aware intelligence</p>
            </div>
          </div>
          <button onClick={onClose} aria-label="Close navigation" className="rounded-md p-1 text-text-muted hover:bg-navy-700 lg:hidden">
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  isActive ? 'bg-accent/10 text-accent' : 'text-text-muted hover:bg-navy-700 hover:text-text-primary',
                )
              }
            >
              <Icon className="h-5 w-5" aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>

        <p className="border-t border-navy-700 p-4 text-xs text-text-muted">
          AI output is advisory. Human responders make every dispatch decision.
        </p>
      </aside>
    </>
  )
}