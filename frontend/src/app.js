import { createSSRApp } from 'vue'
import App from './App.vue'
import { createAppRouter } from './router/index.js'
import { AppStateKey, createAppState } from './state/appState.js'

export function createVelmoraApp({ initialState = {}, head }) {
  const app = createSSRApp(App)
  const router = createAppRouter()
  const state = createAppState(initialState)
  app.provide(AppStateKey, state)
  app.use(router)
  app.use(head)
  return { app, router, state, head }
}
