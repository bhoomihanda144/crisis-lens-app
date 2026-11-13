import { cn } from '../../utils/cn'

// columns: [{ key, header, render?(row), className? }]
export default function Table({ columns, rows, rowKey, onRowClick, caption }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-navy-700">
      <table className="w-full text-left text-sm">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead className="bg-navy-900 text-xs uppercase tracking-wide text-text-muted">
          <tr>
            {columns.map((col) => (
              <th key={col.key} scope="col" className={cn('px-4 py-3 font-medium', col.className)}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-navy-700 bg-navy-800">
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              onKeyDown={onRowClick ? (e) => e.key === 'Enter' && onRowClick(row) : undefined}
              tabIndex={onRowClick ? 0 : undefined}
              className={cn(onRowClick && 'cursor-pointer hover:bg-navy-700/60')}
            >
              {columns.map((col) => (
                <td key={col.key} className={cn('px-4 py-3 align-top', col.className)}>
                  {col.render ? col.render(row) : row[col.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}