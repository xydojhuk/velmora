<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../../components/AppIcon.vue'
import IconPicker from '../../components/IconPicker.vue'
import { adminApi } from '../../api/services.js'
import { useSeo } from '../../composables/useSeo.js'
import { useToast } from '../../composables/useToast.js'
import { normalizeImage } from '../../utils/format.js'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const editing = computed(() => Boolean(route.params.id))
const loading = ref(editing.value)
const saving = ref(false)
const error = ref('')
const existingImages = ref([])
const categories = ref([])
const pendingImages = ref([])
const fileInput = ref(null)
const editorForm = ref(null)

function defaultExtra() {
  return {
    warranty: '12-month warranty',
    warranty_note: 'Warranty does not cover liquid ingress, mechanical damage, or operation outside the documented limits.',
    availability_label: 'Available to order',
    unavailable_label: 'Orders are temporarily paused',
    primary_action_label: 'Place order',
    secondary_action_label: 'Ask a question',
    detail_eyebrow: 'Configuration {model}',
    tab_labels: { description: 'Description', specifications: 'Specifications', usage: 'Operation' },
    specifications_title: 'Technical specifications',
    usage_title: 'Before you start',
    benefits: [
      { icon: 'shield-check', title: 'Warranty', text: '12-month warranty' },
      { icon: 'connection', title: 'Reliable operation', text: 'Designed for consistent everyday use' },
      { icon: 'pulse', title: 'Ready to use', text: 'Configured and ready after setup' }
    ],
    visual_features: [
      { icon: 'connection', text: 'Highlight an important product capability here' },
      { icon: 'shield-check', text: 'Add a second product-specific benefit' },
      { icon: 'pulse', text: 'Use custom SVG icons from the icon library if needed' }
    ],
    usage_items: [
      'Read the product documentation before first use.',
      'Use only compatible accessories and power sources.',
      'Store the product in a dry, ventilated location.'
    ],
    secondary_sections: [
      {
        title: 'Before ordering', accent: false,
        items: [
          { icon: 'resize', title: 'Choose the right configuration', text: 'Describe which version is best for a specific use case.' },
          { icon: 'phone', title: 'Need help?', text: 'Invite the customer to contact the store before ordering.' }
        ],
        checks: [], link_label: 'Shipping, payment and warranty', link_modal: 'delivery'
      },
      {
        title: 'Important information', accent: true, items: [], link_label: '', link_modal: '',
        checks: [
          { icon: 'shield-check', text: 'Add important product limitations, compatibility notes, or safety information here.' },
          { icon: 'pulse', text: 'Every field in this section can be changed or removed from the admin panel.' }
        ]
      }
    ]
  }
}

function defaultForm() {
  return {
    slug: `new-product-${Date.now().toString(36)}`,
    sku: 'VELMORA-001',
    model: 'Standard',
    name: 'Standard',
    title: 'New product',
    subtitle: 'A short product subtitle',
    short_description: 'A short description shown in the catalog and at the top of the product page.',
    description_title: 'Product overview',
    description_paragraphs: ['Describe the product, its purpose, and the main reasons a customer should choose it.'],
    price: 99,
    currency: 'USD',
    is_active: true,
    category_slug: 'general', track_inventory: false, stock_quantity: 0, low_stock_threshold: 5,
    catalog_metrics: [
      { icon: 'shield-check', label: 'Quality', value: 'Premium' },
      { icon: 'weight', label: 'Weight', value: '—' },
      { icon: 'resize', label: 'Dimensions', value: '—' }
    ],
    summary_features: [
      { icon: 'shield-check', text: 'Primary product advantage' },
      { icon: 'pulse', text: 'Second product advantage' },
      { icon: 'connection', text: 'Third product advantage' }
    ],
    specifications: [
      { group: 'General', label: 'Model', value: 'Standard' },
      { group: 'General', label: 'Material', value: '—' },
      { group: 'General', label: 'Warranty', value: '12 months' }
    ],
    extra: defaultExtra(),
    sort_order: 0
  }
}

const form = reactive(defaultForm())
const imageCount = computed(() => existingImages.value.length + pendingImages.value.length)
const canAddImages = computed(() => imageCount.value < 4)

useSeo({
  title: editing.value ? 'Edit product | Velmora Admin' : 'New product | Velmora Admin',
  description: 'Velmora product editor.',
  path: route.fullPath,
  noindex: true
})

function normalizeExtra(source = {}) {
  const defaults = defaultExtra()
  const data = { ...defaults, ...source }
  data.tab_labels = { ...defaults.tab_labels, ...(source.tab_labels || {}) }
  data.benefits = Array.isArray(source.benefits) ? source.benefits.map(item => ({ ...item })) : defaults.benefits
  data.visual_features = Array.isArray(source.visual_features) ? source.visual_features.map(item => ({ ...item })) : defaults.visual_features
  data.usage_items = Array.isArray(source.usage_items) ? [...source.usage_items] : defaults.usage_items
  data.secondary_sections = Array.isArray(source.secondary_sections)
    ? source.secondary_sections.map(section => ({
        title: section.title || '', accent: Boolean(section.accent),
        items: Array.isArray(section.items) ? section.items.map(item => ({ ...item })) : [],
        checks: Array.isArray(section.checks) ? section.checks.map(item => ({ ...item })) : [],
        link_label: section.link_label || '', link_modal: section.link_modal || ''
      }))
    : defaults.secondary_sections
  return data
}

function assignProduct(product) {
  Object.assign(form, {
    slug: product.slug, sku: product.sku, model: product.model, name: product.name, title: product.title,
    subtitle: product.subtitle, short_description: product.short_description, description_title: product.description_title,
    description_paragraphs: product.description_paragraphs?.length ? [...product.description_paragraphs] : [''],
    price: product.price_minor / 100, currency: product.currency, is_active: product.is_active,
    category_slug: product.category_slug || 'general', track_inventory: Boolean(product.track_inventory),
    stock_quantity: product.stock_quantity ?? 0, low_stock_threshold: product.low_stock_threshold ?? 5,
    catalog_metrics: (product.catalog_metrics || []).map(item => ({ ...item })),
    summary_features: (product.summary_features || []).map(item => ({ ...item })),
    specifications: (product.specifications || []).map(item => ({ ...item })),
    extra: normalizeExtra(product.extra || {}), sort_order: product.sort_order
  })
  existingImages.value = [...(product.images || [])].sort((a, b) => a.sort_order - b.sort_order)
}

async function load() {
  if (!editing.value) return
  try { assignProduct(await adminApi.product(route.params.id)) }
  catch { error.value = 'Could not load the product.' }
  finally { loading.value = false }
}

function cleanExtra() {
  const source = form.extra
  return {
    ...source,
    benefits: source.benefits.filter(item => String(item.title || '').trim() || String(item.text || '').trim()).map(item => ({ icon: item.icon || 'shield-check', title: String(item.title || '').trim(), text: String(item.text || '').trim() })),
    visual_features: source.visual_features.filter(item => String(item.text || '').trim()).map(item => ({ icon: item.icon || 'pulse', text: String(item.text || '').trim() })),
    usage_items: source.usage_items.map(item => String(item || '').trim()).filter(Boolean),
    secondary_sections: source.secondary_sections
      .filter(section => String(section.title || '').trim() || section.items?.length || section.checks?.length)
      .map(section => ({
        title: String(section.title || '').trim(), accent: Boolean(section.accent),
        items: (section.items || []).filter(item => item.title || item.text).map(item => ({ icon: item.icon || 'pulse', title: String(item.title || '').trim(), text: String(item.text || '').trim() })),
        checks: (section.checks || []).filter(item => item.text).map(item => ({ icon: item.icon || 'shield-check', text: String(item.text || '').trim() })),
        link_label: String(section.link_label || '').trim(), link_modal: String(section.link_modal || '').trim()
      }))
  }
}

function payload() {
  return {
    slug: form.slug.trim(), sku: form.sku.trim(), model: form.model.trim(), name: form.name.trim(), title: form.title.trim(),
    subtitle: form.subtitle.trim(), short_description: form.short_description.trim(), description_title: form.description_title.trim(),
    description_paragraphs: form.description_paragraphs.map(item => item.trim()).filter(Boolean),
    price_minor: Math.round(Number(form.price || 0) * 100), currency: form.currency.trim().toUpperCase(), is_active: form.is_active,
    category_slug: form.category_slug.trim().toLowerCase(), track_inventory: form.track_inventory,
    stock_quantity: Number(form.stock_quantity), low_stock_threshold: Number(form.low_stock_threshold),
    catalog_metrics: form.catalog_metrics.filter(item => String(item.label || '').trim() && String(item.value || '').trim()).map(item => ({ icon: String(item.icon || 'pulse').trim(), label: String(item.label || '').trim(), value: String(item.value || '').trim() })),
    summary_features: form.summary_features.filter(item => String(item.text || '').trim()).map(item => ({ icon: String(item.icon || 'shield-check').trim(), text: String(item.text || '').trim() })),
    specifications: form.specifications.filter(item => String(item.label || '').trim() && String(item.value || '').trim()).map(item => ({ group: String(item.group || '').trim() || null, label: String(item.label || '').trim(), value: String(item.value || '').trim() })),
    extra: cleanExtra(), sort_order: Number(form.sort_order || 0)
  }
}

function selectImages(event) {
  error.value = ''
  const files = Array.from(event.target.files || [])
  if (!files.length) return
  const available = Math.max(0, 4 - imageCount.value)
  if (files.length > available) error.value = `A product can contain up to 4 images. Remaining slots: ${available}.`
  for (const file of files.slice(0, available)) {
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) { error.value = 'Only JPEG, PNG, and WebP product images are supported.'; continue }
    if (file.size > 8 * 1024 * 1024) { error.value = `${file.name} is larger than 8 MB.`; continue }
    pendingImages.value.push({ file, preview: URL.createObjectURL(file) })
  }
  event.target.value = ''
}
function removePending(index) { const item = pendingImages.value[index]; if (item?.preview) URL.revokeObjectURL(item.preview); pendingImages.value.splice(index, 1) }
function movePending(index, direction) { const next = index + direction; if (next < 0 || next >= pendingImages.value.length) return; const copy = [...pendingImages.value]; const [item] = copy.splice(index, 1); copy.splice(next, 0, item); pendingImages.value = copy }
async function deleteExisting(image) {
  if (!editing.value || !confirm('Delete this product image?')) return
  try { await adminApi.deleteProductImage(route.params.id, image.id); existingImages.value = existingImages.value.filter(item => item.id !== image.id); toast.show('Image deleted.') }
  catch (requestError) { error.value = requestError.response?.data?.detail || 'Could not delete the image.' }
}
async function reorderExisting(imageId, direction = 0, makePrimary = false) {
  const current = [...existingImages.value]; const index = current.findIndex(item => item.id === imageId); if (index < 0) return
  const target = makePrimary ? 0 : index + direction; if (target < 0 || target >= current.length || target === index) return
  const [item] = current.splice(index, 1); current.splice(target, 0, item)
  try { existingImages.value = await adminApi.reorderProductImages(route.params.id, current.map(entry => entry.id)) }
  catch (requestError) { error.value = requestError.response?.data?.detail || 'Could not change the image order.' }
}
async function uploadPending(productId) {
  while (pendingImages.value.length) { const item = pendingImages.value[0]; await adminApi.uploadProductImage(productId, item.file, form.title.trim()); URL.revokeObjectURL(item.preview); pendingImages.value.shift() }
}
async function save() {
  error.value = ''
  if (!form.slug.trim() || !form.title.trim() || !form.name.trim() || !form.sku.trim() || !form.model.trim()) { error.value = 'Page slug, SKU, model, product name, and title are required.'; return }
  saving.value = true
  const wasEditing = editing.value
  let savedId = wasEditing ? route.params.id : null
  try {
    let saved = wasEditing ? await adminApi.updateProduct(savedId, payload()) : await adminApi.createProduct(payload())
    savedId = saved.id
    if (!wasEditing) await router.replace(`/admin/products/${saved.id}`)
    if (pendingImages.value.length) await uploadPending(saved.id)
    saved = await adminApi.product(saved.id); assignProduct(saved); toast.show(wasEditing ? 'Product updated.' : 'Product created.')
  } catch (requestError) {
    if (savedId) { try { assignProduct(await adminApi.product(savedId)) } catch {} }
    const detail = requestError.response?.data?.detail; error.value = typeof detail === 'string' ? detail : 'Could not save the product.'
  } finally { saving.value = false }
}

function addSecondarySection() { form.extra.secondary_sections.push({ title: 'New section', accent: false, items: [], checks: [], link_label: '', link_modal: '' }) }
function addSectionItem(section) { section.items.push({ icon: 'pulse', title: 'New item', text: 'Describe this item.' }) }
function addSectionCheck(section) { section.checks.push({ icon: 'shield-check', text: 'Add an important note.' }) }

function expandSections(expand) { editorForm.value?.querySelectorAll('details.editor-accordion').forEach(group => { group.open = expand }) }
function revealInvalid(event) { const section = event.target.closest('details.editor-accordion'); if (section) section.open = true }
onMounted(async () => {
  try { categories.value = await adminApi.categories() } catch { error.value = 'Cannot load categories. Check your connection.' }
  await load()
})
onBeforeUnmount(() => pendingImages.value.forEach(item => URL.revokeObjectURL(item.preview)))
</script>

<template>
  <section class="admin-page admin-editor-page">
    <div class="admin-page-head"><div><p>CATALOG</p><h1 class="ui-display">{{ editing ? 'Edit product' : 'New product' }}</h1><span>Everything shown on the catalog card and product detail page can be configured here.</span></div><RouterLink class="admin-back" to="/admin/products">← Back to products</RouterLink></div>
    <div v-if="loading" class="admin-loading">Loading product…</div>

    <form v-else ref="editorForm" class="admin-editor" @submit.prevent="save" @invalid.capture="revealInvalid">
      <div class="editor-toolbar"><div><strong>Product workspace</strong><small>Start with essentials; expand advanced sections only when needed.</small></div><div><button type="button" @click="expandSections(true)">Expand all</button><button type="button" @click="expandSections(false)">Collapse all</button></div></div>
      <div v-if="error" class="admin-alert" role="alert">{{ error }}</div>

      <details class="editor-accordion" open><summary class="editor-accordion__summary"><span class="editor-accordion__index">01</span><span class="editor-accordion__label"><strong>Essential product information</strong><small>Basic settings</small></span><span class="editor-accordion__arrow" aria-hidden="true">⌄</span></summary>
      <section class="admin-panel admin-editor-section">
        <div class="admin-panel-head"><div><small>BASIC</small><h2>Product card</h2><p>New products start with useful defaults. Change only what you need.</p></div></div>
        <div class="admin-form-grid admin-form-grid--3">
          <label class="admin-field"><span>Page slug *</span><input v-model="form.slug" maxlength="120" autocomplete="off"><small>Lowercase Latin letters, digits, and hyphens. Used in the product URL.</small></label>
          <label class="admin-field"><span>SKU *</span><input v-model="form.sku" maxlength="120" autocomplete="off"></label>
          <label class="admin-field"><span>Model *</span><input v-model="form.model" maxlength="120" autocomplete="off"></label>
        </div>
        <div class="admin-form-grid"><label class="admin-field"><span>Variant name *</span><input v-model="form.name" maxlength="160"></label><label class="admin-field"><span>Full title *</span><input v-model="form.title" maxlength="240"></label></div>
        <label class="admin-field"><span>Subtitle</span><input v-model="form.subtitle" maxlength="300"></label>
        <label class="admin-field"><span>Catalog description</span><textarea v-model="form.short_description" rows="4" maxlength="1800"></textarea></label>
        <div class="admin-form-grid admin-form-grid--4">
          <label class="admin-field"><span>Price</span><input v-model.number="form.price" type="number" min="0" step="0.01"></label>
          <label class="admin-field"><span>Currency</span><input v-model="form.currency" maxlength="3" placeholder="USD"></label>
          <label class="admin-field"><span>Catalog order</span><input v-model.number="form.sort_order" type="number"></label>
        </div>
        <div class="admin-form-grid admin-form-grid--3">
          <label class="admin-field"><span>Category</span><select v-model="form.category_slug" required><option v-for="item in categories" :key="item.slug" :value="item.slug">{{ item.name }}{{ item.is_active ? '' : ' (hidden)' }}</option></select><small><RouterLink to="/admin/categories">Manage categories</RouterLink></small></label>
          <label class="admin-field"><span>Stock on hand</span><input v-model.number="form.stock_quantity" type="number" min="0" step="1" :disabled="!form.track_inventory"></label>
          <label class="admin-field"><span>Low stock warning at</span><input v-model.number="form.low_stock_threshold" type="number" min="0" step="1" :disabled="!form.track_inventory"></label>
        </div>
        <div class="admin-switches"><label><input v-model="form.track_inventory" type="checkbox"><span>Track inventory (disable for services or made-to-order products)</span></label></div>
        <div class="admin-switches"><label><input v-model="form.is_active" type="checkbox"><span>Product is active and visible in the catalog</span></label></div>
      </section>
      </details>

      <details class="editor-accordion" open><summary class="editor-accordion__summary"><span class="editor-accordion__index">02</span><span class="editor-accordion__label"><strong>Product images</strong><small>Configure this area</small></span><span class="editor-accordion__arrow" aria-hidden="true">⌄</span></summary>
      <section class="admin-panel admin-editor-section admin-media-section">
        <div class="admin-panel-head"><div><small>MEDIA</small><h2>Product images</h2><p>Up to 4 images. The first image is the primary image.</p></div><button class="admin-panel-action" type="button" :disabled="!canAddImages" @click="fileInput?.click()"><AppIcon name="plus" />Add image</button></div>
        <input ref="fileInput" class="admin-file-input" type="file" accept="image/jpeg,image/png,image/webp" multiple @change="selectImages">
        <div v-if="imageCount" class="admin-media-grid">
          <article v-for="(item, index) in existingImages" :key="item.id" class="admin-media-card">
            <div class="admin-media-card__image"><img :src="normalizeImage(item.url)" :alt="item.alt_text || form.title"><span v-if="index === 0">Primary</span></div>
            <div class="admin-media-card__info"><strong>{{ item.original_name || `Image ${index + 1}` }}</strong><small v-if="item.width && item.height">{{ item.width }} × {{ item.height }}</small></div>
            <div class="admin-media-card__actions"><button v-if="index > 0" type="button" @click="reorderExisting(item.id, 0, true)">Make primary</button><button type="button" :disabled="index === 0" aria-label="Move left" @click="reorderExisting(item.id, -1)">←</button><button type="button" :disabled="index === existingImages.length - 1" aria-label="Move right" @click="reorderExisting(item.id, 1)">→</button><button class="is-danger" type="button" @click="deleteExisting(item)">Delete</button></div>
          </article>
          <article v-for="(item, index) in pendingImages" :key="item.preview" class="admin-media-card is-pending"><div class="admin-media-card__image"><img :src="item.preview" :alt="item.file.name"><span>After save</span></div><div class="admin-media-card__info"><strong>{{ item.file.name }}</strong><small>{{ Math.ceil(item.file.size / 1024) }} KB</small></div><div class="admin-media-card__actions"><button type="button" :disabled="index === 0" @click="movePending(index, -1)">←</button><button type="button" :disabled="index === pendingImages.length - 1" @click="movePending(index, 1)">→</button><button class="is-danger" type="button" @click="removePending(index)">Remove</button></div></article>
        </div>
        <button v-else class="admin-upload-empty" type="button" @click="fileInput?.click()"><AppIcon name="plus" :size="30" /><strong>Upload product images</strong><span>JPEG, PNG, or WebP, up to 8 MB each</span></button>
      </section>
      </details>

      <details class="editor-accordion" ><summary class="editor-accordion__summary"><span class="editor-accordion__index">03</span><span class="editor-accordion__label"><strong>Description</strong><small>Configure this area</small></span><span class="editor-accordion__arrow" aria-hidden="true">⌄</span></summary>
      <section class="admin-panel admin-editor-section">
        <div class="admin-panel-head"><div><small>DETAIL PAGE</small><h2>Description</h2><p>Main long-form product description.</p></div><button class="admin-panel-action" type="button" @click="form.description_paragraphs.push('')">+ Paragraph</button></div>
        <label class="admin-field"><span>Description heading</span><input v-model="form.description_title" maxlength="240"></label>
        <label class="admin-field"><span>Eyebrow above the heading</span><input v-model="form.extra.detail_eyebrow" maxlength="240"><small>Use <code>{model}</code> to insert the product model automatically.</small></label>
        <div class="repeater"><div v-for="(paragraph,index) in form.description_paragraphs" :key="index" class="repeater-row repeater-row--textarea"><label class="admin-field"><span>Paragraph {{ index + 1 }}</span><textarea v-model="form.description_paragraphs[index]" rows="4" maxlength="3000"></textarea></label><button class="repeater-remove" type="button" aria-label="Delete paragraph" @click="form.description_paragraphs.splice(index,1)">×</button></div></div>
      </section>
      </details>

      <details class="editor-accordion" ><summary class="editor-accordion__summary"><span class="editor-accordion__index">04</span><span class="editor-accordion__label"><strong>Quick metrics</strong><small>Configure this area</small></span><span class="editor-accordion__arrow" aria-hidden="true">⌄</span></summary>
      <section class="admin-panel admin-editor-section">
        <div class="admin-panel-head"><div><small>CATALOG</small><h2>Quick metrics</h2><p>Compact values shown on product cards.</p></div><button class="admin-panel-action" type="button" @click="form.catalog_metrics.push({ icon: 'pulse', label: '', value: '' })">+ Metric</button></div>
        <div class="repeater"><div v-for="(item,index) in form.catalog_metrics" :key="index" class="repeater-row repeater-row--metric"><IconPicker v-model="item.icon" /><label class="admin-field"><span>Label</span><input v-model="item.label" maxlength="120"></label><label class="admin-field"><span>Value</span><input v-model="item.value" maxlength="180"></label><button class="repeater-remove" type="button" aria-label="Delete metric" @click="form.catalog_metrics.splice(index,1)">×</button></div></div>
      </section>
      </details>

      <details class="editor-accordion" ><summary class="editor-accordion__summary"><span class="editor-accordion__index">05</span><span class="editor-accordion__label"><strong>Top features</strong><small>Configure this area</small></span><span class="editor-accordion__arrow" aria-hidden="true">⌄</span></summary>
      <section class="admin-panel admin-editor-section">
        <div class="admin-panel-head"><div><small>SUMMARY</small><h2>Top features</h2><p>Short feature bullets shown next to the price and order button.</p></div><button class="admin-panel-action" type="button" @click="form.summary_features.push({ icon: 'shield-check', text: '' })">+ Feature</button></div>
        <div class="repeater"><div v-for="(item,index) in form.summary_features" :key="index" class="repeater-row repeater-row--feature"><IconPicker v-model="item.icon" /><label class="admin-field"><span>Text</span><input v-model="item.text" maxlength="240"></label><button class="repeater-remove" type="button" aria-label="Delete feature" @click="form.summary_features.splice(index,1)">×</button></div></div>
      </section>
      </details>

      <details class="editor-accordion" ><summary class="editor-accordion__summary"><span class="editor-accordion__index">06</span><span class="editor-accordion__label"><strong>Benefit strip</strong><small>Configure this area</small></span><span class="editor-accordion__arrow" aria-hidden="true">⌄</span></summary>
      <section class="admin-panel admin-editor-section">
        <div class="admin-panel-head"><div><small>HIGHLIGHTS</small><h2>Benefit strip</h2><p>Large benefits displayed under the product hero.</p></div><button class="admin-panel-action" type="button" @click="form.extra.benefits.push({ icon: 'shield-check', title: 'New benefit', text: 'Describe the benefit.' })">+ Benefit</button></div>
        <div class="repeater"><div v-for="(item,index) in form.extra.benefits" :key="index" class="repeater-row repeater-row--metric"><IconPicker v-model="item.icon" /><label class="admin-field"><span>Title</span><input v-model="item.title" maxlength="120"></label><label class="admin-field"><span>Text</span><input v-model="item.text" maxlength="240"></label><button class="repeater-remove" type="button" aria-label="Delete benefit" @click="form.extra.benefits.splice(index,1)">×</button></div></div>
      </section>
      </details>

      <details class="editor-accordion" ><summary class="editor-accordion__summary"><span class="editor-accordion__index">07</span><span class="editor-accordion__label"><strong>Image highlights</strong><small>Configure this area</small></span><span class="editor-accordion__arrow" aria-hidden="true">⌄</span></summary>
      <section class="admin-panel admin-editor-section">
        <div class="admin-panel-head"><div><small>DESCRIPTION VISUAL</small><h2>Image feature list</h2><p>Feature lines shown beside the image in the Description tab.</p></div><button class="admin-panel-action" type="button" @click="form.extra.visual_features.push({ icon: 'pulse', text: 'New highlight' })">+ Highlight</button></div>
        <div class="repeater"><div v-for="(item,index) in form.extra.visual_features" :key="index" class="repeater-row repeater-row--feature"><IconPicker v-model="item.icon" /><label class="admin-field"><span>Text</span><input v-model="item.text" maxlength="300"></label><button class="repeater-remove" type="button" aria-label="Delete highlight" @click="form.extra.visual_features.splice(index,1)">×</button></div></div>
      </section>
      </details>

      <details class="editor-accordion" ><summary class="editor-accordion__summary"><span class="editor-accordion__index">08</span><span class="editor-accordion__label"><strong>Specifications</strong><small>Configure this area</small></span><span class="editor-accordion__arrow" aria-hidden="true">⌄</span></summary>
      <section class="admin-panel admin-editor-section">
        <div class="admin-panel-head"><div><small>SPECIFICATIONS</small><h2>Technical specifications</h2><p>Full list of product parameters.</p></div><button class="admin-panel-action" type="button" @click="form.specifications.push({ group: 'General', label: '', value: '' })">+ Parameter</button></div>
        <label class="admin-field"><span>Tab heading</span><input v-model="form.extra.specifications_title" maxlength="240"></label>
        <div class="repeater"><div v-for="(item,index) in form.specifications" :key="index" class="repeater-row repeater-row--spec"><label class="admin-field"><span>Group</span><input v-model="item.group" maxlength="100"></label><label class="admin-field"><span>Parameter</span><input v-model="item.label" maxlength="160"></label><label class="admin-field"><span>Value</span><input v-model="item.value" maxlength="400"></label><button class="repeater-remove" type="button" aria-label="Delete parameter" @click="form.specifications.splice(index,1)">×</button></div></div>
      </section>
      </details>

      <details class="editor-accordion" ><summary class="editor-accordion__summary"><span class="editor-accordion__index">09</span><span class="editor-accordion__label"><strong>Usage instructions</strong><small>Configure this area</small></span><span class="editor-accordion__arrow" aria-hidden="true">⌄</span></summary>
      <section class="admin-panel admin-editor-section">
        <div class="admin-panel-head"><div><small>OPERATION</small><h2>Usage / instructions</h2><p>List displayed in the third product information tab.</p></div><button class="admin-panel-action" type="button" @click="form.extra.usage_items.push('')">+ Item</button></div>
        <label class="admin-field"><span>Section heading</span><input v-model="form.extra.usage_title" maxlength="240"></label>
        <div class="repeater"><div v-for="(item,index) in form.extra.usage_items" :key="index" class="repeater-row repeater-row--textarea"><label class="admin-field"><span>Item {{ index + 1 }}</span><textarea v-model="form.extra.usage_items[index]" rows="2" maxlength="1000"></textarea></label><button class="repeater-remove" type="button" aria-label="Delete item" @click="form.extra.usage_items.splice(index,1)">×</button></div></div>
      </section>
      </details>

      <details class="editor-accordion" ><summary class="editor-accordion__summary"><span class="editor-accordion__index">10</span><span class="editor-accordion__label"><strong>Labels & actions</strong><small>Configure this area</small></span><span class="editor-accordion__arrow" aria-hidden="true">⌄</span></summary>
      <section class="admin-panel admin-editor-section">
        <div class="admin-panel-head"><div><small>LABELS</small><h2>Product page labels</h2><p>Customize the labels and calls to action without editing the storefront code.</p></div></div>
        <div class="admin-form-grid"><label class="admin-field"><span>Available label</span><input v-model="form.extra.availability_label" maxlength="160"></label><label class="admin-field"><span>Unavailable label</span><input v-model="form.extra.unavailable_label" maxlength="160"></label></div>
        <div class="admin-form-grid"><label class="admin-field"><span>Primary action</span><input v-model="form.extra.primary_action_label" maxlength="100"></label><label class="admin-field"><span>Secondary action</span><input v-model="form.extra.secondary_action_label" maxlength="100"></label></div>
        <div class="admin-form-grid admin-form-grid--3"><label class="admin-field"><span>Description tab</span><input v-model="form.extra.tab_labels.description" maxlength="80"></label><label class="admin-field"><span>Specifications tab</span><input v-model="form.extra.tab_labels.specifications" maxlength="80"></label><label class="admin-field"><span>Operation tab</span><input v-model="form.extra.tab_labels.usage" maxlength="80"></label></div>
      </section>
      </details>

      <details class="editor-accordion" ><summary class="editor-accordion__summary"><span class="editor-accordion__index">11</span><span class="editor-accordion__label"><strong>Additional sections</strong><small>Configure this area</small></span><span class="editor-accordion__arrow" aria-hidden="true">⌄</span></summary>
      <section class="admin-panel admin-editor-section">
        <div class="admin-panel-head"><div><small>ADDITIONAL CONTENT</small><h2>Bottom sections</h2><p>Flexible cards shown below the tabbed information block.</p></div><button class="admin-panel-action" type="button" @click="addSecondarySection">+ Section</button></div>
        <div class="repeater">
          <div v-for="(section,sectionIndex) in form.extra.secondary_sections" :key="sectionIndex" class="admin-panel admin-editor-section">
            <div class="admin-panel-head"><div><small>SECTION {{ sectionIndex + 1 }}</small><h3>{{ section.title || 'Untitled section' }}</h3></div><button class="repeater-remove" type="button" aria-label="Delete section" @click="form.extra.secondary_sections.splice(sectionIndex,1)">×</button></div>
            <div class="admin-form-grid"><label class="admin-field"><span>Title</span><input v-model="section.title" maxlength="180"></label><label class="admin-field"><span>Style</span><select v-model="section.accent"><option :value="false">Regular</option><option :value="true">Accent</option></select></label></div>
            <div class="admin-panel-head"><div><small>COLUMNS</small><p>Cards with icon, title, and text.</p></div><button class="admin-panel-action" type="button" @click="addSectionItem(section)">+ Column</button></div>
            <div class="repeater"><div v-for="(item,itemIndex) in section.items" :key="itemIndex" class="repeater-row repeater-row--metric"><IconPicker v-model="item.icon" /><label class="admin-field"><span>Title</span><input v-model="item.title" maxlength="160"></label><label class="admin-field"><span>Text</span><input v-model="item.text" maxlength="500"></label><button class="repeater-remove" type="button" @click="section.items.splice(itemIndex,1)">×</button></div></div>
            <div class="admin-panel-head"><div><small>CHECKLIST</small><p>Icon + text rows.</p></div><button class="admin-panel-action" type="button" @click="addSectionCheck(section)">+ Check</button></div>
            <div class="repeater"><div v-for="(item,itemIndex) in section.checks" :key="itemIndex" class="repeater-row repeater-row--feature"><IconPicker v-model="item.icon" /><label class="admin-field"><span>Text</span><input v-model="item.text" maxlength="700"></label><button class="repeater-remove" type="button" @click="section.checks.splice(itemIndex,1)">×</button></div></div>
            <div class="admin-form-grid"><label class="admin-field"><span>Optional link label</span><input v-model="section.link_label" maxlength="160"></label><label class="admin-field"><span>Open modal</span><select v-model="section.link_modal"><option value="">No action</option><option value="delivery">Shipping / payment</option><option value="contacts">Contacts</option><option value="about">About</option></select></label></div>
          </div>
        </div>
      </section>
      </details>

      <details class="editor-accordion" ><summary class="editor-accordion__summary"><span class="editor-accordion__index">12</span><span class="editor-accordion__label"><strong>Warranty</strong><small>Configure this area</small></span><span class="editor-accordion__arrow" aria-hidden="true">⌄</span></summary>
      <section class="admin-panel admin-editor-section">
        <div class="admin-panel-head"><div><small>WARRANTY</small><h2>Warranty note</h2></div><AppIcon name="shield" /></div>
        <label class="admin-field"><span>Warranty</span><input v-model="form.extra.warranty" maxlength="240"></label>
        <label class="admin-field"><span>Note</span><textarea v-model="form.extra.warranty_note" rows="3" maxlength="1000"></textarea></label>
      </section>
      </details>

      <div class="admin-editor-actions"><RouterLink class="btn admin-cancel" to="/admin/products">Cancel</RouterLink><button class="btn btn-primary" type="submit" :disabled="saving"><AppIcon name="shield-check" />{{ saving ? 'Saving…' : 'Save product' }}</button></div>
    </form>
  </section>
</template>
