import { AlertTriangle } from 'lucide-react'
import Button from './Button'

export default function ErrorState({ title = 'Something went wrong', message, onRetry }) {
  return (
    <div role="alert" className="flex flex-col items-center justify-center rounded-xl border border-critical/40 bg-critical/5 px-6 py-10 text-center">
      <AlertTriangle className="h-10 w-10 text-critical" aria-hidden="true" />
      <h3 className="mt-3 text-base font-semibold">{title}</h3>
      {message && <p className="mt-1 max-w-md text-sm text-text-muted">{message}</p>}
      {onRetry && (
        <Button variant="secondary" className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}