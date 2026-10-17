import { reactive } from 'vue'

export const AppStateKey = Symbol('AppState')

export function createAppState(initial = {}) {
  return reactive({
    pageData: initial.pageData || {},
    authUser: initial.authUser || null,
    apiOnline: initial.apiOnline !== false,
    siteUrl: initial.siteUrl || '',
    runtimeConfig: initial.runtimeConfig || {},
    cspNonce: initial.cspNonce || '',
    iconLibrary: initial.iconLibrary || initial.pageData?.storeConfig?.icons || [],
    modal: null,
    toast: null
  })
}
