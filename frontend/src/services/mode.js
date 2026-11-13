// Holds "demo" (simulated data) or "live" (real backend). Survives page refresh.
const KEY = 'crisislens_data_mode'
const listeners = new Set()

function initialMode() {
  try {
    const saved = localStorage.getItem(KEY)
    if (saved === 'demo' || saved === 'live') return saved
  } catch {
    /* storage unavailable, ignore */
  }
  return import.meta.env.VITE_USE_MOCK === 'false' ? 'live' : 'demo'
}

let mode = initialMode()

export const getDataMode = () => mode
export const isDemo = () => mode === 'demo'

export function setDataMode(next) {
  mode = next
  try {
    localStorage.setItem(KEY, next)
  } catch {
    /* ignore */
  }
  listeners.forEach((listener) => listener())
}

export function subscribe(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}