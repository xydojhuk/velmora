<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch, nextTick } from 'vue'
import AppIcon from './AppIcon.vue'
import { VELMORA_VERSION } from '../utils/version.js'
import { useStoreInfo } from '../composables/useStoreInfo.js'
import { useAppState } from '../composables/useAppState.js'

const state = useAppState()
const store = useStoreInfo()
const open = computed(() => Boolean(state.modal))
const modalDialog = ref(null)
let previousFocus = null
const modals = computed(() => store.value.storefront.modals)
const about = computed(() => modals.value.about)
const shipping = computed(() => modals.value.shipping)
const contacts = computed(() => modals.value.contacts)
const platform = computed(() => store.value.storefront.platform)
const repositoryUrl = computed(() => platform.value.repository_url || 'https://github.com/xydojhuk/velmora')
const template = value => String(value || '').replaceAll('{store}', store.value.name)
const padIndex = index => String(index + 1).padStart(2, '0')

const onKeyDown = event => {
  if (!open.value) return
  if (event.key === 'Escape') { event.preventDefault(); close(); return }
  if (event.key !== 'Tab' || !modalDialog.value) return
  const elements = [...modalDialog.value.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')]
  if (!elements.length) { event.preventDefault(); return }
  const first = elements[0], last = elements[elements.length - 1]
  if (event.shiftKey && (document.activeElement === first || !modalDialog.value.contains(document.activeElement))) { event.preventDefault(); last.focus() }
  else if (!event.shiftKey && (document.activeElement === last || !modalDialog.value.contains(document.activeElement))) { event.preventDefault(); first.focus() }
}
onMounted(() => { if (typeof document !== 'undefined') document.addEventListener('keydown', onKeyDown) })
watch(open, async value => {
  if (typeof document === 'undefined') return
  document.body.classList.toggle('modal-open', value)
  if (value) {
    previousFocus = document.activeElement
    await nextTick()
    modalDialog.value?.querySelector('.site-modal__close')?.focus()
  } else {
    previousFocus?.focus?.()
    previousFocus = null
  }
})
onBeforeUnmount(() => { if (typeof document !== 'undefined') document.body.classList.remove('modal-open'); document.removeEventListener('keydown', onKeyDown) })
const close = () => { state.modal = null }
</script>

<template>
  <div v-if="open" class="site-modal is-open" aria-hidden="false" @click.self="close">
    <div ref="modalDialog" class="site-modal__dialog ui-card" role="dialog" aria-modal="true" aria-labelledby="site-modal-title">
      <button class="site-modal__close" type="button" aria-label="Close" @click="close">×</button>

      <template v-if="state.modal === 'velmora'">
        <div class="velmora-about__icon" aria-hidden="true">&lt;/&gt;</div>
        <p v-if="platform.eyebrow" class="site-modal__eyebrow">{{ platform.eyebrow }}</p>
        <h2 class="site-modal__title ui-display" id="site-modal-title">{{ platform.title }}</h2>
        <p v-if="platform.description" class="site-modal__lead">{{ platform.description }}</p>
        <p class="velmora-about__version">Version <strong>v{{ VELMORA_VERSION }}</strong> · self-hosted software</p>
        <div class="velmora-about__support">
          <strong>{{ platform.support_title }}</strong>
          <p>{{ platform.support_text }}</p>
          <div class="velmora-about__links">
            <a class="btn btn-primary" :href="repositoryUrl" target="_blank" rel="noopener noreferrer">{{ platform.repository_label }} ↗</a>
            <a v-if="platform.support_url" class="btn btn-secondary" :href="platform.support_url" target="_blank" rel="noopener noreferrer">{{ platform.support_label }} ↗</a>
          </div>
        </div>
      </template>

      <template v-else-if="state.modal === 'about' && about.enabled">
        <p v-if="about.eyebrow" class="site-modal__eyebrow">{{ template(about.eyebrow) }}</p>
        <h2 class="site-modal__title ui-display" id="site-modal-title">{{ about.title }}</h2>
        <p v-if="about.lead" class="site-modal__lead">{{ about.lead }}</p>
        <div v-if="about.stats.length" class="site-modal__stats"><div v-for="item in about.stats" :key="`${item.value}-${item.label}`"><strong>{{ item.value }}</strong><span>{{ item.label }}</span></div></div>
        <div v-if="about.cards.length" class="site-modal__grid">
          <article v-for="(item,index) in about.cards" :key="`${item.title}-${index}`" class="site-modal__card"><span class="site-modal__card-index">{{ padIndex(index) }}</span><h3>{{ item.title }}</h3><p>{{ item.text }}</p></article>
        </div>
        <div v-if="about.callout_title || about.callout_text" class="site-modal__callout"><AppIcon name="shield-check" /><div><strong>{{ about.callout_title }}</strong><p>{{ about.callout_text }}</p></div></div>
      </template>

      <template v-else-if="state.modal === 'delivery' && shipping.enabled">
        <p v-if="shipping.eyebrow" class="site-modal__eyebrow">{{ shipping.eyebrow }}</p>
        <h2 class="site-modal__title ui-display" id="site-modal-title">{{ shipping.title }}</h2>
        <p v-if="shipping.lead" class="site-modal__lead">{{ shipping.lead }}</p>
        <div v-if="shipping.steps.length" class="site-modal__steps">
          <div v-for="(item,index) in shipping.steps" :key="`${item.title}-${index}`" class="site-modal__step"><span>{{ padIndex(index) }}</span><strong>{{ item.title }}</strong><p>{{ item.text }}</p></div>
        </div>
        <div v-if="shipping.sections.length" class="site-modal__grid site-modal__grid--compact">
          <article v-for="section in shipping.sections" :key="section.title" class="site-modal__card"><h3>{{ section.title }}</h3><ul><li v-for="item in section.items" :key="item">{{ item }}</li></ul></article>
        </div>
        <div v-if="shipping.note" class="site-modal__note">{{ shipping.note }}</div>
      </template>

      <template v-else-if="state.modal === 'contacts'">
        <p class="site-modal__eyebrow">CONTACT {{ store.name }}</p>
        <h2 class="site-modal__title ui-display" id="site-modal-title">{{ contacts.title }}</h2>
        <p class="site-modal__lead">{{ contacts.lead }}</p>
        <div class="site-modal__contacts">
          <a v-if="store.phoneDisplay" class="site-modal__contact" :href="`tel:${store.phoneHref}`"><AppIcon name="phone" /><span><small>Phone</small><strong>{{ store.phoneDisplay }}</strong><em v-if="store.hours">{{ store.hours }}</em></span></a>
          <a v-if="store.email" class="site-modal__contact" :href="`mailto:${store.email}`"><AppIcon name="notification" /><span><small>Email</small><strong>{{ store.email }}</strong><em>{{ contacts.email_note }}</em></span></a>
          <div v-if="store.location" class="site-modal__contact"><AppIcon name="connection" /><span><small>Service region</small><strong>{{ store.location }}</strong><em>{{ contacts.region_note }}</em></span></div>
        </div>
        <div v-if="contacts.cards.length" class="site-modal__support-grid">
          <article v-for="item in contacts.cards" :key="item.title"><span>{{ item.eyebrow }}</span><h3>{{ item.title }}</h3><p>{{ item.text }}</p></article>
        </div>
        <div v-if="contacts.callout_title || contacts.callout_text" class="site-modal__callout site-modal__callout--contact"><AppIcon name="phone" /><div><strong>{{ contacts.callout_title }}</strong><p>{{ contacts.callout_text }}</p></div></div>
      </template>

      <template v-else>
        <h2 class="site-modal__title ui-display" id="site-modal-title">Content unavailable</h2>
        <p class="site-modal__lead">This storefront section is disabled.</p>
      </template>
    </div>
  </div>
</template>
