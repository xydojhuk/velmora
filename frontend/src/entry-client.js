import { createHead } from '@unhead/vue/client'
import { createVelmoraApp } from './app.js'
import { authApi } from './api/services.js'

const initialState = window.__INITIAL_STATE__ || {}
const head = createHead()
const { app, router, state } = createVelmoraApp({ initialState, head })

let authChecked = Boolean(state.authUser)

router.beforeEach(async to => {
  if (!to.meta.auth) return true
  if (!authChecked) {
    try {
      state.authUser = await authApi.me()
    } catch {
      state.authUser = null
    }
    authChecked = true
  }
  if (!state.authUser) return { name: 'login', query: { next: to.fullPath } }
  if (to.meta.adminOnly && state.authUser.role !== 'admin') return { name: 'admin-dashboard' }
  return true
})

router.beforeEach(to => {
  if (to.name === 'login' && state.authUser) return { name: 'admin-dashboard' }
  return true
})


window.addEventListener('velmora:auth-expired', () => {
  state.authUser = null
  authChecked = true
  if (router.currentRoute.value.meta.auth) {
    router.replace({ name: 'login', query: { next: router.currentRoute.value.fullPath } })
  }
})

async function mountApplication() {
  await router.isReady()
  app.mount('#app')
  try {
    if (document.fonts?.ready) await Promise.race([document.fonts.ready, new Promise(resolve => setTimeout(resolve, 1400))])
  } catch {}
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      clearTimeout(window.__VELMORA_BOOT_FALLBACK__)
      document.documentElement.classList.add('velmora-ready')
    })
  })
}

mountApplication()
