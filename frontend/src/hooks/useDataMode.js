import { useSyncExternalStore } from 'react'
import { subscribe, getDataMode } from '../services/mode'

export default function useDataMode() {
  return useSyncExternalStore(subscribe, getDataMode)
}