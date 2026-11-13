import { cn } from '../../utils/cn'

const tones = {
  critical: 'bg-critical/10 text-red-300 ring-critical/40',
  verify:   'bg-verify/10 text-orange-300 ring-verify/40',
  verified: 'bg-verified/10 text-green-300 ring-verified/30',
  info:     'bg-accent/8 text-cyan-300 ring-accent/25',
  neutral:  'bg-navy-700/80 text-slate-300 ring-navy-600/60',
}

const glows = {
  critical: '0 0 8px rgba(255,59,59,0.3)',
  verify:   '0 0 8px rgba(249,115,22,0.25)',
  verified: '0 0 8px rgba(0,230,118,0.25)',
  info:     '0 0 8px rgba(0,229,255,0.2)',
  neutral:  'none',
}

export default function Badge({ tone = 'neutral', children, className }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset font-tactical tracking-wider',
        tones[tone],
        className,
      )}
      style={{ boxShadow: glows[tone] }}
    >
      {children}
    </span>
  )
}