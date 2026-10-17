<script setup>
import { useRouter } from 'vue-router'
import AppIcon from './AppIcon.vue'
import { formatMoney, normalizeImage } from '../utils/format.js'
import { useStoreInfo } from '../composables/useStoreInfo.js'
import { useAppState } from '../composables/useAppState.js'

const props = defineProps({ product: { type: Object, required: true }, reverse: { type: Boolean, default: false } })
const router = useRouter()
const store = useStoreInfo()
const state = useAppState()
const available = () => !props.product.track_inventory || props.product.stock_quantity > 0
function openDetail(event) {
  if (event?.target?.closest('a,button,input,select,textarea,summary')) return
  router.push(`/product/${props.product.slug}`)
}
</script>

<template>
  <article class="product ui-card" :class="{ 'product--reverse': reverse }" tabindex="0" @click="openDetail" @keydown.enter="openDetail">
    <div class="product__image-wrapper"><img :src="normalizeImage(product.primary_image)" :alt="product.title" class="product__image"></div>
    <div class="product__content">
      <h2 class="product__title ui-display">{{ product.title }}</h2>
      <p v-if="product.subtitle" class="product__subtitle">{{ product.subtitle }}</p>
      <p v-if="product.short_description" class="product__description">{{ product.short_description }}</p>
      <div class="product__content-bottom">
        <ul v-if="product.catalog_metrics?.length" class="product__characteristics">
          <li v-for="item in product.catalog_metrics.slice(0, 4)" :key="`${item.label}-${item.value}`" class="product__characteristic"><AppIcon :name="item.icon" class="product__characteristic-icon" /><span class="product__characteristic-label">{{ item.label }}</span><strong class="product__characteristic-value">{{ item.value }}</strong></li>
        </ul>
        <div class="product__purchase"><div class="product__purchase-card ui-card"><div class="product__price ui-display">{{ formatMoney(product.price_minor, product.currency) }}</div><div class="product__stock" :class="{ 'product__stock--empty': !store.ordersEnabled || !available() }"><span class="product__stock-dot"></span>{{ store.ordersEnabled && available() ? (product.extra?.availability_label || 'Available to order') : (!available() ? 'Out of stock' : (product.extra?.unavailable_label || 'Orders are temporarily paused')) }}</div><RouterLink v-if="store.ordersEnabled && state.apiOnline && available()" class="product__order-button btn btn-primary" :to="`/checkout/${product.slug}`"><AppIcon name="cart" />Order</RouterLink><RouterLink class="product__details-button" :to="`/product/${product.slug}`">View details<AppIcon name="arrow" /></RouterLink></div></div>
      </div>
    </div>
  </article>
</template>
