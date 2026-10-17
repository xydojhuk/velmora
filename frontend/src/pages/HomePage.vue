<script setup>
import { computed, onMounted, ref } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import ProductCard from '../components/ProductCard.vue'
import { publicApi } from '../api/services.js'
import { fallbackProducts } from '../state/fallback.js'
import { useStoreInfo } from '../composables/useStoreInfo.js'
import { useAppState } from '../composables/useAppState.js'
import { useSeo } from '../composables/useSeo.js'

const state = useAppState()
const store = useStoreInfo()
const products = computed(() => Array.isArray(state.pageData.products) ? state.pageData.products : fallbackProducts)
const search = ref('')
const category = ref('')
const availabilityOnly = ref(false)
const categoryRecords = ref([])
const categories = computed(() => categoryRecords.value.length ? categoryRecords.value.filter(c => c.is_active && products.value.some(p => (p.category_slug || 'general') === c.slug)).map(c => ({ slug: c.slug, name: c.name })) : [...new Set(products.value.map(p => p.category_slug || 'general'))].sort().map(slug => ({ slug, name: slug.replaceAll('-', ' ') })))
const filteredProducts = computed(() => products.value.filter(p => {
  const text = search.value.trim().toLocaleLowerCase()
  return (!text || `${p.title} ${p.sku} ${p.short_description || ''}`.toLocaleLowerCase().includes(text))
    && (!category.value || (p.category_slug || 'general') === category.value)
    && (!availabilityOnly.value || !p.track_inventory || p.stock_quantity > 0)
}))
const siteUrl = computed(() => String(state.siteUrl || '').replace(/\/$/, ''))
const absolute = path => siteUrl.value ? new URL(path, `${siteUrl.value}/`).toString() : path
const storefront = computed(() => store.value.storefront)
const hero = computed(() => storefront.value.hero)
const faq = computed(() => storefront.value.faq)
const featureStrip = computed(() => storefront.value.feature_strip)
const catalog = computed(() => storefront.value.catalog)

function openAction(action) {
  if (action?.action === 'contacts') state.modal = 'contacts'
}

useSeo({
  title: store.value.seoTitle,
  description: store.value.seoDescription,
  image: store.value.seoOgImage,
  path: '/',
  imageAlt: `${store.value.name} storefront`,
  jsonLd: [
    {
      '@context': 'https://schema.org', '@type': 'Organization', name: store.value.name, url: absolute('/'),
      logo: absolute(store.value.logoUrl), email: store.value.email, telephone: store.value.phoneHref, areaServed: store.value.location || undefined,
      contactPoint: { '@type': 'ContactPoint', telephone: store.value.phoneHref, email: store.value.email, contactType: 'customer service', availableLanguage: ['en'] }
    },
    { '@context': 'https://schema.org', '@type': 'WebSite', name: store.value.name, url: absolute('/'), inLanguage: 'en' },
    {
      '@context': 'https://schema.org', '@type': 'ItemList', name: `${store.value.name} catalog`,
      itemListElement: products.value.map((product, index) => ({ '@type': 'ListItem', position: index + 1, url: absolute(`/product/${encodeURIComponent(product.slug)}`), name: product.title }))
    },
    ...(faq.value.enabled && faq.value.items.length ? [{ '@context': 'https://schema.org', '@type': 'FAQPage', mainEntity: faq.value.items.map(item => ({ '@type': 'Question', name: item.question, acceptedAnswer: { '@type': 'Answer', text: item.answer } })) }] : [])
  ]
})

onMounted(async () => {
  try { categoryRecords.value = await publicApi.categories() } catch { /* Legacy / temporarily unavailable API: use slugs. */ }
  if (Array.isArray(state.pageData.products) && state.apiOnline) return
  try { state.pageData.products = await publicApi.products(); state.apiOnline = true }
  catch { state.pageData.products = fallbackProducts; state.apiOnline = false }
})
</script>

<template>
  <section v-if="hero.enabled" class="hero" aria-labelledby="hero-title">
    <div class="hero__grid"></div>
    <div class="hero__content">
      <p v-if="hero.eyebrow" class="hero__eyebrow">{{ hero.eyebrow }}</p>
      <h1 class="hero__title hero__title--editable" id="hero-title">{{ hero.title }}</h1>
      <p v-if="hero.description" class="hero__description">{{ hero.description }}</p>
      <div v-if="hero.primary_action.enabled || hero.secondary_action.enabled" class="hero__actions">
        <RouterLink v-if="hero.primary_action.enabled && hero.primary_action.action === 'catalog'" :to="{ name: 'home', hash: '#catalog' }" class="btn btn-primary hero__primary"><AppIcon name="cart" />{{ hero.primary_action.label }}</RouterLink>
        <button v-else-if="hero.primary_action.enabled && hero.primary_action.action === 'contacts'" class="btn btn-primary hero__primary" type="button" @click="openAction(hero.primary_action)">{{ hero.primary_action.label }}</button>
        <a v-else-if="hero.primary_action.enabled && hero.primary_action.action === 'url' && hero.primary_action.url" class="btn btn-primary hero__primary" :href="hero.primary_action.url">{{ hero.primary_action.label }}</a>
        <RouterLink v-if="hero.secondary_action.enabled && hero.secondary_action.action === 'catalog'" :to="{ name: 'home', hash: '#catalog' }" class="btn btn-secondary hero__secondary">{{ hero.secondary_action.label }}</RouterLink>
        <button v-else-if="hero.secondary_action.enabled && hero.secondary_action.action === 'contacts'" class="btn btn-secondary hero__secondary" type="button" @click="openAction(hero.secondary_action)">{{ hero.secondary_action.label }}</button>
        <a v-else-if="hero.secondary_action.enabled && hero.secondary_action.action === 'url' && hero.secondary_action.url" class="btn btn-secondary hero__secondary" :href="hero.secondary_action.url">{{ hero.secondary_action.label }}</a>
      </div>
      <div v-if="hero.features.length" class="hero__features">
        <article v-for="item in hero.features" :key="`${item.icon}-${item.title}`" class="hero-feature"><AppIcon :name="item.icon" class="hero-feature__icon" stroke="1.5" /><span><strong>{{ item.title }}</strong><small>{{ item.text }}</small></span></article>
      </div>
    </div>
    <img v-if="hero.image_url" :src="hero.image_url" alt="" class="hero__bg">
  </section>

  <div v-if="!state.apiOnline" class="store-api-note">The catalog is temporarily unavailable. Please try again when the store connection is restored.</div>

  <section class="products" id="catalog" aria-label="Catalog">
    <p v-if="state.apiOnline && !products.length" class="store-api-note">No products are available yet.</p>
    <header v-if="catalog.show_heading" class="catalog-heading"><p>CATALOG</p><h2 class="ui-display">{{ catalog.title }}</h2><span v-if="catalog.description">{{ catalog.description }}</span></header>
    <p v-if="products.length && !filteredProducts.length" class="store-api-note">No products match the selected filters.</p>
    <ProductCard v-for="(product, index) in filteredProducts" :key="product.slug" :product="product" :reverse="index % 2 === 1" />
  </section>

  <section v-if="featureStrip.enabled && featureStrip.items.length" class="features ui-card" aria-label="Store features">
    <div v-for="item in featureStrip.items" :key="`${item.icon}-${item.title}`" class="feature"><AppIcon :name="item.icon" class="feature__icon" stroke="1.5" /><span><strong>{{ item.title }}</strong><small>{{ item.text }}</small></span></div>
  </section>

  <section v-if="faq.enabled && faq.items.length" class="faq" id="faq" aria-labelledby="faq-title">
    <h2 class="faq__title ui-display" id="faq-title">{{ faq.title }}</h2>
    <div class="faq__grid">
      <details v-for="item in faq.items" :key="item.question" class="faq__item ui-card">
        <summary class="faq__question"><span>{{ item.question }}</span><span class="faq__plus" aria-hidden="true"></span></summary>
        <div class="faq__answer">{{ item.answer }}</div>
      </details>
    </div>
  </section>
</template>
