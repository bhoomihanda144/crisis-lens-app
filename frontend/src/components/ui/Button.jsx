import { Loader2 } from 'lucide-react'
import { cn } from '../../utils/cn'

const variants = {
  primary:   'text-navy-950 font-semibold hover:brightness-110 active:scale-95',
  secondary: 'text-text-primary hover:text-accent active:scale-95',
  danger:    'text-white hover:brightness-110 active:scale-95',
  ghost:     'text-text-muted hover:text-text-primary active:scale-95',
}

const variantStyles = {
  primary: {
    background: 'linear-gradient(135deg, #00e5ff 0%, #22d3ee 100%)',
    boxShadow: '0 0 16px rgba(0,229,255,0.3), 0 2px 8px rgba(0,0,0,0.3)',
    border: '1px solid rgba(0,229,255,0.4)',
  },
  secondary: {
    background: 'linear-gradient(135deg, rgba(20,36,64,0.9) 0%, rgba(12,23,43,0.95) 100%)',
    boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
    border: '1px solid rgba(0,229,255,0.15)',
  },
  danger: {
    background: 'linear-gradient(135deg, #ff3b3b 0%, #ef4444 100%)',
    boxShadow: '0 0 12px rgba(255,59,59,0.3), 0 2px 8px rgba(0,0,0,0.3)',
    border: '1px solid rgba(255,59,59,0.4)',
  },
  ghost: {
    background: 'transparent',
    border: '1px solid transparent',
  },
}

const sizes = { sm: 'px-3 py-1.5 text-xs', md: 'px-4 py-2 text-sm' }

export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon: Icon,
  children,
  className,
  disabled,
  type = 'button',
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-all duration-200',
        'disabled:cursor-not-allowed disabled:opacity-40',
        variants[variant],
        sizes[size],
        className,
      )}
      style={variantStyles[variant]}
      {...props}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : Icon && <Icon className="h-4 w-4" aria-hidden="true" />}
      {children}
    </button>
  )
}