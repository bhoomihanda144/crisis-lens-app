import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Map as MapIcon, ListChecks, Cpu, Network, ShieldAlert, FlaskConical, BadgeCheck, X, Radar, Activity } from 'lucide-react'
import { cn } from '../../utils/cn'

const NAV = [
  { to: '/',            label: 'Overview',         icon: LayoutDashboard, end: true,  tag: null },
  { to: '/map',         label: 'Incident Map',     icon: MapIcon,         end: false, tag: 'LIVE' },
  { to: '/incidents',   label: 'Incident Queue',   icon: ListChecks,      end: false, tag: null },
  { to: '/analysis',    label: 'AI Analysis',      icon: Cpu,             end: false, tag: 'AI' },
  { to: '/graph',       label: 'Evidence Graph',   icon: Network,         end: false, tag: 'DAG' },
  { to: '/priority',    label: 'Rescue Priority',  icon: ShieldAlert,     end: false, tag: 'LIVE' },
  { to: '/simulation',  label: 'What-if Sim',      icon: FlaskConical,    end: false, tag: '3D' },
  { to: '/verification',label: 'Verify Centre',    icon: BadgeCheck,      end: false, tag: null },
]

const tagColors = {
  LIVE: 'text-verified bg-verified/10 ring-verified/30',
  AI:   'text-accent bg-accent/10 ring-accent/30',
  DAG:  'text-accent-blue bg-accent-blue/10 ring-accent-blue/30',
  '3D': 'text-amber-300 bg-amber-300/10 ring-amber-300/30',
}

export default function Sidebar({ open, onClose }) {
  return (
    <>
      {open && (
        <div className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm lg:hidden" onClick={onClose} aria-hidden="true" />
      )}
      <aside
        aria-label="Primary navigation"
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col transition-transform duration-300 ease-out lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
        style={{
          background: 'linear-gradient(180deg, rgba(6,13,26,0.99) 0%, rgba(9,18,34,0.99) 100%)',
          borderRight: '1px solid rgba(0,229,255,0.1)',
          boxShadow: '4px 0 32px rgba(0,0,0,0.6), inset -1px 0 0 rgba(0,229,255,0.05)',
        }}
      >
        {/* Logo area */}
        <div className="flex h-[72px] items-center justify-between px-4"
          style={{ borderBottom: '1px solid rgba(0,229,255,0.1)' }}>
          <div className="flex items-center gap-3">
            <div className="relative flex h-9 w-9 items-center justify-center rounded-lg"
              style={{
                background: 'linear-gradient(135deg, rgba(0,229,255,0.15) 0%, rgba(0,229,255,0.05) 100%)',
                border: '1px solid rgba(0,229,255,0.3)',
                boxShadow: '0 0 16px rgba(0,229,255,0.2)',
              }}>
              <Radar className="h-5 w-5 text-accent" aria-hidden="true" />
              <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-verified animate-pulse-green" />
            </div>
            <div className="leading-tight">
              <p className="font-tactical text-sm font-bold text-text-primary tracking-wider">CrisisLens</p>
              <p className="text-[9px] uppercase tracking-widest text-text-dim">Intelligence Platform</p>
            </div>
          </div>
          <button onClick={onClose} aria-label="Close navigation"
            className="rounded-md p-1.5 text-text-muted hover:bg-navy-700 hover:text-text-primary lg:hidden transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Section label */}
        <div className="px-4 pt-4 pb-1">
          <p className="text-[9px] font-tactical font-semibold uppercase tracking-widest text-text-dim">Navigation</p>
        </div>

        {/* Nav links */}
        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-3">
          {NAV.map(({ to, label, icon: Icon, end, tag }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  'group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'text-accent'
                    : 'text-text-muted hover:text-text-primary',
                )
              }
              style={({ isActive }) => isActive ? {
                background: 'linear-gradient(90deg, rgba(0,229,255,0.1) 0%, transparent 100%)',
                borderLeft: '2px solid rgba(0,229,255,0.7)',
                boxShadow: 'inset 0 0 20px rgba(0,229,255,0.03)',
                paddingLeft: '10px',
              } : {
                borderLeft: '2px solid transparent',
              }}
            >
              {({ isActive }) => (
                <>
                  <Icon className={cn('h-4 w-4 shrink-0 transition-all duration-200', isActive ? 'text-accent drop-shadow-[0_0_6px_rgba(0,229,255,0.8)]' : 'text-text-dim group-hover:text-text-muted')} aria-hidden="true" />
                  <span className="flex-1 truncate">{label}</span>
                  {tag && (
                    <span className={cn('rounded px-1.5 py-0.5 text-[9px] font-tactical font-bold tracking-wider ring-1 ring-inset', tagColors[tag])}>
                      {tag}
                    </span>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* System status at bottom */}
        <div className="p-3" style={{ borderTop: '1px solid rgba(0,229,255,0.08)' }}>
          <div className="rounded-lg p-3" style={{ background: 'rgba(0,230,118,0.05)', border: '1px solid rgba(0,230,118,0.1)' }}>
            <div className="flex items-center gap-2 mb-1">
              <Activity className="h-3.5 w-3.5 text-verified" />
              <span className="text-[10px] font-tactical font-semibold text-verified tracking-wider">ALL SYSTEMS NOMINAL</span>
            </div>
            <p className="text-[10px] text-text-dim leading-relaxed">
              AI output is advisory only. Human responders make every dispatch decision.
            </p>
          </div>
        </div>
      </aside>
    </>
  )
}