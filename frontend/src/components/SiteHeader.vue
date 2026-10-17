<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import AppIcon from './AppIcon.vue'
import { useAppState } from '../composables/useAppState.js'
import { useStoreInfo } from '../composables/useStoreInfo.js'

const route = useRoute()
const state = useAppState()
const store = useStoreInfo()
const menuOpen = ref(false)
const closeMenu = () => { menuOpen.value = false }
const openModal = name => { closeMenu(); state.modal = name }
const header = computed(() => store.value.storefront.header)
const announcement = computed(() => store.value.storefront.announcement)
const modals = computed(() => store.value.storefront.modals)
const nav = computed(() => (header.value.nav || []).filter(item => {
  if (!item.enabled) return false
  if (item.key === 'about' && !modals.value.about.enabled) return false
  if (item.key === 'shipping' && !modals.value.shipping.enabled) return false
  return true
}))

watch(menuOpen, value => { if (typeof document !== 'undefined') document.body.classList.toggle('menu-open', value) })
watch(() => route.fullPath, closeMenu)
onBeforeUnmount(() => { if (typeof document !== 'undefined') document.body.classList.remove('menu-open') })
</script>

<template>
  <header class="header">
    <div v-if="announcement.enabled && announcement.text" class="announcement">
      <span>{{ announcement.text }}</span>
      <a v-if="announcement.link_url && announcement.link_label" :href="announcement.link_url" :target="announcement.link_url.startsWith('https://') ? '_blank' : undefined" rel="noopener">{{ announcement.link_label }}</a>
    </div>
    <div class="header__inner">
      <RouterLink to="/" class="brand" :aria-label="`${store.name} — home`">
        <img :src="store.logoUrl" class="brand__mark" :alt="store.logoAlt">
        <span class="brand__copy"><strong>{{ store.name }}</strong><small v-if="store.tagline">{{ store.tagline }}</small></span>
      </RouterLink>
      <nav class="header__links" aria-label="Main navigation" @click.self="closeMenu">
        <template v-for="item in nav" :key="item.key">
          <RouterLink v-if="item.key === 'home'" to="/" class="header__link" active-class="active" @click="closeMenu">{{ item.label }}</RouterLink>
          <RouterLink v-else-if="item.key === 'catalog'" :to="{ name: 'home', hash: '#catalog' }" class="header__link" @click="closeMenu">{{ item.label }}</RouterLink>
          <RouterLink v-else-if="item.key === 'faq'" :to="{ name: 'home', hash: '#faq' }" class="header__link" @click="closeMenu">{{ item.label }}</RouterLink>
          <button v-else-if="item.key === 'about'" class="header__link header__link-button" type="button" @click="openModal('about')">{{ item.label }}</button>
          <button v-else-if="item.key === 'shipping'" class="header__link header__link-button" type="button" @click="openModal('delivery')">{{ item.label }}</button>
          <button v-else-if="item.key === 'contacts'" class="header__link header__link-button" type="button" @click="openModal('contacts')">{{ item.label }}</button>
        </template>
      </nav>
      <div class="header__actions">
        <a v-if="header.show_phone && store.phoneDisplay" :href="`tel:${store.phoneHref}`" class="phone">
          <AppIcon name="phone" class="phone__icon" :size="28" stroke="1.7" />
          <span class="phone__copy"><strong>{{ store.phoneDisplay }}</strong><small v-if="header.show_hours && store.hours" :title="store.hours">{{ store.hours }}</small></span>
        </a>
        <button v-if="header.show_consultation" class="btn header__consultation" type="button" @click="openModal('contacts')">{{ header.consultation_label }}</button>
      </div>
      <button class="header__menu-toggle" type="button" :aria-label="menuOpen ? 'Close menu' : 'Open menu'" :aria-expanded="menuOpen" @click="menuOpen = !menuOpen"><span class="header__menu-line"></span><span class="header__menu-line"></span><span class="header__menu-line"></span></button>
    </div>
  </header>
</template>
