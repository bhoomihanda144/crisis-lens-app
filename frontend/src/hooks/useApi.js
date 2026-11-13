import { useCallback, useEffect, useState } from 'react'
import useDataMode from './useDataMode'

// Usage: const { data, loading, error, reload } = useApi(() => listReports({ q }), [q])
export default function useApi(fetcher, deps = []) {
  const mode = useDataMode()
  const [state, setState] = useState({ data: null, loading: true, error: null })
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let cancelled = false
    setState((prev) => ({ ...prev, loading: true, error: null }))
    fetcher()
      .then((data) => { if (!cancelled) setState({ data, loading: false, error: null }) })
      .catch((error) => { if (!cancelled) setState({ data: null, loading: false, error }) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, mode, tick])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { ...state, reload }
}