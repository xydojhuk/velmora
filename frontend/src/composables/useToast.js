import { useAppState } from './useAppState.js'

export function useToast() {
  const state = useAppState()
  let timer
  const show = (message, type = 'success') => {
    state.toast = { message, type }
    clearTimeout(timer)
    timer = setTimeout(() => {
      state.toast = null
    }, 4200)
  }
  return { show }
}
