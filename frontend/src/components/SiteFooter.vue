<script setup>
import { computed } from 'vue'
import { VELMORA_VERSION } from '../utils/version.js'
import { RouterLink } from 'vue-router'
import { useAppState } from '../composables/useAppState.js'
import { useStoreInfo } from '../composables/useStoreInfo.js'

const props = defineProps({ products: { type: Array, default: () => [] } })
const state = useAppState()
const store = useStoreInfo()
const footer = computed(() => store.value.storefront.footer)
const header = computed(() => store.value.storefront.header)
const modals = computed(() => store.value.storefront.modals)
const platform = computed(() => store.value.storefront.platform)
const menuItems = computed(() => (header.value.nav || []).filter(item => item.enabled && !(item.key === 'about' && !modals.value.about.enabled) && !(item.key === 'shipping' && !modals.value.shipping.enabled)))
const copyright = computed(() => String(footer.value.copyright || '').replaceAll('{year}', String(new Date().getFullYear())).replaceAll('{store}', store.value.name))
const openModal = name => { state.modal = name }
</script>

<template>
  <footer class="footer" id="contacts">
    <div class="footer__inner">
      <div class="footer__brand">
        <RouterLink to="/" class="brand" :aria-label="`${store.name} — home`"><img :src="store.logoUrl" class="brand__mark" :alt="store.logoAlt"><span class="brand__copy"><strong>{{ store.name }}</strong><small v-if="store.tagline">{{ store.tagline }}</small></span></RouterLink>
        <p v-if="store.footerDescription" class="footer__description">{{ store.footerDescription }}</p>
      </div>
      <div v-if="footer.show_menu" class="footer__column"><h3 class="footer__heading">Menu</h3><nav class="footer__links ui-link-stack">
        <template v-for="item in menuItems" :key="item.key">
          <RouterLink v-if="item.key === 'home'" to="/">{{ item.label }}</RouterLink>
          <RouterLink v-else-if="item.key === 'catalog'" :to="{ name: 'home', hash: '#catalog' }">{{ item.label }}</RouterLink>
          <RouterLink v-else-if="item.key === 'faq'" :to="{ name: 'home', hash: '#faq' }">{{ item.label }}</RouterLink>
          <button v-else-if="item.key === 'about'" type="button" @click="openModal('about')">{{ item.label }}</button>
          <button v-else-if="item.key === 'shipping'" type="button" @click="openModal('delivery')">{{ item.label }}</button>
          <button v-else-if="item.key === 'contacts'" type="button" @click="openModal('contacts')">{{ item.label }}</button>
        </template>
      </nav></div>
      <div v-if="footer.show_products" class="footer__column"><h3 class="footer__heading">Products</h3><div class="footer__links ui-link-stack"><RouterLink v-for="product in props.products" :key="product.slug" :to="`/product/${product.slug}`">{{ product.title }}</RouterLink></div></div>
      <div v-if="footer.show_contacts" class="footer__column"><h3 class="footer__heading">Contacts</h3><div class="footer__contacts ui-link-stack"><a v-if="store.phoneDisplay" :href="`tel:${store.phoneHref}`">{{ store.phoneDisplay }}</a><a v-if="store.email" :href="`mailto:${store.email}`">{{ store.email }}</a><span v-if="store.hours">{{ store.hours }}</span><span v-if="store.location">{{ store.location }}</span></div></div>
      <div v-if="footer.show_callback" class="footer__callback ui-card"><div class="footer__callback-title ui-display">{{ footer.callback_title }}</div><p class="footer__callback-text">{{ footer.callback_text }}</p><button class="btn btn-primary footer__callback-button" type="button" @click="openModal('contacts')">{{ footer.callback_button_label }}</button></div>
    </div>
    <div class="footer__bottom">
      <p v-if="copyright" class="footer__copyright">{{ copyright }}</p>
      <button class="footer__opensource" type="button" aria-haspopup="dialog" @click="openModal('velmora')">
        <span aria-hidden="true">&lt;/&gt;</span> {{ platform.footer_label }} <span class="footer__opensource-version">v{{ VELMORA_VERSION }}</span>
      </button>
    </div>
  </footer>
</template>
