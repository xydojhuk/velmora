<script setup>
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import SiteHeader from '../components/SiteHeader.vue'
import SiteFooter from '../components/SiteFooter.vue'
import MaintenanceScreen from '../components/MaintenanceScreen.vue'
import { publicApi } from '../api/services.js'
import { useAppState } from '../composables/useAppState.js'
import { useStoreInfo } from '../composables/useStoreInfo.js'
import { fallbackProducts } from '../state/fallback.js'

const state = useAppState()
const store = useStoreInfo()
const products = computed(() => Array.isArray(state.pageData.products) ? state.pageData.products : fallbackProducts)

const cssVarMap = {
  '--bg': 'background', '--bg-soft': 'background_soft', '--surface': 'surface', '--surface-2': 'surface_alt', '--surface-3': 'surface_alt',
  '--primary': 'primary', '--primary-hover': 'accent', '--accent': 'accent', '--accent-soft': 'accent_soft', '--accent-dark': 'primary',
  '--text': 'text', '--text-secondary': 'text_secondary', '--border': 'border', '--border-light': 'accent_soft', '--border-accent': 'accent_soft'
}
const previousRootVars = new Map()
function applyRootTheme(theme) {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  for (const [cssVar, key] of Object.entries(cssVarMap)) {
    if (!previousRootVars.has(cssVar)) previousRootVars.set(cssVar, root.style.getPropertyValue(cssVar))
    root.style.setProperty(cssVar, theme[key])
  }
}
watch(() => store.value.storefront.theme, value => applyRootTheme(value), { deep: true, immediate: true })
onBeforeUnmount(() => {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  for (const [cssVar, previous] of previousRootVars.entries()) {
    if (previous) root.style.setProperty(cssVar, previous)
    else root.style.removeProperty(cssVar)
  }
})

const themeStyle = computed(() => {
  const theme = store.value.storefront.theme
  return {
    '--bg': theme.background,
    '--bg-soft': theme.background_soft,
    '--surface': theme.surface,
    '--surface-2': theme.surface_alt,
    '--surface-3': theme.surface_alt,
    '--primary': theme.primary,
    '--primary-hover': theme.accent,
    '--accent': theme.accent,
    '--accent-soft': theme.accent_soft,
    '--accent-dark': theme.primary,
    '--text': theme.text,
    '--text-secondary': theme.text_secondary,
    '--border': theme.border,
    '--border-light': theme.accent_soft,
    '--border-accent': theme.accent_soft
  }
})

onMounted(async () => {
  if (state.pageData.storeConfig) return
  try {
    state.pageData.storeConfig = await publicApi.config()
    state.iconLibrary = state.pageData.storeConfig?.icons || []
  } catch {
    state.apiOnline = false
  }
})
</script>

<template>
  <div class="page" :style="themeStyle">
    <SiteHeader />
    <main><MaintenanceScreen v-if="store.maintenanceMode" /><slot v-else /></main>
    <SiteFooter :products="products" />
  </div>
</template>
