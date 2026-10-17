<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { adminApi } from '../../api/services.js'
import IconPicker from '../../components/IconPicker.vue'
import { defaultStorefront, mergeStorefrontConfig } from '../../state/storefrontDefaults.js'
import { useSeo } from '../../composables/useSeo.js'
import { useToast } from '../../composables/useToast.js'
import { VELMORA_VERSION } from '../../utils/version.js'

const toast = useToast()
const loading = ref(true)
const saving = ref(false)
const uploading = ref('')
const storeName = ref('Your store')
const error = ref('')
const tab = ref('brand')
const savedSnapshot = ref('')
const dirty = computed(() => savedSnapshot.value !== '' && JSON.stringify(form) !== savedSnapshot.value)
const sectionsRef = ref(null)
const tabDescriptions = {brand:'Logo and visual colors', header:'Navigation and announcements',hero:'Main banner and calls to action',sections:'Catalog, benefits and FAQ',modals:'Store information and contact dialogs',footer:'Footer layout and text',platform:'Open-source credit and project links'}
const form = reactive(JSON.parse(JSON.stringify(defaultStorefront)))
const tabs = [
  ['brand', 'Brand & theme'], ['header', 'Header'], ['hero', 'Hero'], ['sections', 'Sections'], ['modals', 'Dialogs'], ['footer', 'Footer'], ['platform', 'About Velmora']
]
const actionOptions = [['catalog','Catalog'],['contacts','Contacts modal'],['url','Custom URL'],['none','Do nothing']]
const navKeys = ['home','catalog','about','shipping','faq','contacts']
const previewStyle = computed(() => ({
  '--preview-bg': form.theme.background, '--preview-surface': form.theme.surface, '--preview-primary': form.theme.primary,
  '--preview-accent': form.theme.accent, '--preview-text': form.theme.text, '--preview-muted': form.theme.text_secondary,
  '--preview-border': form.theme.border
}))
useSeo({ title: 'Storefront | Velmora Admin', description: 'Storefront appearance and content.', path: '/admin/storefront', noindex: true })

function replaceObject(target, source) {
  for (const key of Object.keys(target)) delete target[key]
  Object.assign(target, JSON.parse(JSON.stringify(source)))
}
async function load() {
  loading.value = true; error.value = ''
  try {
    const settings = await adminApi.settings()
    storeName.value = settings.store_name || 'Your store'
    replaceObject(form, mergeStorefrontConfig(settings.storefront))
    savedSnapshot.value = JSON.stringify(form)
  } catch (e) { error.value = e.response?.data?.detail || 'Could not load storefront configuration.' }
  finally { loading.value = false }
}
async function save() {
  saving.value = true; error.value = ''
  try {
    const updated = await adminApi.updateSettings({ storefront: form })
    replaceObject(form, mergeStorefrontConfig(updated.storefront))
    savedSnapshot.value = JSON.stringify(form)
    toast.show('Storefront saved.')
  } catch (e) {
    const detail = e.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(x => `${x.loc?.slice(-1)[0] || 'field'}: ${x.msg}`).join(' · ') : 'Could not save storefront.'
  } finally { saving.value = false }
}
async function uploadImage(kind, event) {
  const file = event.target.files?.[0]; event.target.value = ''
  if (!file) return
  uploading.value = kind; error.value = ''
  try {
    const asset = await adminApi.uploadStorefrontImage(file)
    if (kind === 'logo') form.branding.logo_url = asset.url
    if (kind === 'hero') form.hero.image_url = asset.url
    toast.show('Image uploaded. Save storefront to publish it.')
  } catch (e) { error.value = e.response?.data?.detail || 'Could not upload image.' }
  finally { uploading.value = '' }
}
function resetAll() { if (confirm('Reset storefront editor to the bundled Velmora defaults? This only changes the editor until you save.')) replaceObject(form, defaultStorefront) }
function move(list, index, direction) { const next=index+direction; if(next<0||next>=list.length)return; [list[index],list[next]]=[list[next],list[index]] }
function addFeature(list) { list.push({ icon:'pulse', title:'New feature', text:'Describe the feature.' }) }
function addFaq() { form.faq.items.push({ question:'New question', answer:'Answer the question.' }) }
function addCard(list) { list.push({ eyebrow:'', title:'New card', text:'Card text.' }) }
function addStat() { form.modals.about.stats.push({ value:'1', label:'stat' }) }
function addStep() { form.modals.shipping.steps.push({ title:'New step', text:'Step description.' }) }
function addInfoSection() { form.modals.shipping.sections.push({ title:'New section', items:['New item'] }) }
function remove(list,index){ list.splice(index,1) }
function navLabel(key){ return ({home:'Home',catalog:'Catalog',about:'About',shipping:'Shipping & payment',faq:'FAQ',contacts:'Contacts'})[key] || key }
function ensureNav(){
  const existing=new Set(form.header.nav.map(x=>x.key));
  for(const key of navKeys) if(!existing.has(key)) form.header.nav.push({key,label:navLabel(key),enabled:true})
}
function expandAll(value) { sectionsRef.value?.querySelectorAll('details.builder-accordion').forEach(item => { item.open = value }) }
function revealInvalid(event) { const section = event.target.closest('details'); if (section) section.open = true }
function setTab(id) { tab.value = id }
onMounted(async()=>{ await load(); ensureNav(); savedSnapshot.value = JSON.stringify(form) })
</script>

<template>
<section class="admin-page storefront-editor">
  <div class="admin-page-head"><div><p>STOREFRONT BUILDER</p><h1 class="ui-display">Storefront</h1><span>Branding, navigation, hero, content sections, dialogs and theme — without editing Vue files.</span></div><div class="admin-head-actions"><button type="button" class="admin-back" @click="resetAll">Reset defaults</button><a class="admin-back" href="/" target="_blank" rel="noopener">Open storefront ↗</a></div></div>
  <div v-if="error" class="admin-alert">{{ error }}</div><div v-if="loading" class="admin-loading">Loading…</div>
  <template v-else>
    <div class="builder-workspace">
      <nav class="builder-navigation" aria-label="Storefront editor sections">
        <p class="builder-navigation__eyebrow">YOUR STOREFRONT</p>
        <button v-for="(item,index) in tabs" :key="item[0]" type="button" :class="['builder-nav-item',{active:tab===item[0]}]" :aria-current="tab===item[0]?'step':undefined" @click="setTab(item[0])"><span class="builder-nav-item__num">{{String(index+1).padStart(2,'0')}}</span><span><strong>{{item[1]}}</strong><small>{{tabDescriptions[item[0]]}}</small></span><span aria-hidden="true">›</span></button>
        <div class="builder-navigation__hint">Changes are saved together. Preview before publishing on your storefront.</div>
      </nav>
      <div ref="sectionsRef" class="builder-content">
        <div class="builder-current"><div><small>STORE EDITOR / {{tab.toUpperCase()}}</small><h2>{{tabs.find(item=>item[0]===tab)?.[1]}}</h2><p>{{tabDescriptions[tab]}}</p></div><div class="builder-current__actions"><span v-if="dirty" class="builder-unsaved" role="status">● Unsaved changes</span><button type="button" @click="expandAll(true)">Expand all</button><button type="button" @click="expandAll(false)">Collapse all</button></div></div>
    <form class="settings-panel storefront-form" @submit.prevent="save" @invalid.capture="revealInvalid">
      <template v-if="tab==='brand'">
        <details class="builder-accordion" open><summary class="builder-accordion__summary"><span><strong>Logo & visual theme</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body"><p class="builder-section-intro">Uploaded images are converted to WebP on the server. Theme values are validated as safe #RRGGBB colors.</p>
        <div class="storefront-brand-grid">
          <div class="storefront-upload-card"><div class="storefront-logo-preview" :style="previewStyle"><img :src="form.branding.logo_url" :alt="form.branding.logo_alt"></div><label class="btn btn-secondary storefront-upload-button"><input type="file" accept="image/jpeg,image/png,image/webp" @change="uploadImage('logo',$event)"><span>{{uploading==='logo'?'Uploading…':'Upload logo'}}</span></label></div>
          <div class="settings-grid"><label class="admin-field"><span>Logo URL</span><input v-model="form.branding.logo_url" maxlength="500"></label><label class="admin-field"><span>Logo alt text</span><input v-model="form.branding.logo_alt" maxlength="160"></label></div>
        </div>
        </div></details><details class="builder-accordion" ><summary class="builder-accordion__summary"><span><strong>Theme palette</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body"><p class="builder-section-intro">These colors are applied as storefront CSS variables.</p>
        <div class="theme-color-grid"><label v-for="key in ['background','background_soft','surface','surface_alt','primary','accent','accent_soft','text','text_secondary','border']" :key="key" class="theme-color-field"><span>{{key.replaceAll('_',' ')}}</span><div><input v-model="form.theme[key]" type="color"><input v-model="form.theme[key]" maxlength="7" pattern="#[0-9A-Fa-f]{6}"></div></label></div>
        <div class="storefront-mini-preview" :style="previewStyle"><div class="preview-nav">{{ storeName }} <span>Catalog</span><button type="button">Action</button></div><h3>Storefront preview</h3><p>Theme colors update here before you save.</p></div></div></details>
      </template>

      <template v-if="tab==='header'">
        <details class="builder-accordion" open><summary class="builder-accordion__summary"><span><strong>Navigation & actions</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body"><p class="builder-section-intro">Business hours are hidden from the desktop header by default to prevent long schedules from breaking the layout.</p>
        <div class="settings-checks storefront-toggles"><label><input v-model="form.header.show_phone" type="checkbox">Show phone</label><label><input v-model="form.header.show_hours" type="checkbox">Show hours under phone</label><label><input v-model="form.header.show_consultation" type="checkbox">Show action button</label></div>
        <label class="admin-field"><span>Header action label</span><input v-model="form.header.consultation_label" maxlength="80"></label>
        </div></details><details class="builder-accordion" ><summary class="builder-accordion__summary"><span><strong>Menu items</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body">
        <div class="storefront-list"><div v-for="(item,index) in form.header.nav" :key="item.key" class="storefront-list-row"><label class="settings-switch"><input v-model="item.enabled" type="checkbox"><span><strong>{{navLabel(item.key)}}</strong><small>{{item.key}}</small></span></label><label class="admin-field"><span>Label</span><input v-model="item.label" maxlength="48"></label><div class="storefront-row-actions"><button type="button" :disabled="index===0" @click="move(form.header.nav,index,-1)">↑</button><button type="button" :disabled="index===form.header.nav.length-1" @click="move(form.header.nav,index,1)">↓</button></div></div></div>
        </div></details><details class="builder-accordion" ><summary class="builder-accordion__summary"><span><strong>Announcement bar</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body"><p class="builder-section-intro">Useful for delivery notices, promotions, maintenance notices, or a temporary message.</p>
        <label class="settings-switch"><input v-model="form.announcement.enabled" type="checkbox"><span><strong>Show announcement bar</strong></span></label>
        <div class="settings-grid"><label class="admin-field admin-field--wide"><span>Message</span><input v-model="form.announcement.text" maxlength="240"></label><label class="admin-field"><span>Link label</span><input v-model="form.announcement.link_label" maxlength="60"></label><label class="admin-field"><span>Link URL</span><input v-model="form.announcement.link_url" maxlength="500" placeholder="/catalog or https://..."></label></div></div></details>
      </template>

      <template v-if="tab==='hero'">
        <details class="builder-accordion" open><summary class="builder-accordion__summary"><span><strong>Homepage hero</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body"><p class="builder-section-intro">Turn it off entirely or replace every visible element.</p>
        <label class="settings-switch"><input v-model="form.hero.enabled" type="checkbox"><span><strong>Show hero</strong></span></label>
        <div class="settings-grid"><label class="admin-field"><span>Eyebrow</span><input v-model="form.hero.eyebrow" maxlength="160"></label><label class="admin-field admin-field--wide"><span>Title</span><textarea v-model="form.hero.title" rows="4" maxlength="320"></textarea><small>Line breaks are preserved.</small></label><label class="admin-field admin-field--wide"><span>Description</span><textarea v-model="form.hero.description" rows="5" maxlength="1200"></textarea></label><label class="admin-field admin-field--wide"><span>Background image URL</span><input v-model="form.hero.image_url" maxlength="500"></label></div>
        <label class="btn btn-secondary storefront-upload-button storefront-inline-upload"><input type="file" accept="image/jpeg,image/png,image/webp" @change="uploadImage('hero',$event)"><span>{{uploading==='hero'?'Uploading…':'Upload hero image'}}</span></label>
        <div class="storefront-actions-grid"><section v-for="key in ['primary_action','secondary_action']" :key="key" class="admin-panel storefront-subpanel"><label class="settings-switch"><input v-model="form.hero[key].enabled" type="checkbox"><span><strong>{{key==='primary_action'?'Primary':'Secondary'}} button</strong></span></label><label class="admin-field"><span>Label</span><input v-model="form.hero[key].label" maxlength="80"></label><label class="admin-field"><span>Action</span><select v-model="form.hero[key].action"><option v-for="opt in actionOptions" :key="opt[0]" :value="opt[0]">{{opt[1]}}</option></select></label><label v-if="form.hero[key].action==='url'" class="admin-field"><span>URL</span><input v-model="form.hero[key].url" maxlength="500"></label></section></div>
        </div></details><details class="builder-accordion" ><summary class="builder-accordion__summary"><span><strong>Highlights</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body"><div class="admin-panel-head settings-section-head"><div><strong class="builder-subsection-title">Hero highlights</strong></div><button type="button" class="admin-panel-action" @click="addFeature(form.hero.features)">+ Feature</button></div>
        <div class="repeater"><div v-for="(item,index) in form.hero.features" :key="index" class="repeater-row repeater-row--metric"><IconPicker v-model="item.icon"/><label class="admin-field"><span>Title</span><input v-model="item.title" maxlength="120"></label><label class="admin-field"><span>Text</span><input v-model="item.text" maxlength="300"></label><button type="button" class="repeater-remove" @click="remove(form.hero.features,index)">×</button></div></div></div></details>
      </template>

      <template v-if="tab==='sections'">
        <details class="builder-accordion" open><summary class="builder-accordion__summary"><span><strong>Catalog heading</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body"><label class="settings-switch"><input v-model="form.catalog.show_heading" type="checkbox"><span><strong>Show catalog heading</strong></span></label><div class="settings-grid"><label class="admin-field"><span>Title</span><input v-model="form.catalog.title" maxlength="160"></label><label class="admin-field admin-field--wide"><span>Description</span><textarea v-model="form.catalog.description" rows="3" maxlength="600"></textarea></label></div>
        </div></details><details class="builder-accordion" ><summary class="builder-accordion__summary"><span><strong>Store features</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body"><div class="admin-panel-head settings-section-head"><div><strong class="builder-subsection-title">Store benefits</strong></div><button type="button" class="admin-panel-action" @click="addFeature(form.feature_strip.items)">+ Feature</button></div><label class="settings-switch"><input v-model="form.feature_strip.enabled" type="checkbox"><span><strong>Show feature strip</strong></span></label><div class="repeater"><div v-for="(item,index) in form.feature_strip.items" :key="index" class="repeater-row repeater-row--metric"><IconPicker v-model="item.icon"/><label class="admin-field"><span>Title</span><input v-model="item.title" maxlength="120"></label><label class="admin-field"><span>Text</span><input v-model="item.text" maxlength="300"></label><button type="button" class="repeater-remove" @click="remove(form.feature_strip.items,index)">×</button></div></div>
        </div></details><details class="builder-accordion" ><summary class="builder-accordion__summary"><span><strong>Frequently asked questions</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body"><div class="admin-panel-head settings-section-head"><div><strong class="builder-subsection-title">Questions & answers</strong></div><button type="button" class="admin-panel-action" @click="addFaq">+ Question</button></div><label class="settings-switch"><input v-model="form.faq.enabled" type="checkbox"><span><strong>Show FAQ</strong></span></label><label class="admin-field"><span>Section title</span><input v-model="form.faq.title" maxlength="160"></label><div class="repeater"><div v-for="(item,index) in form.faq.items" :key="index" class="repeater-row repeater-row--textarea repeater-row--two-fields"><label class="admin-field"><span>Question</span><input v-model="item.question" maxlength="240"></label><label class="admin-field"><span>Answer</span><textarea v-model="item.answer" rows="3" maxlength="2000"></textarea></label><button type="button" class="repeater-remove" @click="remove(form.faq.items,index)">×</button></div></div></div></details>
      </template>

      <template v-if="tab==='modals'">
        <details class="builder-accordion" open><summary class="builder-accordion__summary"><span><strong>About dialog</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body"><label class="settings-switch"><input v-model="form.modals.about.enabled" type="checkbox"><span><strong>Enable About dialog</strong></span></label><div class="settings-grid"><label class="admin-field"><span>Eyebrow</span><input v-model="form.modals.about.eyebrow"></label><label class="admin-field"><span>Title</span><input v-model="form.modals.about.title"></label><label class="admin-field admin-field--wide"><span>Lead</span><textarea v-model="form.modals.about.lead" rows="3"></textarea></label></div><div class="admin-panel-head settings-section-head"><div><strong class="builder-subsection-title">Key facts</strong><p class="builder-subsection-note">Short figures displayed in the About dialog.</p></div><button type="button" class="admin-panel-action" @click="addStat">+ Stat</button></div><div class="repeater"><div v-for="(item,index) in form.modals.about.stats" :key="index" class="repeater-row repeater-row--two-fields"><label class="admin-field"><span>Value</span><input v-model="item.value"></label><label class="admin-field"><span>Label</span><input v-model="item.label"></label><button type="button" class="repeater-remove" @click="remove(form.modals.about.stats,index)">×</button></div></div><div class="admin-panel-head settings-section-head"><div><strong class="builder-subsection-title">Information cards</strong><p class="builder-subsection-note">Explain what makes your store useful.</p></div><button type="button" class="admin-panel-action" @click="addCard(form.modals.about.cards)">+ Card</button></div><div class="repeater"><div v-for="(item,index) in form.modals.about.cards" :key="index" class="repeater-row repeater-row--textarea repeater-row--two-fields"><label class="admin-field"><span>Title</span><input v-model="item.title"></label><label class="admin-field"><span>Text</span><textarea v-model="item.text" rows="2"></textarea></label><button type="button" class="repeater-remove" @click="remove(form.modals.about.cards,index)">×</button></div></div><div class="settings-grid"><label class="admin-field"><span>Callout title</span><input v-model="form.modals.about.callout_title"></label><label class="admin-field admin-field--wide"><span>Callout text</span><textarea v-model="form.modals.about.callout_text" rows="3"></textarea></label></div></div></details>
        <details class="builder-accordion" ><summary class="builder-accordion__summary"><span><strong>Shipping & payment dialog</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body"><label class="settings-switch"><input v-model="form.modals.shipping.enabled" type="checkbox"><span><strong>Enable Shipping dialog</strong></span></label><div class="settings-grid"><label class="admin-field"><span>Eyebrow</span><input v-model="form.modals.shipping.eyebrow"></label><label class="admin-field"><span>Title</span><input v-model="form.modals.shipping.title"></label><label class="admin-field admin-field--wide"><span>Lead</span><textarea v-model="form.modals.shipping.lead" rows="3"></textarea></label></div><div class="admin-panel-head settings-section-head"><div><strong class="builder-subsection-title">Delivery steps</strong><p class="builder-subsection-note">Help customers understand how their order is processed.</p></div><button type="button" class="admin-panel-action" @click="addStep">+ Step</button></div><div class="repeater"><div v-for="(item,index) in form.modals.shipping.steps" :key="index" class="repeater-row repeater-row--textarea repeater-row--two-fields"><label class="admin-field"><span>Title</span><input v-model="item.title"></label><label class="admin-field"><span>Text</span><textarea v-model="item.text" rows="2"></textarea></label><button type="button" class="repeater-remove" @click="remove(form.modals.shipping.steps,index)">×</button></div></div><div class="admin-panel-head settings-section-head"><div><strong class="builder-subsection-title">Shipping and payment details</strong><p class="builder-subsection-note">Group important information into readable sections.</p></div><button type="button" class="admin-panel-action" @click="addInfoSection">+ Section</button></div><div class="storefront-list"><div v-for="(section,index) in form.modals.shipping.sections" :key="index" class="admin-panel storefront-subpanel"><div class="admin-panel-head"><label class="admin-field"><span>Section title</span><input v-model="section.title"></label><button type="button" class="repeater-remove" @click="remove(form.modals.shipping.sections,index)">×</button></div><div class="repeater"><div v-for="(item,itemIndex) in section.items" :key="itemIndex" class="repeater-row"><label class="admin-field"><span>Item</span><input v-model="section.items[itemIndex]" maxlength="500"></label><button type="button" class="repeater-remove" @click="remove(section.items,itemIndex)">×</button></div></div><button type="button" class="admin-panel-action" @click="section.items.push('New item')">+ Item</button></div></div><label class="admin-field admin-field--wide"><span>Shipping note</span><textarea v-model="form.modals.shipping.note" rows="3"></textarea></label></div></details>
        <details class="builder-accordion" ><summary class="builder-accordion__summary"><span><strong>Contact dialog</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body"><div class="settings-grid"><label class="admin-field"><span>Title</span><input v-model="form.modals.contacts.title"></label><label class="admin-field admin-field--wide"><span>Lead</span><textarea v-model="form.modals.contacts.lead" rows="3"></textarea></label><label class="admin-field"><span>Email note</span><input v-model="form.modals.contacts.email_note"></label><label class="admin-field"><span>Region note</span><input v-model="form.modals.contacts.region_note"></label></div><div class="admin-panel-head settings-section-head"><div><strong class="builder-subsection-title">Contact options</strong><p class="builder-subsection-note">Describe ways customers can reach you.</p></div><button type="button" class="admin-panel-action" @click="addCard(form.modals.contacts.cards)">+ Card</button></div><div class="repeater"><div v-for="(item,index) in form.modals.contacts.cards" :key="index" class="repeater-row repeater-row--textarea repeater-row--three-fields"><label class="admin-field"><span>Eyebrow</span><input v-model="item.eyebrow"></label><label class="admin-field"><span>Title</span><input v-model="item.title"></label><label class="admin-field"><span>Text</span><textarea v-model="item.text" rows="2"></textarea></label><button type="button" class="repeater-remove" @click="remove(form.modals.contacts.cards,index)">×</button></div></div><div class="settings-grid"><label class="admin-field"><span>Callout title</span><input v-model="form.modals.contacts.callout_title"></label><label class="admin-field admin-field--wide"><span>Callout text</span><textarea v-model="form.modals.contacts.callout_text" rows="3"></textarea></label></div></div></details>
      </template>

      <template v-if="tab==='footer'">
        <details class="builder-accordion" open><summary class="builder-accordion__summary"><span><strong>Footer layout</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body"><p class="builder-section-intro">Store name, tagline, description and contact data still come from Store Settings.</p><div class="settings-checks storefront-toggles"><label><input v-model="form.footer.show_menu" type="checkbox">Menu</label><label><input v-model="form.footer.show_products" type="checkbox">Products</label><label><input v-model="form.footer.show_contacts" type="checkbox">Contacts</label><label><input v-model="form.footer.show_callback" type="checkbox">Callback card</label></div><div class="settings-grid"><label class="admin-field"><span>Callback title</span><input v-model="form.footer.callback_title"></label><label class="admin-field admin-field--wide"><span>Callback text</span><textarea v-model="form.footer.callback_text" rows="3"></textarea></label><label class="admin-field"><span>Button label</span><input v-model="form.footer.callback_button_label"></label><label class="admin-field admin-field--wide"><span>Copyright</span><input v-model="form.footer.copyright"><small>Supported placeholders: {year}, {store}</small></label></div></div></details>
      </template>

      <template v-if="tab==='platform'">
        <details class="builder-accordion" open><summary class="builder-accordion__summary"><span><strong>Open-source information</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body"><p class="builder-section-intro">This dialog describes Velmora itself — not your individual store. The application version always comes from VERSION and cannot be edited here.</p>
        
        <div class="settings-grid"><label class="admin-field"><span>Footer button text</span><input v-model="form.platform.footer_label" maxlength="80"></label><label class="admin-field"><span>Eyebrow</span><input v-model="form.platform.eyebrow" maxlength="120"></label><label class="admin-field admin-field--wide"><span>Dialog title</span><input v-model="form.platform.title" maxlength="220"></label><label class="admin-field admin-field--wide"><span>Project description</span><textarea v-model="form.platform.description" rows="4" maxlength="1400"></textarea></label></div>
        </div></details><details class="builder-accordion" ><summary class="builder-accordion__summary"><span><strong>Support and source code</strong><small>Click to expand or collapse settings</small></span><span aria-hidden="true" class="builder-accordion__chevron">⌄</span></summary><div class="builder-accordion__body"><p class="builder-section-intro">The GitHub link is always visible. You can set a support URL whenever you are ready.</p>
        <div class="settings-grid"><label class="admin-field"><span>Support heading</span><input v-model="form.platform.support_title" maxlength="180"></label><label class="admin-field admin-field--wide"><span>Support description</span><textarea v-model="form.platform.support_text" rows="3" maxlength="1200"></textarea></label><label class="admin-field"><span>Repository button label</span><input v-model="form.platform.repository_label" maxlength="80"></label><label class="admin-field"><span>Repository URL</span><input v-model="form.platform.repository_url" type="url" placeholder="https://github.com/xydojhuk/velmora" maxlength="500"></label><label class="admin-field"><span>Support button label</span><input v-model="form.platform.support_label" maxlength="80"></label><label class="admin-field"><span>Support URL</span><input v-model="form.platform.support_url" type="url" placeholder="https://..." maxlength="500"></label></div>
        <div class="builder-platform-preview"><strong>Powered by Velmora</strong><p>{{form.platform.title}}</p><small>v{{ VELMORA_VERSION }} · Open source · self-hosted</small></div></div></details>
      </template>

      <div class="settings-savebar builder-savebar"><span class="builder-savebar__status" :class="dirty?'builder-save-pending':'builder-save-ok'" role="status">{{dirty ? '● Changes not saved' : '✓ All changes saved'}}</span><button class="btn btn-primary admin-save builder-savebar__button" type="submit" :disabled="saving || !dirty">{{saving?'Saving…':'Save changes'}}</button></div>
    </form>
    </div>
    </div>
  </template>
</section>
</template>
