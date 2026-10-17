<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useHead } from '@unhead/vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { publicApi } from '../api/services.js'
import { fallbackProduct } from '../state/fallback.js'
import { useStoreInfo } from '../composables/useStoreInfo.js'
import { useAppState } from '../composables/useAppState.js'
import { formatMoney, normalizeImage } from '../utils/format.js'
import { compactMetaText, safeJsonLd } from '../utils/seo.js'

const state = useAppState()
const store = useStoreInfo()
const route = useRoute()
const router = useRouter()
const hasInitialProduct = !state.pageData.productMissing && state.pageData.product?.slug === route.params.slug
const product = ref(state.pageData.productMissing ? null : (hasInitialProduct ? state.pageData.product : fallbackProduct(route.params.slug)))
const quantity = ref(1)
const activeTab = ref('description')
const activeImageIndex = ref(0)
const zoomed = ref(false)
const loading = ref(false)

const images = computed(() => {
  const gallery = Array.isArray(product.value?.gallery) ? product.value.gallery.filter(Boolean).slice(0, 4) : []
  if (gallery.length) return gallery.map(normalizeImage)
  return [normalizeImage(product.value?.primary_image)]
})
const image = computed(() => images.value[Math.min(activeImageIndex.value, images.value.length - 1)] || '/img/logo.png')
const title = computed(() => product.value?.title || 'Product not found')
const description = computed(() => product.value?.short_description || `This product is not available in the ${store.value.name} catalog.`)
const canonicalPath = computed(() => `/product/${route.params.slug}`)
const canOrder = computed(() => store.value.ordersEnabled && (!product.value?.track_inventory || product.value.stock_quantity > 0))
const availability = computed(() => canOrder.value ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock')
const extra = computed(() => product.value?.extra || {})
const availabilityLabel = computed(() => !canOrder.value && product.value?.track_inventory && product.value.stock_quantity <= 0 ? 'Out of stock' : canOrder.value ? (extra.value.availability_label || 'Available to order') : (extra.value.unavailable_label || 'Orders are temporarily paused'))
const primaryActionLabel = computed(() => extra.value.primary_action_label || 'Place order')
const secondaryActionLabel = computed(() => extra.value.secondary_action_label || 'Ask a question')
const detailEyebrow = computed(() => String(extra.value.detail_eyebrow || 'Configuration {model}').replace('{model}', product.value?.model || ''))
const tabLabels = computed(() => ({ description: 'Description', specifications: 'Specifications', usage: 'Operation', ...(extra.value.tab_labels || {}) }))
const tabs = computed(() => [
  ['description', tabLabels.value.description],
  ['specifications', tabLabels.value.specifications],
  ['usage', tabLabels.value.usage]
])
const benefits = computed(() => Array.isArray(extra.value.benefits) ? extra.value.benefits.filter(item => item?.title || item?.text) : [])
const visualFeatures = computed(() => Array.isArray(extra.value.visual_features) ? extra.value.visual_features.filter(item => item?.text) : [])
const usageItems = computed(() => Array.isArray(extra.value.usage_items) ? extra.value.usage_items.filter(Boolean) : [])
const secondarySections = computed(() => Array.isArray(extra.value.secondary_sections) ? extra.value.secondary_sections : [])
const warrantyNote = computed(() => extra.value.warranty_note || '')

useHead(() => {
  const siteUrl = String(state.siteUrl || '').replace(/\/$/, '')
  const canonical = siteUrl ? new URL(canonicalPath.value, siteUrl).toString() : canonicalPath.value
  const imageUrls = images.value.map(item => siteUrl ? new URL(item, `${siteUrl}/`).toString() : item)
  const imageUrl = imageUrls[0] || image.value
  const metaTitle = compactMetaText(product.value ? `${product.value.title} | ${store.value.name}` : `Product not found | ${store.value.name}`, 80)
  const metaDescription = compactMetaText(description.value, 200)
  const jsonLd = product.value ? [
    {
      '@context': 'https://schema.org', '@type': 'Product', name: product.value.title, sku: product.value.sku,
      model: product.value.model, url: canonical, image: imageUrls, description: product.value.short_description,
      brand: { '@type': 'Brand', name: store.value.name },
      offers: {
        '@type': 'Offer', url: canonical, priceCurrency: product.value.currency,
        price: (product.value.price_minor / 100).toFixed(2), availability: availability.value,
        itemCondition: 'https://schema.org/NewCondition', seller: { '@type': 'Organization', name: store.value.name, url: siteUrl || '/' }
      }
    },
    {
      '@context': 'https://schema.org', '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Home', item: siteUrl ? `${siteUrl}/` : '/' },
        { '@type': 'ListItem', position: 2, name: product.value.title, item: canonical }
      ]
    }
  ] : []
  return {
    title: metaTitle,
    link: [{ rel: 'canonical', href: canonical }],
    meta: [
      { name: 'description', content: metaDescription },
      { name: 'robots', content: product.value ? 'index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1' : 'noindex,follow' },
      { property: 'og:locale', content: 'en_US' }, { property: 'og:type', content: 'product' },
      { property: 'og:site_name', content: store.value.name }, { property: 'og:title', content: metaTitle },
      { property: 'og:description', content: metaDescription }, { property: 'og:url', content: canonical },
      { property: 'og:image', content: imageUrl }, { property: 'og:image:alt', content: product.value?.title || store.value.name },
      { property: 'product:price:amount', content: product.value ? String(product.value.price_minor / 100) : '' },
      { property: 'product:price:currency', content: product.value?.currency || 'USD' },
      { name: 'twitter:card', content: 'summary_large_image' }, { name: 'twitter:title', content: metaTitle },
      { name: 'twitter:description', content: metaDescription }, { name: 'twitter:image', content: imageUrl },
      { name: 'twitter:image:alt', content: product.value?.title || store.value.name }
    ],
    script: jsonLd.map(item => ({ type: 'application/ld+json', nonce: state.cspNonce || undefined, innerHTML: safeJsonLd(item) }))
  }
})

async function loadProduct(slug) {
  loading.value = true
  try {
    product.value = await publicApi.product(slug)
    state.pageData.product = product.value
    state.apiOnline = true
  } catch (error) {
    product.value = null
    state.apiOnline = error.response?.status === 404
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (state.pageData.productMissing) return
  if (!hasInitialProduct || !state.apiOnline) loadProduct(route.params.slug)
})

watch(() => route.params.slug, slug => {
  quantity.value = 1
  activeTab.value = 'description'
  activeImageIndex.value = 0
  zoomed.value = false
  loadProduct(slug)
})

function goCheckout() {
  if (!product.value || !state.apiOnline || !canOrder.value || (product.value.track_inventory && quantity.value > product.value.stock_quantity)) return
  router.push({ name: 'checkout', params: { slug: product.value.slug }, query: { quantity: quantity.value } })
}
</script>

<template>
  <div v-if="product" class="product-page">
    <nav class="breadcrumbs ui-scrollbar-hidden" aria-label="Breadcrumb">
      <RouterLink to="/">Home</RouterLink><span>›</span><RouterLink :to="{ name: 'home', hash: '#catalog' }">Catalog</RouterLink><span>›</span><span>{{ product.title }}</span>
    </nav>

    <section class="detail-hero">
      <div class="detail-gallery">
        <div class="detail-gallery__main" :class="{ zoomed }">
          <img :src="image" :alt="product.title" class="detail-gallery__image">
          <button class="detail-gallery__zoom" type="button" aria-label="Zoom product image" @click="zoomed = !zoomed"><AppIcon name="resize" /></button>
        </div>
        <div v-if="images.length > 1" class="detail-gallery__thumbs" aria-label="Product images">
          <button v-for="(item, index) in images" :key="`${item}-${index}`" class="detail-gallery__thumb" :class="{ active: activeImageIndex === index }" type="button" :aria-label="`Image ${index + 1}`" @click="activeImageIndex = index"><img :src="item" :alt="`${product.title}, image ${index + 1}`"></button>
        </div>
      </div>

      <div class="detail-summary">
        <p class="detail-summary__sku">{{ product.sku }}</p>
        <h1 class="detail-summary__title ui-display">{{ product.title }}</h1>
        <p v-if="product.subtitle" class="detail-summary__subtitle">{{ product.subtitle }}</p>
        <div class="detail-summary__price ui-display">{{ formatMoney(product.price_minor, product.currency) }}</div>
        <div class="detail-summary__stock" :class="{ 'is-empty': !canOrder }"><span class="detail-summary__stock-dot"></span><span>{{ availabilityLabel }}</span></div>
        <p v-if="product.short_description" class="detail-summary__description">{{ product.short_description }}</p>
        <ul v-if="product.summary_features?.length" class="detail-summary__features">
          <li v-for="(feature, index) in product.summary_features" :key="`${feature.text}-${index}`"><AppIcon :name="feature.icon" /><span>{{ feature.text }}</span></li>
        </ul>
        <div class="detail-summary__quantity" aria-label="Quantity">
          <button type="button" aria-label="Decrease quantity" @click="quantity = Math.max(1, quantity - 1)">−</button><span>{{ quantity }}</span><button type="button" aria-label="Increase quantity" @click="quantity = Math.min(99, quantity + 1)">+</button>
        </div>
        <div class="detail-summary__actions">
          <button class="btn btn-primary detail-summary__buy" type="button" :disabled="!state.apiOnline || !canOrder || (product.track_inventory && quantity > product.stock_quantity)" @click="goCheckout"><AppIcon name="cart" />{{ primaryActionLabel }}</button>
          <button class="btn btn-secondary detail-summary__quick" type="button" @click="state.modal = 'contacts'"><AppIcon name="phone" />{{ secondaryActionLabel }}</button>
        </div>
      </div>
    </section>

    <section v-if="benefits.length" class="detail-benefits ui-card" aria-label="Product benefits">
      <article v-for="(item,index) in benefits" :key="`${item.title}-${index}`" class="detail-benefit">
        <AppIcon :name="item.icon || 'shield-check'" class="detail-benefit__icon" /><span><strong>{{ item.title }}</strong><small>{{ item.text }}</small></span>
      </article>
    </section>
    <p v-if="warrantyNote" class="detail-warranty-note">{{ warrantyNote }}</p>

    <section class="detail-information ui-card">
      <div class="detail-tabs ui-scrollbar-hidden" role="tablist" aria-label="Product information">
        <button v-for="tab in tabs" :key="tab[0]" class="detail-tab" :class="{ active: activeTab === tab[0] }" type="button" role="tab" :aria-selected="activeTab === tab[0]" @click="activeTab = tab[0]">{{ tab[1] }}</button>
      </div>

      <div v-show="activeTab === 'description'" class="detail-panel active">
        <div class="detail-panel__copy">
          <p v-if="detailEyebrow" class="detail-panel__eyebrow">{{ detailEyebrow }}</p>
          <h2 v-if="product.description_title" class="ui-display">{{ product.description_title }}</h2>
          <div v-if="product.description_paragraphs?.length" class="detail-panel__paragraphs"><p v-for="(paragraph,index) in product.description_paragraphs" :key="index">{{ paragraph }}</p></div>
          <div v-if="visualFeatures.length" class="detail-panel__visual">
            <img :src="image" :alt="`${product.title} — product view`">
            <div class="detail-panel__visual-features">
              <span v-for="(item,index) in visualFeatures" :key="`${item.text}-${index}`"><AppIcon :name="item.icon || 'pulse'" />{{ item.text }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-show="activeTab === 'specifications'" class="detail-panel active">
        <div class="detail-specs detail-specs--full">
          <h3 class="ui-display">{{ extra.specifications_title || 'Technical specifications' }}</h3>
          <dl><template v-for="(spec,index) in product.specifications" :key="`${spec.group}-${spec.label}-${index}`"><div><dt>{{ spec.label }}</dt><dd>{{ spec.value }}</dd></div></template></dl>
        </div>
      </div>

      <div v-show="activeTab === 'usage'" class="detail-panel active">
        <div class="detail-package">
          <h3 class="ui-display">{{ extra.usage_title || 'Before you start' }}</h3>
          <ul><li v-for="(item,index) in usageItems" :key="index">{{ item }}</li></ul>
        </div>
      </div>
    </section>

    <section v-if="secondarySections.length" class="detail-secondary">
      <article v-for="(section,index) in secondarySections" :key="`${section.title}-${index}`" class="detail-secondary__card ui-card" :class="{ 'detail-secondary__card--accent': section.accent }">
        <h2 class="ui-display">{{ section.title }}</h2>
        <div v-if="section.items?.length" class="detail-secondary__columns">
          <div v-for="(item,itemIndex) in section.items" :key="`${item.title}-${itemIndex}`"><AppIcon :name="item.icon || 'pulse'" /><h3>{{ item.title }}</h3><p>{{ item.text }}</p></div>
        </div>
        <ul v-if="section.checks?.length" class="detail-checks">
          <li v-for="(item,itemIndex) in section.checks" :key="`${item.text}-${itemIndex}`"><AppIcon :name="item.icon || 'shield-check'" />{{ item.text }}</li>
        </ul>
        <button v-if="section.link_label && section.link_modal" class="detail-secondary__link" type="button" @click="state.modal = section.link_modal">{{ section.link_label }} <AppIcon name="arrow" /></button>
      </article>
    </section>
  </div>

  <section v-else class="store-empty">
    <p>{{ state.apiOnline ? "404 / PRODUCT" : "503 / STORE UNAVAILABLE" }}</p>
    <h1 class="ui-display">{{ state.apiOnline ? "Product not found" : "The store is temporarily unavailable" }}</h1>
    <RouterLink class="btn btn-primary" to="/">Back to catalog</RouterLink>
  </section>
</template>
