import { Handle, Position } from '@xyflow/react'
import { ROLE_STYLE } from './roleStyle'
import { timeAgo } from '../../utils/format'
import { cn } from '../../utils/cn'

export default function ReportNode({ data, selected }) {
  const style = ROLE_STYLE[data.role] || ROLE_STYLE.duplicate
  return (
    <div
      className={cn('w-64 rounded-lg border bg-navy-800 px-3 py-2 text-left shadow-lg', selected && 'ring-2 ring-accent')}
      style={{ borderColor: style.color, borderLeftWidth: 4 }}
    >
      <Handle type="target" position={Position.Right} style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Left} style={{ opacity: 0 }} />
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-xs text-accent">{data.report_id}</span>
        <span
          className="rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase"
          style={{ background: `${style.color}26`, color: style.color }}
        >
          {style.label}
        </span>
      </div>
      <p className="mt-1 line-clamp-2 text-sm text-text-primary">{data.label}</p>
      <p className="mt-1 text-xs text-text-muted">
        {data.source_name} · {timeAgo(data.timestamp)}
      </p>
    </div>
  )
}