import { cn } from '../../utils/cn'

// tabs: [{ id, label, count? }]
export default function Tabs({ tabs, value, onChange, label = 'Sections' }) {
  return (
    <div role="tablist" aria-label={label} className="mb-4 flex flex-wrap gap-1 border-b border-navy-700">
      {tabs.map((tab) => {
        const active = tab.id === value
        return (
          <button
            key={tab.id}
            role="tab"
            type="button"
            aria-selected={active}
            onClick={() => onChange(tab.id)}
            className={cn(
              '-mb-px flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors',
              active ? 'border-accent text-accent' : 'border-transparent text-text-muted hover:text-text-primary',
            )}
          >
            {tab.label}
            {tab.count !== undefined && <span className="rounded bg-navy-700 px-1.5 text-xs text-text-primary">{tab.count}</span>}
          </button>
        )
      })}
    </div>
  )
}