import { cn } from '../../utils/cn'

export function Card({ className, children, glow = false, ...props }) {
  return (
    <div
      className={cn('rounded-xl p-4 transition-all duration-300 bracket-corner', className)}
      style={{
        background: 'linear-gradient(135deg, rgba(12,23,43,0.92) 0%, rgba(9,18,34,0.96) 100%)',
        border: '1px solid rgba(0,229,255,0.1)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        boxShadow: glow
          ? '0 0 0 1px rgba(0,229,255,0.08), 0 8px 32px rgba(0,0,0,0.5), 0 0 20px rgba(0,229,255,0.08)'
          : '0 4px 20px rgba(0,0,0,0.4)',
      }}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action }) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div>
        <h2 className="text-base font-semibold text-text-primary">{title}</h2>
        {subtitle && <p className="mt-0.5 text-sm text-text-muted">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export default Card