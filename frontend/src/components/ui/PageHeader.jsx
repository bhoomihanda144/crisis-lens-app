export default function PageHeader({ title, description, actions, icon: Icon }) {
  return (
    <div className="mb-6 animate-fade-in-up">
      {/* Decorative top line */}
      <div className="mb-4 flex items-center gap-3">
        <div className="h-px flex-1" style={{ background: 'linear-gradient(90deg, rgba(0,229,255,0.4) 0%, transparent 100%)' }} />
        <span className="font-tactical text-[9px] font-semibold uppercase tracking-widest text-text-dim">CrisisLens · Command Interface</span>
        <div className="h-px flex-1" style={{ background: 'linear-gradient(-90deg, rgba(0,229,255,0.4) 0%, transparent 100%)' }} />
      </div>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          {Icon && (
            <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
              style={{ background: 'linear-gradient(135deg, rgba(0,229,255,0.12) 0%, rgba(0,229,255,0.04) 100%)', border: '1px solid rgba(0,229,255,0.2)', boxShadow: '0 0 16px rgba(0,229,255,0.1)' }}>
              <Icon className="h-5 w-5 text-accent" />
            </div>
          )}
          <div>
            <h1 className="font-tactical text-2xl font-bold tracking-wide text-text-primary"
              style={{ textShadow: '0 0 20px rgba(0,229,255,0.2)' }}>
              {title}
            </h1>
            {description && (
              <p className="mt-1 max-w-2xl text-sm text-text-muted leading-relaxed">{description}</p>
            )}
          </div>
        </div>
        {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
      </div>
    </div>
  )
}