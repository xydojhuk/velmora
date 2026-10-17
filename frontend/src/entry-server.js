import { renderToString } from 'vue/server-renderer'
import { createHead, renderSSRHead } from '@unhead/vue/server'
import { createVelmoraApp } from './app.js'
import { createServerApi } from './api/client.js'
import { loadSsrState } from './ssr.js'

export async function render(url, context = {}) {
  const head = createHead()
  const api = createServerApi(context.apiBaseURL || 'http://127.0.0.1:8000/api/v1', context.cookie || '')
  const initial = {
    pageData: {},
    apiOnline: true,
    siteUrl: context.siteUrl || '',
    runtimeConfig: context.runtimeConfig || {},
    cspNonce: context.cspNonce || ''
  }
  const { app, router, state } = createVelmoraApp({ initialState: initial, head })
  await router.push(url)
  await router.isReady()
  const loaded = await loadSsrState(router.currentRoute.value, api)
  state.pageData = loaded.pageData
  state.apiOnline = loaded.apiOnline
  const html = await renderToString(app)
  const headPayload = renderSSRHead(head)
  return {
    html,
    head: headPayload.headTags || '',
    state: {
      pageData: state.pageData,
      apiOnline: state.apiOnline,
      siteUrl: state.siteUrl,
      runtimeConfig: state.runtimeConfig,
      cspNonce: state.cspNonce,
      authUser: null
    },
    status: loaded.status
  }
}
