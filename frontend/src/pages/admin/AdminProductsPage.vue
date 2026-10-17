<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import AppIcon from '../../components/AppIcon.vue'
import { adminApi } from '../../api/services.js'
import { useSeo } from '../../composables/useSeo.js'
import { useToast } from '../../composables/useToast.js'
import { formatMoney, normalizeImage } from '../../utils/format.js'

const toast = useToast()
const result = ref({ items: [], total: 0, page: 1, size: 25 })
const loading = ref(false)
const categories = ref([])
const filters = reactive({ page: 1, size: 25, search: '', active: '', category: '', lowStock: false })
let timer

useSeo({ title: 'Products | Velmora Admin', description: 'Manage products.', path: '/admin/products', noindex: true })

async function load() {
  loading.value = true
  try {
    result.value = await adminApi.products({
      page: filters.page,
      size: filters.size,
      low_stock: filters.lowStock,
      category: filters.category || undefined,
      search: filters.search || undefined,
      active: filters.active === '' ? undefined : filters.active === 'true'
    })
  } finally {
    loading.value = false
  }
}

async function deactivate(product) {
  if (!confirm(`Deactivate ${product.title}? The product will disappear from the public catalog.`)) return
  await adminApi.deactivateProduct(product.id)
  toast.show('Product deactivated.')
  load()
}

onMounted(async () => { try { categories.value = await adminApi.categories() } catch { /* Keep catalog available. */ } await load() })
watch(() => filters.page, load)
watch(() => [filters.active, filters.category, filters.lowStock], () => {
  if (filters.page !== 1) filters.page = 1
  else load()
})
watch(() => filters.search, () => {
  clearTimeout(timer)
  timer = setTimeout(() => {
    if (filters.page !== 1) filters.page = 1
    else load()
  }, 350)
})
</script>

<template>
  <section class="admin-page">
    <div class="admin-page-head"><div><p>CATALOG</p><h1 class="ui-display">Products</h1><span>Prices, availability, images and product details.</span></div><RouterLink class="btn btn-primary admin-create" to="/admin/products/new"><AppIcon name="plus" />New product</RouterLink></div>
    <div class="admin-toolbar"><input v-model="filters.search" class="admin-search" type="search" placeholder="Name, SKU, page slug or model"><select v-model="filters.category" class="admin-select"><option value="">All categories</option><option v-for="item in categories" :key="item.slug" :value="item.slug">{{ item.name }}</option></select><select v-model="filters.active" class="admin-select"><option value="">Status: all</option><option value="true">Active</option><option value="false">Inactive</option></select></div>
    <div class="admin-toolbar"><label class="admin-stock-toggle"><input type="checkbox" v-model="filters.lowStock"> Low stock only</label><RouterLink to="/admin/categories">Manage categories</RouterLink><a href="/api/v1/admin/products/export.csv" download>Export products (CSV)</a></div>
    <div class="admin-products-grid">
      <article v-for="product in result.items" :key="product.id" class="admin-product-card admin-panel">
        <div class="admin-product-card__image"><img :src="normalizeImage(product.primary_image)" :alt="product.title"><span :class="product.is_active ? 'is-live' : 'is-draft'">{{ product.is_active ? 'ACTIVE' : 'OFF' }}</span></div>
        <div class="admin-product-card__body"><small>{{ product.sku }} / {{ product.slug }}</small><h2 class="ui-display">{{ product.title }}</h2><p>{{ product.subtitle }}</p><div class="admin-product-card__meta"><strong>{{ formatMoney(product.price_minor, product.currency) }}</strong><span>{{ product.track_inventory ? `Stock: ${product.stock_quantity}` : (product.is_active ? 'Active' : 'Inactive') }}</span></div></div>
        <div class="admin-product-card__actions"><RouterLink :to="`/admin/products/${product.id}`">Edit</RouterLink><button v-if="product.is_active" type="button" @click="deactivate(product)">Deactivate</button><span v-else class="admin-product-card__inactive">Inactive</span></div>
      </article>
      <div v-if="!loading && !result.items.length" class="admin-panel admin-empty-card">No products match these filters.</div>
    </div>
    <nav v-if="result.total > result.size" class="admin-pagination" aria-label="Product pages"><button class="btn btn-secondary" type="button" :disabled="filters.page <= 1 || loading" @click="filters.page--">Previous</button><span>Page {{ filters.page }} / {{ Math.ceil(result.total / result.size) }}</span><button class="btn btn-secondary" type="button" :disabled="filters.page >= Math.ceil(result.total / result.size) || loading" @click="filters.page++">Next</button></nav>
  </section>
</template>
