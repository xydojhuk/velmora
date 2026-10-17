import { inject } from 'vue'
import { AppStateKey } from '../state/appState.js'

export function useAppState() {
  const state = inject(AppStateKey)
  if (!state) throw new Error('App state is not available')
  return state
}
