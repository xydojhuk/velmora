<script setup>
import { computed, onMounted, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import StoreLayout from './layouts/StoreLayout.vue'
import AuthLayout from './layouts/AuthLayout.vue'
import AdminLayout from './layouts/AdminLayout.vue'
import InstallerLayout from './layouts/InstallerLayout.vue'
import StoreModal from './components/StoreModal.vue'
import GlobalHead from './components/GlobalHead.vue'
import AppToast from './components/AppToast.vue'
import { publicApi } from './api/services.js'
import { useAppState } from './composables/useAppState.js'

const route = useRoute()
const state = useAppState()
const layouts = { store: StoreLayout, auth: AuthLayout, admin: AdminLayout, installer: InstallerLayout }
const layout = computed(() => layouts[route.meta.layout] || StoreLayout)

function makeVisitSessionId() {
  if (typeof globalThis.crypto?.randomUUID === 'function') return globalThis.crypto.randomUUID()
  if (typeof globalThis.crypto?.getRandomValues === 'function') {
    const bytes = new Uint8Array(16)
    globalThis.crypto.getRandomValues(bytes)
    bytes[6] = (bytes[6] & 0x0f) | 0x40
    bytes[8] = (bytes[8] & 0x3f) | 0x80
    const hex = [...bytes].map(value => value.toString(16).padStart(2, '0')).join('')
    return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`
  }
  return `local-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`
}

function sessionId() {
  if (typeof window === 'undefined') return ''
  let id = localStorage.getItem('velmora_visit_session')
  if (!id) {
    id = makeVisitSessionId()
    localStorage.setItem('velmora_visit_session', id)
  }
  return id
}

function trackVisit() {
  if (route.meta.layout !== 'store') return
  if (typeof window !== 'undefined') {
    if (typeof window.gtag === 'function' && state.runtimeConfig.googleAnalyticsId) window.gtag('event', 'page_view', { page_path: route.fullPath })
    if (state.runtimeConfig.googleTagManagerId && Array.isArray(window.dataLayer)) window.dataLayer.push({ event: 'virtual_page_view', page_path: route.fullPath })
  }
  publicApi.visit({
    page: route.fullPath.slice(0, 300),
    referrer: typeof document !== 'undefined' ? document.referrer.slice(0, 1000) || null : null,
    session_id: sessionId()
  })
}

onMounted(trackVisit)
watch(() => route.fullPath, trackVisit)
</script>

<template>
  <GlobalHead />
  <component :is="layout">
    <RouterView />
  </component>
  <StoreModal />
  <AppToast />
</template>
