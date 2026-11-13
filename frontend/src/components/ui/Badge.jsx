import { cn } from '../../utils/cn'

const tones = {
  critical: 'bg-critical/15 text-red-300 ring-critical/40',
  verify: 'bg-verify/15 text-orange-300 ring-verify/40',
  verified: 'bg-verified/15 text-green-300 ring-verified/40',
  info: 'bg-accent/10 text-cyan-300 ring-accent/30',
  neutral: 'bg-navy-700 text-slate-300 ring-navy-600',
}

export default function Badge({ tone = 'neutral', children, className }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}